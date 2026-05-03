import os
import logging
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import db

load_dotenv()

# Configure logging so Render shows our messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


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

    # ── Create DB tables (safe: drops stale schema if columns mismatch) ───────
    with app.app_context():
        from models.user    import User    # noqa
        from models.meeting import Meeting # noqa
        _safe_create_tables()

    return app


def _safe_create_tables():
    """
    Create tables if they don't exist.
    If the existing schema is missing expected columns (stale deploy),
    drop everything and recreate cleanly.
    """
    from sqlalchemy import text, inspect
    engine = db.engine

    try:
        # Quick schema sanity check — verify 'name' column exists on users
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "users" in tables:
            cols = [c["name"] for c in inspector.get_columns("users")]
            if "name" not in cols:
                log.warning("Stale schema detected (missing 'name' column) — rebuilding tables")
                _drop_all_cascade(engine)
        db.create_all()
        log.info("✅ Database tables ready")
    except Exception as e:
        log.error("DB init error: %s — attempting full rebuild", e)
        try:
            _drop_all_cascade(engine)
            db.create_all()
            log.info("✅ Database tables rebuilt successfully")
        except Exception as e2:
            log.error("DB rebuild failed: %s", e2)
            raise


def _drop_all_cascade(engine):
    """Drop all app tables. Only runs on PostgreSQL (not SQLite)."""
    dialect = engine.dialect.name
    if dialect != "postgresql":
        log.warning("_drop_all_cascade skipped for dialect: %s", dialect)
        return
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS action_items  CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS meetings      CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users         CASCADE"))
        conn.execute(text("DROP TYPE  IF EXISTS meeting_status CASCADE"))
        conn.execute(text("DROP TYPE  IF EXISTS user_role      CASCADE"))
        conn.commit()
    log.info("All old tables dropped with CASCADE")


# Module-level app instance for gunicorn (gunicorn app:app)
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
