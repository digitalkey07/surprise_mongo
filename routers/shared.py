
from flask import (
    Blueprint,
    render_template,
    abort,
    jsonify
)

from bson import ObjectId
from pymongo.errors import PyMongoError

from database import get_db


share_bp = Blueprint("share", __name__)


# ============================================================
# OPEN SHARE LINK
# ============================================================

@share_bp.route(
    "/share/<string:user_id>/<string:ui_id>",
    methods=["GET"]
)
def open_share_link(user_id, ui_id):

    # Validate both IDs
    if (
        not ObjectId.is_valid(user_id)
        or not ObjectId.is_valid(ui_id)
    ):
        abort(400, description="Invalid request")

    try:

        db = get_db()

        user_object_id = ObjectId(user_id)
        ui_object_id = ObjectId(ui_id)

        # ----------------------------------------------------
        # 1. FIND SHARE OWNER
        # ----------------------------------------------------

        user = db.users.find_one(
            {
                "_id": user_object_id
            },
            {
                "_id": 1
            }
        )

        if user is None:
            abort(404, description="Invalid or expired share link")

        # ----------------------------------------------------
        # 2. FIND ACTIVE UI DATA
        # ----------------------------------------------------

        festival = db.uidata.find_one({
            "_id": ui_object_id,
            "is_active": 1
        })

        if festival is None:
            abort(404, description="UI not found or inactive")

        # ----------------------------------------------------
        # 3. CONVERT OBJECTID TO STRING
        # ----------------------------------------------------

        user_id = str(user["_id"])
        ui_id = str(festival["_id"])

        festival["_id"] = ui_id

        # ----------------------------------------------------
        # 4. RENDER SHARED PAGE
        # ----------------------------------------------------

        return render_template(
            "shared_page.html",
            user_id=user_id,
            ui_id=ui_id,
            festival=festival
        )

    except PyMongoError as e:

        print("Share link database error:", e)

        abort(500, description="Database error")


# ============================================================
# GET UI DATA API
# ============================================================

@share_bp.route(
    "/ui/<string:ui_id>",
    methods=["GET"]
)
def get_ui_data(ui_id):

    if not ObjectId.is_valid(ui_id):

        return jsonify({
            "status": "error",
            "message": "Invalid UI ID"
        }), 400

    try:

        db = get_db()

        festival = db.uidata.find_one({
            "_id": ObjectId(ui_id),
            "is_active": 1
        })

        if festival is None:

            return jsonify({
                "status": "error",
                "message": "UI not found or inactive"
            }), 404

        # MongoDB ObjectId JSON-compatible string
        festival["_id"] = str(festival["_id"])

        return jsonify({
            "status": "success",
            **festival
        }), 200

    except PyMongoError as e:

        print("UI database error:", e)

        return jsonify({
            "status": "error",
            "message": "Database error. Please try again."
        }), 500
