"""
This provides some low-level things to make our HTTP life easier.
"""
import re
from functools import wraps

from typing import Dict, List

# noinspection PyPackageRequirements
from flask import abort, after_this_request, g, jsonify, request

from .data import DBObject, User

digits = re.compile(r"^\d+$")


def error(code, reason):
    """
    This sets up flask to return an error.

    :param code: the HTTP status code to return with the error.
    :param reason: the text of the error message to return.
    """

    def set_code(response):
        response.status_code = code
        return response

    after_this_request(set_code)

    return {"error": reason, "code": code}

def safe_delete(key, data: dict):
    try:
        del data[key]
    except KeyError:
        pass

def _make_json_ready(obj):
    if isinstance(obj, DBObject):
        data = obj.to_dict()
        for key in obj.json_excludes:
            safe_delete(key, data)
        obj = data
    elif isinstance(obj, Dict):
        for key, value in obj.items():
            obj[key] = _make_json_ready(value)
    elif isinstance(obj, List):
        obj = [_make_json_ready(item) for item in obj]
    return obj


def endpoint(
    authenticated: bool = False,
    auth_optional: bool = False,
    cls=None,
    writes_json: bool = False,
):
    def decorator(function):
        @wraps(function)
        def wrapper(object_id=None, *args, **kwargs):
            if authenticated:
                auth = request.headers.get("Authorization")
                user = None
                if auth is not None and auth.startswith("Key "):
                    user = User.get_user_by_api_key(auth[4:])

                if user is None and not auth_optional:
                    abort(401)

                g.user = user

            if cls is None:
                result = _make_json_ready(function(*args, **kwargs))
            else:
                if digits.match(object_id):
                    object_id = int(object_id)
                item = cls.get_object(object_id)
                if item is None:
                    result = error(404, "%s with ID %s not found." % (cls.__name__, object_id))
                else:
                    result = _make_json_ready(function(item, *args, **kwargs))

            if writes_json:
                result = jsonify(result)

            return result

        return wrapper

    return decorator
