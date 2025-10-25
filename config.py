# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'

    # Use DATABASE_URL if set (for Docker/PostgreSQL), otherwise use SQLite
    # In Docker, this will be /app/data/app.db (persisted in volume)
    # Locally, this will be in the project root directory
    default_db_path = os.path.join(basedir, 'data', 'app.db') if os.path.exists(os.path.join(basedir, 'data')) else os.path.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + default_db_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False
