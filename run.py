# # run.py
# from app import app, db

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=True)
from app import create_app, db

# Create the Flask app instance using the factory pattern from our 'app' package.
app = create_app()

# This block ensures that the script runs only when executed directly
# (not when imported) and that the app context is available for db operations.
if __name__ == '__main__':
    with app.app_context():
        # Create all database tables if they don't exist yet.
        # This is safe to run every time; it won't overwrite existing tables.
        db.create_all()
    
    # Run the Flask development server.
    # debug=True enables auto-reloading on code changes and provides helpful error pages.
    app.run(debug=True)
