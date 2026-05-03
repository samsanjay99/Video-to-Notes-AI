import os
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import db

load_dotenv()

def create_app():
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("JWT_SECRET", "change_this_in_production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meetmind"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    CORS(app, origins=["*"], supports_credentials=True)

    # ── Register API blueprints ───────────────────────────────────────────────
    from routes.auth     import auth_bp
    from routes.meetings import meetings_bp
    from routes.upload   import upload_bp
    from routes.export   import export_bp

    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(meetings_bp, url_prefix="/api/meetings")
    app.register_blueprint(upload_bp,   url_prefix="/api/upload")
    app.register_blueprint(export_bp,   url_prefix="/api/export")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        from flask import jsonify
        return jsonify({"status": "ok", "message": "MeetMind API is running"})

    # ── Serve uploaded files ──────────────────────────────────────────────────
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ── Frontend page routes (Jinja2 templates) ───────────────────────────────
    @app.route("/")
    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/register")
    def register_page():
        return render_template("register.html")

    @app.route("/upload")
    def upload_page():
        return render_template("upload.html")

    @app.route("/history")
    def history_page():
        return render_template("history.html")

    @app.route("/meetings/<meeting_id>")
    def meeting_detail_page(meeting_id):
        return render_template("meeting_detail.html", meeting_id=meeting_id)

    @app.route("/shared/<token>")
    def shared_page(token):
        return render_template("shared.html", token=token)

    # ── Create DB tables ──────────────────────────────────────────────────────
    with app.app_context():
        from models.user    import User    # noqa
        from models.meeting import Meeting # noqa
        db.create_all()
        print("✅ Database tables created")

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
