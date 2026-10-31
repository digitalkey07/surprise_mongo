
import ipaddress

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from pymongo.errors import PyMongoError
from bson import ObjectId

from database import get_db
from config import USER_TYPE


track_bp = Blueprint("track", __name__)


# ======================================
# DEVICE DETECTION
# ======================================

def detect_device(ua):

    ua = ua.lower()

    if "ipad" in ua or "tablet" in ua:
        device = "Tablet"

    elif any(x in ua for x in ("mobile", "android", "iphone")):
        device = "Mobile"

    else:
        device = "Desktop / Unknown"

    # Browser detection

    if "edg/" in ua:
        browser = "Microsoft Edge"

    elif "opr/" in ua:
        browser = "Opera"

    elif "firefox/" in ua:
        browser = "Firefox"

    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"

    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"

    else:
        browser = "Other / Unknown"

    # Operating system detection

    if "windows" in ua:
        os_name = "Windows"

    elif "android" in ua:
        os_name = "Android"

    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS / iPadOS"

    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"

    elif "linux" in ua:
        os_name = "Linux"

    else:
        os_name = "Other / Unknown"

    return device, browser, os_name


# ======================================
# TRACKING API
# ======================================

@track_bp.route("/track", methods=["POST"])
def track_visitor():

    data = request.get_json(silent=True) or {}

    # ----------------------------------
    # 1. SHARED ID REQUIRED
    # ----------------------------------

    user_id = data.get("user_id")
    visitor_id = data.get("visitor_id")

    if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):

        return jsonify({
            "status": "error",
            "message": "Shared ID is required"
        }), 400

    user_id = ObjectId(user_id)

    # ----------------------------------
    # 2. VALIDATE PAGE PATH
    # ----------------------------------

    page_path = data.get("page_path", "/")

    if not isinstance(page_path, str) or not page_path.startswith("/"):

        return jsonify({
            "status": "error",
            "message": "Invalid page path"
        }), 400

    page_path = page_path.split("?", 1)[0][:500]

    # ----------------------------------
    # 3. GET IP ADDRESS
    # ----------------------------------

    ip = request.remote_addr

    if ip:
        try:
            ip = str(ipaddress.ip_address(ip))
        except ValueError:
            ip = None

    # ----------------------------------
    # 4. DEVICE INFORMATION
    # ----------------------------------

    ua = request.headers.get("User-Agent", "")[:500]

    device, browser, os_name = detect_device(ua)

    visited_at = datetime.now(timezone.utc)

    # ----------------------------------
    # 5. VALIDATE VISITOR ID
    # ----------------------------------

    if visitor_id is not None:

        if not isinstance(visitor_id, str) or not ObjectId.is_valid(visitor_id):

            return jsonify({
                "status": "error",
                "message": "Invalid visitor ID"
            }), 400

        visitor_object_id = ObjectId(visitor_id)

    else:
        visitor_object_id = None

    try:

        db = get_db()

        # ----------------------------------
        # 6. VERIFY SHARE OWNER
        # ----------------------------------

        owner = db.users.find_one({
            "_id": user_id,
            "user_type": {"$ne": USER_TYPE}
        })

        if owner is None:

            return jsonify({
                "status": "error",
                "message": "Invalid share link"
            }), 404

        # ----------------------------------
        # 7. VISITOR DOCUMENT
        # ----------------------------------

        visitor_data = {
            "ip_address": ip,
            "user_agent": ua,
            "page_path": page_path,
            "visited_at": visited_at,
            "device_type": device,
            "browser": browser,
            "operating_system": os_name
        }

        # ----------------------------------
        # 8. UPDATE EXISTING VISITOR
        # ----------------------------------

        if visitor_object_id is not None:

            result = db.visitor_logs.update_one(
                {
                    "_id": visitor_object_id,
                    "user_id": user_id
                },
                {
                    "$set": visitor_data
                }
            )

            if result.matched_count == 0:

                return jsonify({
                    "status": "error",
                    "message": "Visitor not found for this share link"
                }), 404

            action = "updated"
            visitor_id = str(visitor_object_id)

        # ----------------------------------
        # 9. INSERT NEW VISITOR
        # ----------------------------------

        else:

            visitor_data["user_id"] = user_id

            result = db.visitor_logs.insert_one(visitor_data)

            visitor_id = str(result.inserted_id)

            action = "inserted"

        return jsonify({
            "status": "success",
            "message": "Visitor recorded successfully",
            "visitor_id": visitor_id,
            "action": action
        }), 200

    except PyMongoError as e:

        print("Tracking database error:", e)

        return jsonify({
            "status": "error",
            "message": "Database error. Please try again."
        }), 500


# ======================================
# SAVE LOCATION API
# ======================================

@track_bp.route("/save-location", methods=["POST"])
def save_location():
    print("save Location Call-----------")

    data = request.get_json(silent=True) or {}

    if not data:

        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400

    visitor_id = data.get("id")
    user_id = data.get("user_id")

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    accuracy = data.get("accuracy")

    visited_at = datetime.now(timezone.utc)

    # ----------------------------------
    # 1. REQUIRED FIELDS
    # ----------------------------------

    if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):

        return jsonify({
            "status": "error",
            "message": "User ID is required"
        }), 400

    _id = ObjectId(user_id)

    if not isinstance(visitor_id, str) or not ObjectId.is_valid(visitor_id):

        return jsonify({
            "status": "error",
            "message": "Valid visitor ID is required"
        }), 400

    visitor_object_id = ObjectId(visitor_id)

    # ----------------------------------
    # 2. VALIDATE LOCATION
    # ----------------------------------

    try:

        if isinstance(latitude, bool) or isinstance(longitude, bool):
            raise ValueError()

        latitude = float(latitude)
        longitude = float(longitude)

        if accuracy is not None:

            if isinstance(accuracy, bool):
                raise ValueError()

            accuracy = float(accuracy)

        if not (-90 <= latitude <= 90):
            raise ValueError()

        if not (-180 <= longitude <= 180):
            raise ValueError()

        if accuracy is not None and accuracy < 0:
            raise ValueError()

    except (TypeError, ValueError):

        return jsonify({
            "status": "error",
            "message": "Invalid location data"
        }), 400

    # ----------------------------------
    # 3. VERIFY OWNER AND VISITOR
    # ----------------------------------

    try:

        db = get_db()

        owner = db.users.find_one({
            "_id": _id
        })

        if owner is None:

            return jsonify({
                "status": "error",
                "message": "Invalid User ID"
            }), 404

        visitor = db.visitor_logs.find_one({
            "_id": visitor_object_id,
            "user_id": _id
        })

        if visitor is None:

            return jsonify({
                "status": "error",
                "message": "Visitor does not belong to this share link"
            }), 403

        # ----------------------------------
        # 4. UPDATE LOCATION
        # ----------------------------------

        db.visitor_logs.update_one(
            {
                "_id": visitor_object_id,
                "user_id": _id
            },
            {
                "$set": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "accuracy": accuracy,
                    "visited_at": visited_at
                }
            }
        )
   

        return jsonify({
            "status": "success",
            "message": "Location saved successfully",
            "visitor_id": visitor_id
        }), 200

    except PyMongoError as e:

        print("Location database error:", e)

        return jsonify({
            "status": "error",
            "message": "Database error. Please try again."
        }), 500
