from functools import wraps

from authlib.jose import jwt
from flask import request

from config import Config
from logger import log
from models.machine import Machine


def api_access_token_required(f):
    @wraps(f)
    def decorator(self, *args, **kwargs):
        try:
            data = jwt.decode(
                request.headers.get("Authorization").split(" ")[-1], Config.SECRET
            )
            current_machine = Machine.get(data["machine"])
        except Exception as e:
            log.exception(e)
            return "Unauthorized", 401

        return f(self, current_machine, *args, **kwargs)

    return decorator
