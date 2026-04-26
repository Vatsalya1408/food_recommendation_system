from flask import Flask
from flask_cors import CORS
from pathlib import Path
from app.data_loader import load_food_database

def create_app():
    # Configure template and static folders (relative to project root)
    base_dir = Path(__file__).parent.parent
    template_dir = base_dir / 'templates'
    static_dir = base_dir / 'static'

    app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))
    CORS(app)

    # Load databases
    data_dir = Path(__file__).parent.parent / 'data'
    app.food_db = load_food_database(str(data_dir))

    # Register routes
    from app.routes import bp
    app.register_blueprint(bp)

    return app
