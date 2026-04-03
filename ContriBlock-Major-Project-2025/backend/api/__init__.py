from flask import Blueprint

api_bp = Blueprint("api", __name__)


def init_api():
    # Import routes to attach handlers to api_bp before registration
    from . import auth, contributions, marketplace, profile, blockchain  # noqa: F401,E402
    from . import kyc, dashboard  # noqa: F401,E402


