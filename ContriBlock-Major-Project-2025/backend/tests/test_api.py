import json
from backend.app import create_app, db


def setup_app():
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
    return app


def test_health():
    app = setup_app()
    client = app.test_client()
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


