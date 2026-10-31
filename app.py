from flask import Flask, render_template, request, jsonify
from config import SECRET_KEY
from database import init_database
from werkzeug.middleware.proxy_fix import ProxyFix
from routers.auth import auth_bp
from routers.admin import admin_bp
from routers.track import track_bp
from routers.user_dashboard import user_bp
from routers.shared import share_bp
# =========================
# Initialize Extensions
# =========================
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


# Sirf tab use karo jab hosting trusted proxy headers set karti ho.
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1
)
# =========================
# Register Blueprints
# =========================
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(track_bp)
app.register_blueprint(user_bp)
app.register_blueprint(share_bp)
#======================================
#HOME PAGE
#======================================
@app.route("/")
def home():
    return render_template("index.html")



print("urlMap :", app.url_map, flush=True)
#======================================
#MAIN APPLICATION
#======================================
if __name__ == "__main__":
    init_database() 
    app.run(port=5000,host="0.0.0.0", debug=True)
