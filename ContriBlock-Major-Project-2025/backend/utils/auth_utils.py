from flask_jwt_extended import jwt_required


def auth_required(fn):
    return jwt_required()(fn)


