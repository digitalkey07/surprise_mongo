
from bson import ObjectId
from pymongo.errors import PyMongoError
from flask import Blueprint, render_template, request, jsonify

from database import get_db
from utils.validator import validate_token
from config import USER_TYPE


user_bp = Blueprint("user_dashboard", __name__)


# ============================================================
# AUTHENTICATE NORMAL USER
# ============================================================

def get_current_user():

    data = request.get_json(silent=True) or {}
    token = data.get("token")

    if not isinstance(token, str) or not token:
        return None, (jsonify({
            "status": "error",
            "message": "Login required."
        }), 401)

    try:
        token_data = validate_token(token)
    except Exception:
        token_data = None

    if not isinstance(token_data, dict):
        return None, (jsonify({
            "status": "error",
            "message": "Invalid or expired token."
        }), 401)

    # Current token format uses user_id
    user_id = token_data.get("user_id")

    if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
        return None, (jsonify({
            "status": "error",
            "message": "Invalid user ID in token."
        }), 401)

    try:
        db = get_db()

        user = db.users.find_one(
            {
                "_id": ObjectId(user_id),
                "user_type": {"$ne": USER_TYPE}
            },
            {
                "username": 1,
                "user_type": 1,
                "is_verify": 1
            }
        )

    except PyMongoError as e:
        print("User authentication database error:", e)

        return None, (jsonify({
            "status": "error",
            "message": "Database error."
        }), 500)

    if user is None:
        return None, (jsonify({
            "status": "error",
            "message": "User not found or account is not a normal user."
        }), 401)

    if not user.get("is_verify", False):
        return None, (jsonify({
            "status": "error",
            "message": "Please verify your account."
        }), 403)

    user["id"] = str(user.pop("_id"))

    return user, None


# ============================================================
# SERIALIZE VISITOR DOCUMENT
# ============================================================

def serialize_visitor(visitor):

    visitor["id"] = str(visitor.pop("_id"))

    # Convert BSON ObjectId to string for JSON response
    user_id = visitor.get("user_id")

    if isinstance(user_id, ObjectId):
        visitor["user_id"] = str(user_id)

    return visitor


# ============================================================
# FETCH VISITORS FOR CURRENT USER
# ============================================================

def fetch_visitors(user_id, limit=None, search=""):

    db = get_db()

    query = {
        "user_id": user_id
    }

    if search:

        safe_search = search

        query["$or"] = [
            {
                "ip_address": {
                    "$regex": safe_search,
                    "$options": "i"
                }
            },
            {
                "page_path": {
                    "$regex": safe_search,
                    "$options": "i"
                }
            },
            {
                "browser": {
                    "$regex": safe_search,
                    "$options": "i"
                }
            },
            {
                "operating_system": {
                    "$regex": safe_search,
                    "$options": "i"
                }
            },
            {
                "device_type": {
                    "$regex": safe_search,
                    "$options": "i"
                }
            }
        ]

    projection = {
        "user_id": 1,
        "ip_address": 1,
        "mac_address": 1,
        "page_path": 1,
        "visited_at": 1,
        "device_type": 1,
        "browser": 1,
        "operating_system": 1,
        "latitude": 1,
        "longitude": 1,
        "accuracy": 1
    }

    cursor = db.visitor_logs.find(
        query,
        projection
    ).sort("_id", -1)

    if limit is not None:
        cursor = cursor.limit(limit)

    return [
        serialize_visitor(visitor)
        for visitor in cursor
    ]


# ============================================================
# DASHBOARD PAGE
# ============================================================

@user_bp.route("/dashboard", methods=["GET"])
def user_dashboard_page():

    return render_template("user_dashboard.html")


# ============================================================
# USER PROFILE API
# POST /user/profile
# ============================================================

@user_bp.route("/user/profile", methods=["POST"])
def user_profile():

    user, error = get_current_user()

    if error:
        return error

    return jsonify({
        "status": "success",
        "profile": {
            "id": user["id"],
            "username": user["username"],
            "user_type": user["user_type"]
        }
    }), 200


# ============================================================
# USER DASHBOARD API
# POST /user/dashboard
# ============================================================

@user_bp.route("/user/dashboard", methods=["POST"])
def user_dashboard_data():

    user, error = get_current_user()

    if error:
        return error

    try:
        db = get_db()

        user_object_id = ObjectId(user["id"])

        total = db.visitor_logs.count_documents({
            "user_id": user_object_id
        })

        recent = fetch_visitors(
            user_id=user_object_id,
            limit=5
        )

    except PyMongoError as e:
        print("Dashboard database error:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to load dashboard data."
        }), 500

    return jsonify({
        "status": "success",
        "username": user["username"],
        "user_type": user["user_type"],
        "user_id": user["id"],
        "total_visitors": total,
        "recent_visitors": recent
    }), 200


# ============================================================
# ACTIVE FESTIVALS API
# POST /user/festivals
# ============================================================

@user_bp.route("/user/festivals", methods=["POST"])
def user_festivals():

    user, error = get_current_user()

    if error:
        return error

    try:
        db = get_db()

        cursor = db.uidata.find(
            {
                "is_active": 1
            },
            {
                "festival_name": 1,
                "title": 1,
                "subtitle": 1,
                "eyebrow": 1
            }
        ).sort("festival_name", 1)

        festivals = []

        for festival in cursor:

            festival["id"] = str(festival.pop("_id"))

            festivals.append(festival)

    except PyMongoError as e:
        print("Festivals database error:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to load festivals."
        }), 500

    return jsonify({
        "status": "success",
        "festivals": festivals
    }), 200


# ============================================================
# USER VISITORS API
# POST /user/visitors
# ============================================================

@user_bp.route("/user/visitors", methods=["POST"])
def user_visitors_data():

    user, error = get_current_user()

    if error:
        return error

    data = request.get_json(silent=True) or {}
    search = data.get("search", "")

    if not isinstance(search, str):
        return jsonify({
            "status": "error",
            "message": "Invalid search value."
        }), 400

    try:
        visitors = fetch_visitors(
            user_id=ObjectId(user["id"]),
            search=search.strip()[:100]
        )

    except PyMongoError as e:
        print("Visitors database error:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to load visitors."
        }), 500

    return jsonify({
        "status": "success",
        "total_visitors": len(visitors),
        "visitors": visitors
    }), 200
