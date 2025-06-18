from flask import Blueprint

main_blueprint = Blueprint('main', __name__)
chat_blueprint = Blueprint('chat', __name__)

from . import main_routes, chat_routes
