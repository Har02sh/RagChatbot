from flask import Flask
from .config import Config
from .extensions import db, login_manager
from .routes import main_blueprint, chat_blueprint
from .model import User
# from app.chat.routes import chat_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    with app.app_context():
        db.create_all()  # Create database tables

    # Register blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(chat_blueprint)

    return app
