from flask import Blueprint

bp = Blueprint("processes", __name__)

from app.processes import api, management, routes
