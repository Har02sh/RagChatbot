from . import main_blueprint
from flask import render_template, url_for, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from app.model import User
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
import re


@main_blueprint.route('/')
@login_required
def home():
    return render_template('main.html', name=current_user.name, email=current_user.email)


@main_blueprint.route('/auth')
def auth():
    return render_template("auth.html")
    

@main_blueprint.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Email and password are required."}), 400
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        login_user(user, remember=True)
        return jsonify({"success": True, "message": "Login successful!", "redirect_url":url_for('main.home')}), 200
    else:
        return jsonify({"success": False, "message": "Invalid email or password."}), 401


@main_blueprint.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data or 'name' not in data:
        return jsonify({"success": False, "message": "All fields are required."}), 400
    
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"success": False, "message": "Invalid email format"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password too short"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 409
    
    try:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, password=hashed_password, name=name)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"success": True, "message": "Signup successful!"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Internal server error. Please try again later."}), 500


@main_blueprint.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Logout successful!", "redirect": url_for('main.auth')}), 200