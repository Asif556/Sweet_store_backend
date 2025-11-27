from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import ssl
import re

load_dotenv()

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
    # IMPORTANT: Do not set tlsInsecure and tlsAllowInvalidCertificates together
    client = MongoClient(MONGO_URI, **mongo_kwargs)
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB connection successful!")
except Exception as e:
    print(f"⚠️ MongoDB connection error: {e}")
    client = None

db = client["sweet_store"] if client is not None else None
sweet_collection = db["sweets"] if db is not None else None


def add_sweet(data):
    """Add a new sweet to the database, including category and normalized fields.
    Accepts and stores base64 image strings without modification.
    """
    if sweet_collection is None:
        raise RuntimeError("Database not connected: cannot add sweet")

    # Normalize inputs and coerce types
    try:
        rate_val = float(data.get("rate", 0) or 0)
    except (ValueError, TypeError):
        rate_val = 0

    # Validate and normalize unit field
    unit = data.get("unit", "kg").strip().lower()
    if unit not in ["piece", "kg"]:
        unit = "kg"  # Default to 'kg' if invalid

    # Accept image from multiple keys: image, image_url, or imageUrl
    image_data = data.get("image") or data.get("image_url") or data.get("imageUrl") or ""
    
    # Validate base64 image format if image is provided
    if image_data:
        if not isinstance(image_data, str):
            raise ValueError("Image must be a string")
        if not image_data.startswith('data:image/'):
            raise ValueError("Invalid image format. Must be a base64 data URI starting with 'data:image/'")
        print(f"📸 Storing image for '{data.get('name', 'Unknown')}' - Length: {len(image_data)} characters")
        print(f"   Image starts with: {image_data[:50]}...")
    else:
        print(f"⚠️ No image provided for '{data.get('name', 'Unknown')}'")

    doc = {
        "name": data.get("name", "").strip(),
        "rate": rate_val,
        "description": data.get("description", ""),
        # Store as 'image' field to match common frontend expectations
        "image": image_data,
        "category": data.get("category", "").strip(),
        "unit": unit,
    }

    result = sweet_collection.insert_one(doc)
    print(f"✅ Sweet '{doc['name']}' added successfully with ID: {result.inserted_id}")

def get_sweets(category: str | None = None):
    """Get sweets from the database with optional category filter.
    Includes '_id' (as string) and ensures 'category' in the result.
    Returns complete image field without modification.
    """
    if sweet_collection is None:
        print("⚠️ Database not connected; returning empty sweets list")
        return []
    query = {}
    if category:
        # Case-insensitive CONTAINS match for robustness (e.g., "din" matches "Dinner")
        cat = str(category).strip()
        if cat:
            query["category"] = re.compile(re.escape(cat), re.IGNORECASE)
    docs = list(sweet_collection.find(query))
    # Backfill category and unit for older records, normalize image field
    for d in docs:
        if d.get("_id") is not None:
            d["_id"] = str(d["_id"])
        if "category" not in d:
            d["category"] = "Uncategorized"
        if "unit" not in d:
            d["unit"] = "kg"  # Default to 'kg' for backward compatibility
        
        # Normalize image field: ensure 'image' field exists
        # Support legacy records that may have 'image_url' or 'imageUrl'
        if "image" not in d:
            d["image"] = d.get("image_url") or d.get("imageUrl") or ""
        
        # Log image info for debugging (only first sweet to avoid spam)
        if docs.index(d) == 0 and d.get("image"):
            print(f"📸 Returning sweet '{d.get('name')}' - Image length: {len(d['image'])} characters")
            print(f"   Image starts with: {d['image'][:50]}...")
    
    return docs

def get_sweet_by_id(id_str: str):
    """Fetch a single sweet by its ObjectId string. Returns dict or None.
    Returns complete image field without modification.
    """
    if sweet_collection is None:
        return None
    try:
        oid = ObjectId(id_str)
    except Exception:
        return None
    doc = sweet_collection.find_one({"_id": oid})
    if not doc:
        return None
    # Normalize id to string for callers
    doc["_id"] = str(doc["_id"]) if doc.get("_id") is not None else None
    # Backfill unit for backward compatibility
    if "unit" not in doc:
        doc["unit"] = "kg"
    
    # Normalize image field: ensure 'image' field exists
    # Support legacy records that may have 'image_url' or 'imageUrl'
    if "image" not in doc:
        doc["image"] = doc.get("image_url") or doc.get("imageUrl") or ""
    
    return doc

def remove_sweet(name):
    """Remove a sweet from the database by name."""
    if sweet_collection is None:
        raise RuntimeError("Database not connected: cannot remove sweet")
    sweet_collection.delete_one({"name": name})
