# app/__init__.py
from flask import Flask, request
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import atexit

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'main.login' # Redirect to login page if user is not authenticated

def create_app(config_class=Config):
    logger.info("Creating Flask application")
    app = Flask(__name__)
    app.config.from_object(config_class)

    logger.info("Initializing database and extensions")
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Run migrations check (version upgrades, SECRET_KEY changes, etc.)
    from app.migrations_handler import run_migrations
    run_migrations(app, app.config['SECRET_KEY'])

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    logger.info("Blueprint registered")

    # Add request logging
    @app.before_request
    def log_request():
        logger.info(f"REQUEST: {request.method} {request.path} from {request.remote_addr}")

    @app.after_request
    def log_response(response):
        logger.info(f"RESPONSE: {request.method} {request.path} -> {response.status_code}")
        return response

    # Initialize background scheduler for automatic TOU syncing
    logger.info("Initializing background scheduler for automatic TOU sync")
    scheduler = BackgroundScheduler()

    # Add job to sync all users' TOU schedules at :00 and :30 of every hour (aligned with Amber's update cycle)
    from app.tasks import sync_all_users
    scheduler.add_job(
        func=sync_all_users,
        trigger=CronTrigger(minute='0,30'),
        id='sync_tou_schedules',
        name='Sync TOU schedules from Amber to Tesla',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started - TOU sync will run at :00 and :30 of every hour")

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    logger.info("Flask application created successfully")
    return app

