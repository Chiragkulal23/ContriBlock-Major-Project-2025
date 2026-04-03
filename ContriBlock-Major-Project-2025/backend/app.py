import os
import sys

# Ensure project root is on sys.path so 'backend.*' imports work when running from the backend dir
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify
from flask_cors import CORS
from backend.extensions import db, migrate, jwt, socketio
from sqlalchemy import text
from dotenv import load_dotenv

# Extensions are created in backend.extensions


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")
    # Force Flask to run on localhost:5000 if run directly by user request
    app.config["SERVER_NAME"] = None

    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, async_mode="threading")
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired", "message": "Please login again"}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"[JWT] Invalid token error: {error}")
        return jsonify({"error": "Invalid token", "message": str(error)}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"[JWT] Missing token error: {error}")
        return jsonify({"error": "Authorization required", "message": "Please login"}), 401

    from backend.models import user as user_model  # noqa: F401
    from backend.models import contribution as contribution_model  # noqa: F401
    from backend.models import token as token_model  # noqa: F401
    from backend.models import kyc_document as kyc_document_model  # noqa: F401
    from backend.models import purchase as purchase_model  # noqa: F401

    from backend.api import api_bp, init_api
    init_api()
    app.register_blueprint(api_bp, url_prefix="/api")

    # Global OPTIONS handler for all /api routes (helps with preflight on some browsers)
    @app.route('/api/<path:subpath>', methods=['OPTIONS'])
    def api_options(subpath):
        return ("", 204)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # Ensure tables exist (SQLAlchemy only)
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

        # SQLite-safe lightweight migration: ensure KYC columns on users table
        try:
            engine = db.engine
            # Detect existing columns
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(users)"))
                cols = {row[1] for row in result}
                statements = []
                if "kyc_verified" not in cols:
                    statements.append("ALTER TABLE users ADD COLUMN kyc_verified BOOLEAN DEFAULT 0")
                if "kyc_aadhaar_last4" not in cols:
                    statements.append("ALTER TABLE users ADD COLUMN kyc_aadhaar_last4 VARCHAR(4)")
                for stmt in statements:
                    try:
                        conn.execute(text(stmt))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        pass
                
                # Ensure IPFS metadata columns on contributions table
                result = conn.execute(text("PRAGMA table_info(contributions)"))
                contrib_cols = {row[1] for row in result}
                if "ipfs_file_size" not in contrib_cols:
                    conn.execute(text("ALTER TABLE contributions ADD COLUMN ipfs_file_size INTEGER"))
                    conn.commit()
                    print("[App] Added ipfs_file_size column to contributions table")
                if "ipfs_pin_timestamp" not in contrib_cols:
                    conn.execute(text("ALTER TABLE contributions ADD COLUMN ipfs_pin_timestamp VARCHAR(50)"))
                    conn.commit()
                    print("[App] Added ipfs_pin_timestamp column to contributions table")
                if "citations" not in contrib_cols:
                    conn.execute(text("ALTER TABLE contributions ADD COLUMN citations INTEGER DEFAULT 0"))
                    conn.commit()
                    print("[App] Added citations column to contributions table")
                
                # Add index on ipfs_cid if it doesn't exist
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_contributions_ipfs_cid ON contributions(ipfs_cid)"))
                    conn.commit()
                    print("[App] Added index on ipfs_cid column")
                except Exception as e:
                    print(f"[App] Could not create ipfs_cid index: {e}")
            
            # Ensure kyc_documents table exists and has verified_email column
            try:
                db.create_all()
                # Check if kyc_documents table exists and add verified_email column if missing
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text("PRAGMA table_info(kyc_documents)"))
                        kyc_cols = {row[1] for row in result}
                        if "verified_email" not in kyc_cols:
                            conn.execute(text("ALTER TABLE kyc_documents ADD COLUMN verified_email VARCHAR(255)"))
                            conn.commit()
                            print("[App] Added verified_email column to kyc_documents table")
                except Exception as e:
                    # Table might not exist yet, db.create_all should handle it
                    print(f"[App] Could not check kyc_documents table: {e}")
                
                print("[App] Database tables ensured")
            except Exception as e:
                print(f"[App] Database check: {e}")
        except Exception:
            # Best-effort; if this fails, migrations can handle it
            pass

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    socketio.run(app, host="0.0.0.0", port=port)


