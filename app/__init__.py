from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import logging

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('flask.log')
        ]
    )
    logger = logging.getLogger(__name__)
    logger.debug("create_app called")
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///game_checklist.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    logger.debug("Initializing database and login manager")
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    logger.debug("Registering blueprints")
    from app.routes import main_bp, auth_bp, checklist_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(checklist_bp)
    
    # Create database tables
    logger.debug("Creating database tables")
    with app.app_context():
        db.create_all()
    
    logger.debug("Application created successfully")
    return app
