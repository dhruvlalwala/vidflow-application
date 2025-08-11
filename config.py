import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv() 

# Get the absolute path of your main project folder (VIDFLOW).
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Base configuration class for the application.
    Settings are loaded from environment variables for security, with sensible defaults for development.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key-you-should-change'
    
    # --- NEW: AZURE DATABASE CONFIGURATION ---
    # Construct the database URI from environment variables
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_name = 'postgres' # Default database name
    
    # Check if the database environment variables are set
    if db_user and db_pass and db_host:
        SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_pass}@{db_host}/{db_name}"
    else:
        # Fallback to local SQLite database if environment variables are not set
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'site.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- File Upload Paths (No changes needed here) ---
    STATIC_FOLDER = os.path.join(basedir, 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')
    PROFILE_PICS_FOLDER = os.path.join(STATIC_FOLDER, 'profile_pics')
    STORY_PICS_FOLDER = os.path.join(STATIC_FOLDER, 'story_pics')
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

# --- Function to create directories (No changes needed here) ---
def create_upload_directories():
    """
    Function to ensure all necessary upload directories exist.
    """
    for folder in [Config.UPLOAD_FOLDER, Config.PROFILE_PICS_FOLDER, Config.STORY_PICS_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created directory: {folder}")

create_upload_directories()