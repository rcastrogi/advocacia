from flask import Blueprint

bp = Blueprint("oab_validation", __name__)

from app.oab_validation import routes
