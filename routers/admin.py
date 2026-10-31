
import json
import re

from datetime import datetime, timezone

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify
)

from bson import ObjectId
from pymongo.errors import PyMongoError

from database import get_db
from utils.validator import validate_token
from config import USER_TYPE


admin_bp = Blueprint("admin", __name__)


# ============================================================
# COMMON HELPERS
# ============================================================

def serialize_document(document):
    """MongoDB ObjectId ko JSON-compatible string mein convert karo."""

    if document is None:
        return None

    document = dict(document)

    if "_id" in document:
        document["id"] = str(document.pop("_id"))

    # User ID ko bhi string mein convert karo
    if isinstance(document.get("user_id"), ObjectId):
        document["user_id"] = str(document["user_id"])

    return document


def get_object_id(value):
    """Valid MongoDB ObjectId return karo."""

    if not isinstance(value, str) or not ObjectId.is_valid(value):
        return None

    return ObjectId(value)


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def get_request_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

def get_admin_from_token():

    data = get_request_data()
    token = data.get("token")

    if not token:
        return None, (
            jsonify({
                "status": "error",
                "error": "Login required."
            }),
            401
        )

    token_data = validate_token(token)

    if not token_data:
        return None, (
            jsonify({
                "status": "error",
                "error": "Invalid or expired token."
            }),
            401
        )

    # New token structure:
    # {"user_id": "MongoDB ObjectId"}

    user_id = token_data.get("user_id")

    object_id = get_object_id(user_id)

    if object_id is None:
        return None, (
            jsonify({
                "status": "error",
                "error": "Invalid or expired token."
            }),
            401
        )

    try:

        db = get_db()

        admin = db.users.find_one(
            {
                "_id": object_id,
                "user_type": USER_TYPE,
                "is_verify": True
            },
            {
                "username": 1,
                "user_type": 1,
                "is_verify": 1
            }
        )

        if not admin:
            return None, (
                jsonify({
                    "status": "error",
                    "error": "Admin access required."
                }),
                403
            )

        return serialize_document(admin), None

    except PyMongoError as e:

        print("Admin authentication error:", e)

        return None, (
            jsonify({
                "status": "error",
                "error": "Database error."
            }),
            500
        )


# ============================================================
# VISITOR HELPERS
# ============================================================

def prepare_visitors(db, query=None, limit=200):

    if query is None:
        query = {}

    visitors = list(
        db.visitor_logs.find(query)
        .sort("_id", -1)
        .limit(limit)
    )

    # Visitor records se user IDs collect karo
    user_ids = list({
        visitor.get("user_id")
        for visitor in visitors
        if isinstance(visitor.get("user_id"), ObjectId)
    })

    users_map = {}

    # Ek baar mein sabhi users search karo
    if user_ids:

        owners = db.users.find(
            {
                "_id": {
                    "$in": user_ids
                }
            },
            {
                "username": 1
            }
        )

        users_map = {
            owner["_id"]: owner["username"]
            for owner in owners
        }

    result = []

    for visitor in visitors:

        # Serialize karne se pehle original user_id save karo
        user_id = visitor.get("user_id")

        visitor = serialize_document(visitor)

        visitor["referrer_username"] = users_map.get(user_id)

        result.append(visitor)

    return result


# ============================================================
# COLOR VALIDATION
# ============================================================

def validate_color(value, default):

    if value is None or value == "":
        return default

    if not isinstance(value, str):
        raise ValueError("Invalid color value.")

    value = value.strip()

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(
            "Colors must use hexadecimal format, e.g. #b83280."
        )

    return value


# ============================================================
# FESTIVAL DATA PREPARATION
# ============================================================

def prepare_festival_data(data):

    festival_name = data.get("festival_name")
    title = data.get("title")

    if not isinstance(festival_name, str) or not festival_name.strip():
        raise ValueError("Festival name is required.")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Festival title is required.")

    festival_name = festival_name.strip()
    title = title.strip()

    if len(festival_name) > 100:
        raise ValueError("Festival name cannot exceed 100 characters.")

    if len(title) > 200:
        raise ValueError("Title cannot exceed 200 characters.")

    text_fields = [
        "subtitle",
        "eyebrow",
        "message",
        "image_path",
        "download_text",
        "download_button_text",
        "surprise_button_text",
        "footer_text"
    ]

    result = {
        "festival_name": festival_name,
        "title": title
    }

    for field in text_fields:

        value = data.get(field, "")

        if value is None:
            value = ""

        if not isinstance(value, str):
            raise ValueError(f"{field} must be text.")

        result[field] = value.strip()

    # Wishes JSON array validation

    wishes = data.get("wishes", [])

    if isinstance(wishes, str):

        try:
            wishes = json.loads(wishes)

        except json.JSONDecodeError:
            raise ValueError("Wishes must be a valid JSON array.")

    if not isinstance(wishes, list):
        raise ValueError("Wishes must be a list.")

    if not all(isinstance(item, str) for item in wishes):
        raise ValueError("Every wish must be text.")

    # Frontend compatibility ke liye JSON string store kar rahe hain
    result["wishes"] = json.dumps(
        wishes,
        ensure_ascii=False
    )

    result["background_color"] = validate_color(
        data.get("background_color"),
        "#fff4f7"
    )

    result["card_color"] = validate_color(
        data.get("card_color"),
        "#ffffff"
    )

    result["text_color"] = validate_color(
        data.get("text_color"),
        "#333333"
    )

    result["theme_color"] = validate_color(
        data.get("theme_color"),
        "#b83280"
    )

    is_active = data.get("is_active", 1)

    if isinstance(is_active, bool):
        is_active = int(is_active)

    if isinstance(is_active, str) and is_active in ("0", "1"):
        is_active = int(is_active)

    if (
        isinstance(is_active, bool)
        or not isinstance(is_active, int)
        or is_active not in (0, 1)
    ):
        raise ValueError("is_active must be 0 or 1.")

    result["is_active"] = is_active

    return result


# ============================================================
# GET FESTIVAL BY ID
# ============================================================

def get_festival_by_id(db, festival_id):

    festival = db.uidata.find_one({
        "_id": festival_id
    })

    return serialize_document(festival)


# ============================================================
# ADMIN PAGE
# ============================================================

@admin_bp.route("/admin", methods=["GET"])
def admin():

    return render_template("admin.html")


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@admin_bp.route("/admin/dashboard", methods=["POST"])
def admin_dashboard():

    admin_user, error = get_admin_from_token()

    if error:
        return error

    try:

        db = get_db()

        total_visitors = db.visitor_logs.count_documents({})

        total_users = db.users.count_documents({
            "user_type": "user"
        })

        total_admins = db.users.count_documents({
            "user_type": USER_TYPE
        })

        total_festivals = db.uidata.count_documents({})

        active_festivals = db.uidata.count_documents({
            "is_active": 1
        })

        latest_visitors = prepare_visitors(
            db,
            limit=10
        )

        return jsonify({
            "status": "success",

            "admin": admin_user,

            "statistics": {
                "total_visitors": total_visitors,
                "total_users": total_users,
                "total_admins": total_admins,
                "total_festivals": total_festivals,
                "active_festivals": active_festivals
            },

            "latest_visitors": latest_visitors

        }), 200

    except PyMongoError as e:

        print("Dashboard error:", e)

        return jsonify({
            "status": "error",
            "error": "Database error."
        }), 500


# ============================================================
# USERS LIST
# ============================================================

@admin_bp.route("/admin/users", methods=["POST"])
def admin_users():

    admin_user, error = get_admin_from_token()

    if error:
        return error

    try:

        db = get_db()

        users = list(
            db.users.find(
                {},
                {
                    "username": 1,
                    "user_type": 1,
                    "is_verify": 1
                }
            ).sort("_id", -1)
        )

        return jsonify({
            "status": "success",

            "users": [
                serialize_document(user)
                for user in users
            ]

        }), 200

    except PyMongoError as e:

        print("Users list error:", e)

        return jsonify({
            "status": "error",
            "error": "Database error."
        }), 500


# ============================================================
# ALL VISITORS
# ============================================================

@admin_bp.route("/admin/visitors", methods=["POST"])
def admin_visitors():

    admin_user, error = get_admin_from_token()

    if error:
        return error

    try:

        db = get_db()

        visitors = prepare_visitors(
            db,
            limit=200
        )

        return jsonify({
            "status": "success",
            "visitors": visitors
        }), 200

    except PyMongoError as e:

        print("Visitors list error:", e)

        return jsonify({
            "status": "error",
            "error": "Database error."
        }), 500


# ============================================================
# VISITORS BELONGING TO A USER
# ============================================================

@admin_bp.route(
    "/admin/users/<string:user_id>/visitors",
    methods=["POST"]
)
def admin_user_visitors(user_id):

    admin_user, error = get_admin_from_token()

    if error:
        return error

    object_id = get_object_id(user_id)

    if object_id is None:
        return jsonify({
            "status": "error",
            "error": "Invalid user ID."
        }), 400

    try:

        db = get_db()

        user = db.users.find_one(
            {
                "_id": object_id
            },
            {
                "username": 1,
                "user_type": 1
            }
        )

        if not user:

            return jsonify({
                "status": "error",
                "error": "User not found."
            }), 404

        visitors = prepare_visitors(
            db,
            query={
                "user_id": object_id
            },
            limit=200
        )

        return jsonify({
            "status": "success",

            "user": serialize_document(user),

            "visitors": visitors

        }), 200

    except PyMongoError as e:

        print("User visitors error:", e)

        return jsonify({
            "status": "error",
            "error": "Database error."
        }), 500


# ============================================================
# FESTIVAL MANAGEMENT
#
# POST /admin/festivals
#
# action=list
# action=create
# action=update
# ============================================================

@admin_bp.route("/admin/festivals", methods=["POST"])
def admin_festivals():

    admin_user, error = get_admin_from_token()

    if error:
        return error

    data = get_request_data()

    action = data.get("action")

    try:

        db = get_db()

        # ----------------------------------------------------
        # LIST FESTIVALS
        # ----------------------------------------------------

        if action == "list":

            festivals = list(
                db.uidata.find({}).sort("_id", -1)
            )

            return jsonify({
                "status": "success",

                "festivals": [
                    serialize_document(festival)
                    for festival in festivals
                ]

            }), 200

        # ----------------------------------------------------
        # CREATE FESTIVAL
        # ----------------------------------------------------

        if action == "create":

            try:
                festival = prepare_festival_data(data)

            except ValueError as exc:

                return jsonify({
                    "status": "error",
                    "error": str(exc)
                }), 400

            timestamp = current_timestamp()

            festival["created_at"] = timestamp
            festival["updated_at"] = timestamp

            result = db.uidata.insert_one(festival)

            created = get_festival_by_id(
                db,
                result.inserted_id
            )

            return jsonify({
                "status": "success",
                "message": "Festival created successfully.",
                "festival": created
            }), 201

        # ----------------------------------------------------
        # UPDATE FESTIVAL
        # ----------------------------------------------------

        if action == "update":

            festival_id = get_object_id(data.get("id"))

            if festival_id is None:

                return jsonify({
                    "status": "error",
                    "error": "A valid festival ID is required."
                }), 400

            try:
                festival = prepare_festival_data(data)

            except ValueError as exc:

                return jsonify({
                    "status": "error",
                    "error": str(exc)
                }), 400

            existing = db.uidata.find_one({
                "_id": festival_id
            })

            if not existing:

                return jsonify({
                    "status": "error",
                    "error": "Festival not found."
                }), 404

            festival["updated_at"] = current_timestamp()

            db.uidata.update_one(
                {
                    "_id": festival_id
                },
                {
                    "$set": festival
                }
            )

            updated = get_festival_by_id(
                db,
                festival_id
            )

            return jsonify({
                "status": "success",
                "message": "Festival updated successfully.",
                "festival": updated
            }), 200

        return jsonify({
            "status": "error",
            "error": "Invalid action."
        }), 400

    except PyMongoError as e:

        print("Festival management error:", e)

        return jsonify({
            "status": "error",
            "error": "Database error. Please try again."
        }), 500


# ============================================================
# TOGGLE FESTIVAL / DELETE FESTIVAL
#
# POST /admin/festivals/<festival_id>
#
# action=toggle
# action=delete
# ============================================================

@admin_bp.route(
    "/admin/festivals/<string:festival_id>",
    methods=["POST"]
)
def admin_festival_action(festival_id):

    admin_user, error = get_admin_from_token()

    if error:
        return error

    object_id = get_object_id(festival_id)

    if object_id is None:

        return jsonify({
            "status": "error",
            "error": "Invalid festival ID."
        }), 400

    data = get_request_data()

    action = data.get("action")

    try:

        db = get_db()

        existing = db.uidata.find_one({
            "_id": object_id
        })

        if not existing:

            return jsonify({
                "status": "error",
                "error": "Festival not found."
            }), 404

        # ----------------------------------------------------
        # ACTIVATE / DEACTIVATE
        # ----------------------------------------------------

        if action == "toggle":

            is_active = data.get("is_active")

            if isinstance(is_active, bool):
                is_active = int(is_active)

            if isinstance(is_active, str) and is_active in ("0", "1"):
                is_active = int(is_active)

            if (
                isinstance(is_active, bool)
                or not isinstance(is_active, int)
                or is_active not in (0, 1)
            ):

                return jsonify({
                    "status": "error",
                    "error": "is_active must be 0 or 1."
                }), 400

            db.uidata.update_one(
                {
                    "_id": object_id
                },
                {
                    "$set": {
                        "is_active": is_active,
                        "updated_at": current_timestamp()
                    }
                }
            )

            festival = get_festival_by_id(
                db,
                object_id
            )

            return jsonify({
                "status": "success",

                "message": (
                    "Festival activated successfully."
                    if is_active
                    else "Festival deactivated successfully."
                ),

                "festival": festival

            }), 200

        # ----------------------------------------------------
        # DELETE FESTIVAL
        # ----------------------------------------------------

        if action == "delete":

            db.uidata.delete_one({
                "_id": object_id
            })

            return jsonify({
                "status": "success",
                "message": "Festival deleted successfully."
            }), 200

        return jsonify({
            "status": "error",
            "error": "Invalid action."
        }), 400

    except PyMongoError as e:

        print("Festival action error:", e)

        return jsonify({
            "status": "error",
            "error": "Database error. Please try again."
        }), 500
