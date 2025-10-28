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
import fcntl
import os

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

    # Initialize background scheduler for automatic TOU syncing and price history
    # Use file locking to ensure only ONE worker (in multi-worker setup) runs the scheduler
    lock_file_path = os.path.join(app.instance_path, 'scheduler.lock')
    os.makedirs(app.instance_path, exist_ok=True)

    try:
        # Try to acquire exclusive lock (non-blocking)
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # If we got here, we acquired the lock - this worker will run the scheduler
        logger.info("🔒 This worker acquired the scheduler lock - initializing background scheduler")
        scheduler = BackgroundScheduler()

        # Add job to sync all users' TOU schedules every 5 minutes (aligned with Amber's update cycle)
        from app.tasks import sync_all_users, save_price_history, save_energy_usage

        # Wrapper functions to run tasks within app context
        def run_sync_all_users():
            with app.app_context():
                sync_all_users()

        def run_save_price_history():
            with app.app_context():
                save_price_history()

        def run_save_energy_usage():
            with app.app_context():
                save_energy_usage()

        scheduler.add_job(
            func=run_sync_all_users,
            trigger=CronTrigger(minute='*/5'),
            id='sync_tou_schedules',
            name='Sync TOU schedules from Amber to Tesla',
            replace_existing=True
        )

        # Add job to save price history every 5 minutes for continuous tracking
        scheduler.add_job(
            func=run_save_price_history,
            trigger=CronTrigger(minute='*/5'),
            id='save_price_history',
            name='Save Amber price history to database',
            replace_existing=True
        )

        # Add job to save energy usage every minute for granular tracking (within Teslemetry 1/min limit)
        scheduler.add_job(
            func=run_save_energy_usage,
            trigger=CronTrigger(minute='*'),
            id='save_energy_usage',
            name='Save Tesla energy usage to database',
            replace_existing=True
        )

        # Start the scheduler
        scheduler.start()
        logger.info("✅ Background scheduler started:")
        logger.info("  - TOU sync will run every 5 minutes (Amber updates forecasts every 5 min)")
        logger.info("  - Price history collection will run every 5 minutes")
        logger.info("  - Energy usage logging will run every minute (Teslemetry allows 1/min)")

        # Shut down the scheduler and release lock when exiting the app
        def cleanup():
            scheduler.shutdown()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            logger.info("🔓 Scheduler shut down and lock released")

        atexit.register(cleanup)

    except IOError:
        # Lock already held by another worker - skip scheduler initialization
        logger.info("⏭️  Another worker is running the scheduler - skipping initialization in this worker")

    logger.info("Flask application created successfully")
    return app

