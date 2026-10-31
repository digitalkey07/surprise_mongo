
from flask import (
    Blueprint,
    request,
    jsonify,
    render_template
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from pymongo.errors import DuplicateKeyError, PyMongoError

from database import get_db
from utils.validator import create_token


auth_bp = Blueprint("auth", __name__)


# ======================================
# LOGIN API
# ======================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    # JSON data receive
    data = request.get_json(silent=True) or {}

    username = data.get("username", "")
    password = data.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "status": "error",
            "error": "Invalid input."
        }), 400

    username = username.strip().lower()

    if not username or not password:
        return jsonify({
            "status": "error",
            "error": "Username and password are required."
        }), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({
            "status": "error",
            "error": "Invalid username."
        }), 400

    if len(password) < 8:
        return jsonify({
            "status": "error",
            "error": "Invalid username or password."
        }), 401

    try:

        db = get_db()

        # Find user
        user = db.users.find_one(
            {"username": username},
            {   "_id":1,
                "username": 1,
                "password": 1,
                "user_type": 1,
                "is_verify":1
            }
        )
       

        # Username/password verify
        if not user or not check_password_hash(
            user["password"], password
        ):
            return jsonify({
                "status": "error",
                "error": "Invalid username or password."
            }), 401
       
        if not user.get("is_verify", False):
            return jsonify({
                "status": "error",
                "error": "Please Check your Mail and Verify"
            }), 401
   
        # Token data
        token_data = {
            "id": str(user["_id"])
        }

        # Encrypted token create
        token = create_token(token_data)

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "token": token,
            "user": {
                "username": user["username"],
                "user_type": user["user_type"]
            }
        }), 200

    except PyMongoError:
        return jsonify({
            "status": "error",
            "error": "Database error. Please try again."
        }), 500


# ======================================
# REGISTER API
# ======================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    # JSON data receive
    data = request.get_json(silent=True) or {}

    username = data.get("username", "")
    password = data.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "status": "error",
            "error": "Invalid input."
        }), 400

    username = username.strip().lower()

    if not username or not password:
        return jsonify({
            "status": "error",
            "error": "Username and password are required."
        }), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({
            "status": "error",
            "error": "Username must be 3 to 50 characters."
        }), 400

    if len(password) < 8:
        return jsonify({
            "status": "error",
            "error": "Password must be at least 8 characters."
        }), 400

    # Password hash
    password_hash = generate_password_hash(password)

    # Default user role
    user_type = "user"

 

    try:

        db = get_db()

        # Insert user
        result = db.users.insert_one({
            "username": username,
            "password": password_hash,
            "user_type": user_type,
            "is_verify":False
        })
        # send_mail(username);
        return jsonify({
            "status": "success",
            "message": "Registration successful.",
            "user": {
                "id": str(result.inserted_id),
                "username": username,
                "user_type": user_type
            }
        }), 201

    except DuplicateKeyError:

        return jsonify({
            "status": "error",
            "error": "Username already exists."
        }), 409

    except PyMongoError:

        return jsonify({
            "status": "error",
            "error": "Database error. Please try again."
        }), 500


# ======================================
# LOGOUT API
# ======================================

@auth_bp.route("/logout", methods=["POST"])
def logout():

    return jsonify({
        "status": "success",
        "message": "Logout successfully"
    }), 200
