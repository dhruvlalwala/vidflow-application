import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config

# Initialize extensions here without a specific app instance.
# They will be connected to the app inside the create_app factory.
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Configure Flask-Login. This tells the extension where to redirect users
# who try to access a page that requires them to be logged in.
# 'main.login' refers to the 'login' function inside the 'main' Blueprint.
login_manager.login_view = 'main.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """
    Creates and configures the Flask application instance.
    This is the Application Factory pattern, which is a best practice for Flask.
    """
    # We explicitly tell Flask where to find the templates and static folders.
    # The paths are relative to this file's location inside the 'app' folder.
    # '../templates' means "go up one level from 'app', then into 'templates'".
    app = Flask(__name__,
                instance_relative_config=True,
                template_folder='../templates',
                static_folder='../static')

    # Load the configuration settings from the config.py file.
    app.config.from_object(config_class)

    # Ensure the 'instance' folder exists at the project root.
    # This folder is a safe place to store files that shouldn't be in version control,
    # like your database file.
    try:
        os.makedirs(app.instance_path)
    except OSError:
        # The folder already exists, so we can ignore the error.
        pass

    # Connect the extensions to our Flask app instance.
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Import and register the Blueprint from our routes file.
    # Blueprints are used to organize a group of related routes into a module.
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Note: The upload directories are now created automatically when the
    # `config` module is imported and the `create_upload_directories()`
    # function is run, so we've removed the redundant code here.

    return app
