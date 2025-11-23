from flask import Blueprint

bp = Blueprint("petitions", __name__)

from app.petitions import routes
