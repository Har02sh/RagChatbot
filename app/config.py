from datetime import timedelta
import os

class Config:
    SECRET_KEY = 'dev_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    REMEMBER_COOKIE_DURATION = timedelta(minutes=5) 
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    UPLOAD_FOLDER = r"/Users/harshvardhan/RagChatbot/Uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)