from flask import Flask, request, jsonify
from flask_cors import CORS
from model.sweet_model import add_sweet, get_sweets, remove_sweet, get_sweet_by_id
from model.order_model import place_order, get_orders, get_daily_summary, update_order_status, edit_order

app = Flask(__name__)
CORS(app)

@app.route("/sweets", methods=["GET"])
def fetch_sweets():
    """Get all available sweets."""
    category = request.args.get("category")
    return jsonify(get_sweets(category))

@app.route("/place_order", methods=["POST"])
def new_order():
    """
    Place a new order.
    Now includes delivery date support.
    """
    data = request.get_json()
    
    print("\n" + "="*60)
    print("📝 NEW ORDER RECEIVED")
    print("="*60)
    
    if not data or "items" not in data:
        print("❌ Invalid order data: missing 'items' field")
        return jsonify({"error": "Invalid order data. 'items' field is required."}), 400
    
    items = data.get("items", [])
    
    if not items:
        print("❌ Empty order: no items provided")
        return jsonify({"error": "Order must contain at least one item"}), 400
    
    # Validate required date fields
    if "orderDate" not in data or not data.get("orderDate"):
        print("❌ Missing required field: orderDate")
        return jsonify({"error": "Order date is required"}), 400
    
    if "deliveryDate" not in data or not data.get("deliveryDate"):
        print("❌ Missing required field: deliveryDate")
        return jsonify({"error": "Delivery date is required"}), 400
    
    print(f"📅 Order Date: {data.get('orderDate')}")
    print(f"📅 Delivery Date: {data.get('deliveryDate')}")
    
    print(f"\n📦 Order Details:")
    print(f"   Customer: {data.get('customerName', 'Unknown')}")
    print(f"   Total Items: {len(items)}")
    print(f"   Total Amount: ₹{data.get('total', 0)}")
    
    for item in items:
        if not item.get("sweetId"):
            error_msg = f"Missing sweetId for item: {item.get('sweetName', 'Unknown')}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        # Validate quantity: required and must be >= 1
        if "quantity" not in item:
            error_msg = f"Missing quantity for item: {item.get('sweetName', 'Unknown')}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        try:
            quantity = float(item.get("quantity", 0))
            if quantity < 1:
                error_msg = f"Quantity must be at least 1 for item: {item.get('sweetName', 'Unknown')}"
                print(f"❌ {error_msg}")
                return jsonify({"error": error_msg}), 400
        except (ValueError, TypeError):
            error_msg = f"Invalid quantity for item: {item.get('sweetName', 'Unknown')}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 400
    
    print("\n💾 Saving order to database...")
    try:
        place_order(data)
        print("✅ Order saved successfully!")
        print("="*60 + "\n")
        return jsonify({
            "message": "Order placed successfully! 🎉",
            "orderDate": data.get("orderDate"),
            "deliveryDate": data.get("deliveryDate"),
            "total": data.get("total"),
            "customerName": data.get("customerName")
        }), 201
    except Exception as e:
        error_msg = f"Failed to save order: {str(e)}"
        print(f"❌ {error_msg}")
        print("="*60 + "\n")
        return jsonify({"error": error_msg}), 500

# ---------- ADMIN ROUTES ----------

@app.route("/admin/add_sweet", methods=["POST"])
def admin_add_sweet():
    """Add a new sweet to the inventory.
    Supports optional existingSweetId: if provided, use its details unless overridden by payload.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Category is always required
    if "category" not in data or not str(data.get("category", "")).strip():
        return jsonify({"error": "Missing required field: category"}), 400

    existing_id = data.get("existingSweetId")
    base = {}

    if existing_id:
        found = get_sweet_by_id(existing_id)
        if not found:
            return jsonify({"error": "Existing sweet not found"}), 404
        base = {
            "name": found.get("name", ""),
            "rate": found.get("rate", 0),
            "description": found.get("description", ""),
            "image_url": found.get("image_url") or found.get("imageUrl") or "",
        }
        # Merge with overrides from the request body
        payload = {
            "name": data.get("name", base["name"]),
            "rate": data.get("rate", base["rate"]),
            "description": data.get("description", base["description"]),
            "image_url": data.get("image_url") or data.get("imageUrl") or base["image_url"],
            "category": data.get("category"),
        }
    else:
        # For manual entry, require name and rate
        for field in ["name", "rate"]:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        payload = data

    try:
        add_sweet(payload)
        return jsonify({"message": "Sweet added successfully", "sweet": payload.get("name")}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to add sweet: {str(e)}"}), 500

@app.route("/admin/remove_sweet", methods=["DELETE"])
def admin_remove_sweet():
    """Remove a sweet from the inventory."""
    name = request.args.get("name")
    
    if not name:
        return jsonify({"error": "Sweet name is required"}), 400
    
    try:
        remove_sweet(name)
        return jsonify({"message": f"Sweet '{name}' removed successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to remove sweet: {str(e)}"}), 500

@app.route("/admin/orders", methods=["GET"])
def admin_orders():
    """Get all orders with optional delivery date filtering."""
    try:
        orders = get_orders()
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch orders: {str(e)}"}), 500

@app.route("/admin/daily_summary", methods=["GET"])
def admin_summary():
    """Get daily sales summary."""
    try:
        summary = get_daily_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch daily summary: {str(e)}"}), 500

# ----- ORDER ADMIN UPDATES -----

@app.route("/admin/update_order_status", methods=["PUT"])
def admin_update_order_status():
    """Update status of an order by orderId."""
    # Accept JSON, form, or query params but require BOTH orderId and status
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    order_id = (
        data.get("orderId")
        or data.get("_id")
        or data.get("id")
        or request.args.get("orderId")
        or request.args.get("_id")
        or request.args.get("id")
    )
    raw_status = data.get("status") or request.args.get("status")

    if not order_id or not raw_status:
        return jsonify({"error": "Missing required fields: orderId and status"}), 400

    status_lc = str(raw_status).strip().lower()
    if status_lc not in ("delivered", "cancelled"):
        return jsonify({"error": "Invalid status. Allowed values: Delivered or Cancelled"}), 400
    status = "Delivered" if status_lc == "delivered" else "Cancelled"

    try:
        updated = update_order_status(order_id, status)
        if not updated:
            return jsonify({"error": "Order not found"}), 404
        success_msg = "Order marked as Delivered" if status == "Delivered" else "Order Cancelled"
        return jsonify({"message": success_msg, "order": updated}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update order status: {str(e)}"}), 500


@app.route("/admin/edit_order/<order_id>", methods=["PUT"])
def admin_edit_order(order_id):
    """Edit fields of an order by ID. Only provided fields are updated."""
    data = request.get_json() or {}
    try:
        updated = edit_order(order_id, data)
        if not updated:
            return jsonify({"error": "Order not found"}), 404
        return jsonify({"message": "Order updated successfully", "order": updated}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to edit order: {str(e)}"}), 500

if __name__ == "__main__":
    # Disable auto-reloader on Windows to avoid intermittent WinError 10038 during restarts
    app.run(debug=True, use_reloader=False)