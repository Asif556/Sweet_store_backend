from pymongo import MongoClient, ReturnDocument
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime, date
import ssl

load_dotenv()

def validate_dates(order_date_str, delivery_date_str):
    """Validate that order and delivery dates are valid and meet business rules.
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    try:
        # Parse dates from YYYY-MM-DD format
        order_date = datetime.strptime(order_date_str, "%Y-%m-%d").date()
        delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False, "Invalid date format. Expected YYYY-MM-DD."
    
    today = date.today()
    
    # Check if orderDate is not in the past (allow today)
    if order_date < today:
        return False, "Order date cannot be in the past."
    
    # Check if deliveryDate is not in the past
    if delivery_date < today:
        return False, "Delivery date cannot be in the past."
    
    # Check if deliveryDate is >= orderDate
    if delivery_date < order_date:
        return False, "Delivery date must be on or after the order date."
    
    return True, None

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    # Fallback to local Mongo for development so endpoints don't 500 when env is missing
    MONGO_URI = "mongodb://127.0.0.1:27017"
    print("⚠️ MONGO_URI not set; falling back to local MongoDB at mongodb://127.0.0.1:27017")

# Force legacy OpenSSL provider for compatibility with MongoDB Atlas
os.environ['OPENSSL_CONF'] = ''

# Create SSL context with legacy settings
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT

# MongoDB connection with safer TLS handling
try:
    mongo_kwargs = {
        "serverSelectionTimeoutMS": 30000,
    }
    # Enable TLS only for SRV (Atlas) URIs or when explicitly provided in URI
    if MONGO_URI.startswith("mongodb+srv://"):
        mongo_kwargs["tls"] = True
        # Optionally allow invalid certs via env toggle (default False)
        if os.getenv("MONGO_TLS_ALLOW_INVALID", "false").lower() in ("1", "true", "yes"):
            mongo_kwargs["tlsAllowInvalidCertificates"] = True

    client = MongoClient(MONGO_URI, **mongo_kwargs)
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB connection successful!")
except Exception as e:
    print(f"⚠️ MongoDB connection error: {e}")
    client = None

db = client["sweet_store"] if client is not None else None
order_collection = db["orders"] if db is not None else None

def place_order(order):
    """Place a new order in the database with delivery date support."""
    if order_collection is None:
        raise RuntimeError("Database not connected: cannot place order")
    
    # Validate required date fields
    if "orderDate" not in order or not order["orderDate"]:
        raise ValueError("Order date is required")
    if "deliveryDate" not in order or not order["deliveryDate"]:
        raise ValueError("Delivery date is required")
    
    # Validate dates
    is_valid, error_msg = validate_dates(order["orderDate"], order["deliveryDate"])
    if not is_valid:
        raise ValueError(error_msg)
    
    now = datetime.now()
    order["createdAt"] = now
    
    # Store both dates as strings in YYYY-MM-DD format
    order["orderDate"] = order["orderDate"]
    order["deliveryDate"] = order["deliveryDate"]
    
    # Ensure numeric fields are stored as numbers
    try:
        if "total" in order:
            order["total"] = float(order.get("total", 0) or 0)
    except (ValueError, TypeError):
        order["total"] = 0

    # Coerce item prices and quantities to numeric types
    for item in order.get("items", []) or []:
        try:
            if "quantity" in item:
                item["quantity"] = float(item.get("quantity", 0) or 0)
        except (ValueError, TypeError):
            item["quantity"] = 0
        try:
            if "price" in item:
                item["price"] = float(item.get("price", 0) or 0)
        except (ValueError, TypeError):
            item["price"] = 0

    order_collection.insert_one(order)

def _serialize_datetimes(doc):
    """Convert datetime objects in a document to strings to make them JSON-serializable."""
    if not doc:
        return doc
    if isinstance(doc.get("createdAt"), datetime):
        doc["createdAt"] = doc["createdAt"].strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(doc.get("updatedAt"), datetime):
        doc["updatedAt"] = doc["updatedAt"].strftime("%Y-%m-%d %H:%M:%S")
    # orderDate and deliveryDate are already strings
    return doc

def _serialize_order(doc):
    """Normalize an order document for API responses (stringify _id and datetimes)."""
    if not doc:
        return None
    doc = dict(doc)
    if doc.get("_id") is not None:
        doc["_id"] = str(doc["_id"])
    return _serialize_datetimes(doc)

def get_orders():
    """Retrieve all orders, sorted by delivery date (ascending), including _id as string.
    Orders without deliveryDate will be sorted to the end.
    """
    if order_collection is None:
        print("⚠️ Database not connected; returning empty orders list")
        return []
    # Sort by deliveryDate ascending (1), nulls last
    # MongoDB sorts null/missing values first, so we need a pipeline to handle this
    pipeline = [
        {
            "$addFields": {
                "deliveryDateSort": {
                    "$ifNull": ["$deliveryDate", "9999-12-31"]
                }
            }
        },
        {"$sort": {"deliveryDateSort": 1}},
        {"$project": {"deliveryDateSort": 0}}
    ]
    docs = list(order_collection.aggregate(pipeline))
    return [_serialize_order(d) for d in docs]

def get_daily_summary():
    """Get summary statistics for today's orders."""
    if order_collection is None:
        print("⚠️ Database not connected; returning empty daily summary")
        return {
            "total_orders": 0,
            "total_revenue": 0,
            "total_items_sold": 0,
            "popular_sweets": [],
            "orders": []
        }

    today = datetime.now().strftime("%Y-%m-%d")
    today_orders = list(order_collection.find({"orderDate": today}, {"_id": 0}).sort("createdAt", -1))

    total_orders = len(today_orders)
    total_revenue = 0
    for order in today_orders:
        try:
            total_revenue += float(order.get("total", 0) or 0)
        except (ValueError, TypeError):
            continue

    total_items_sold = 0
    sweet_stats = {}

    for order in today_orders:
        for item in order.get("items", []) or []:
            try:
                quantity_ordered = float(item.get("quantity", 0) or 0)
            except (ValueError, TypeError):
                quantity_ordered = 0

            sweet_name = item.get("sweetName") or item.get("name") or "Unknown"

            try:
                price = float(item.get("price", 0) or 0)
            except (ValueError, TypeError):
                price = 0

            total_items_sold += quantity_ordered

            if sweet_name not in sweet_stats:
                sweet_stats[sweet_name] = {"name": sweet_name, "quantity": 0, "revenue": 0}

            sweet_stats[sweet_name]["quantity"] += quantity_ordered
            sweet_stats[sweet_name]["revenue"] += quantity_ordered * price

    popular_sweets = sorted(sweet_stats.values(), key=lambda x: x["quantity"], reverse=True)

    serialized_orders = [_serialize_order(o) for o in today_orders]

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_items_sold": total_items_sold,
        "popular_sweets": popular_sweets[:5],
        "orders": serialized_orders
    }

def update_order_status(order_id: str, status: str):
    """Update the status of an order and return the updated document.
    Returns None if order not found.
    """
    if order_collection is None:
        raise RuntimeError("Database not connected: cannot update order status")
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None

    updated = order_collection.find_one_and_update(
        {"_id": oid},
        {"$set": {"status": status, "updatedAt": datetime.now()}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 1, "customerName": 1, "mobile": 1, "address": 1, "status": 1, "total": 1, "orderDate": 1, "deliveryDate": 1, "createdAt": 1, "updatedAt": 1, "items": 1}
    )
    if not updated:
        return None
    return _serialize_order(updated)

def edit_order(order_id: str, updates: dict):
    """Update provided fields of an order and return the updated document.
    Supports field mapping: contact->mobile, amount->total.
    Validates deliveryDate if being updated.
    Returns None if order not found.
    """
    if order_collection is None:
        raise RuntimeError("Database not connected: cannot edit order")
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None
    
    # If deliveryDate is being updated, validate it against orderDate
    if "deliveryDate" in updates and updates["deliveryDate"]:
        # Fetch current order to get orderDate
        current_order = order_collection.find_one({"_id": oid})
        if not current_order:
            return None
        
        order_date = current_order.get("orderDate")
        if not order_date:
            # For legacy orders without orderDate, use createdAt date
            if "createdAt" in current_order:
                order_date = current_order["createdAt"].strftime("%Y-%m-%d")
            else:
                order_date = datetime.now().strftime("%Y-%m-%d")
        
        # Validate the new delivery date
        is_valid, error_msg = validate_dates(order_date, updates["deliveryDate"])
        if not is_valid:
            raise ValueError(error_msg)

    field_map = {
        "customerName": "customerName",
        "contact": "mobile",
        "amount": "total",
        "status": "status",
        # Allow some common fields to pass through as-is
        "address": "address",
        "mobile": "mobile",
        "total": "total",
        "orderDate": "orderDate",
        "deliveryDate": "deliveryDate",
        "preference": "preference",
        "items": "items",
    }

    set_payload = {}
    for k, v in (updates or {}).items():
        if k not in field_map:
            continue
        dest = field_map[k]
        if dest == "total":
            try:
                v = float(v or 0)
            except (ValueError, TypeError):
                v = 0
        if dest == "items" and isinstance(v, list):
            # Coerce numeric fields inside items
            norm_items = []
            for item in v:
                if not isinstance(item, dict):
                    continue
                itm = dict(item)
                try:
                    if "quantity" in itm:
                        itm["quantity"] = float(itm.get("quantity", 0) or 0)
                except (ValueError, TypeError):
                    itm["quantity"] = 0
                try:
                    if "price" in itm:
                        itm["price"] = float(itm.get("price", 0) or 0)
                except (ValueError, TypeError):
                    itm["price"] = 0
                norm_items.append(itm)
            v = norm_items
        set_payload[dest] = v

    if not set_payload:
        # Nothing to update; return current doc
        current = order_collection.find_one({"_id": oid})
        if not current:
            return None
        return _serialize_order(current)

    set_payload["updatedAt"] = datetime.now()

    updated = order_collection.find_one_and_update(
        {"_id": oid},
        {"$set": set_payload},
        return_document=ReturnDocument.AFTER
    )
    if not updated:
        return None
    return _serialize_order(updated)
