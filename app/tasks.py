# app/tasks.py
"""Background tasks for automatic syncing"""
import logging
from app.models import User
from app.api_clients import get_amber_client, get_tesla_client
from app.tariff_converter import AmberTariffConverter

logger = logging.getLogger(__name__)


def sync_all_users():
    """
    Automatically sync TOU schedules for all configured users
    This runs periodically in the background
    """
    from app import db

    logger.info("=== Starting automatic TOU sync for all users ===")

    # Import here to avoid circular imports
    users = User.query.all()

    if not users:
        logger.info("No users found to sync")
        return

    success_count = 0
    error_count = 0

    for user in users:
        try:
            # Skip users without required configuration
            if not user.amber_api_token_encrypted:
                logger.debug(f"Skipping user {user.email} - no Amber token")
                continue

            if not user.teslemetry_api_key_encrypted:
                logger.debug(f"Skipping user {user.email} - no Teslemetry token")
                continue

            if not user.tesla_energy_site_id:
                logger.debug(f"Skipping user {user.email} - no Tesla site ID")
                continue

            logger.info(f"Syncing schedule for user: {user.email}")

            # Get API clients
            amber_client = get_amber_client(user)
            tesla_client = get_tesla_client(user)

            if not amber_client or not tesla_client:
                logger.warning(f"Failed to get API clients for user {user.email}")
                error_count += 1
                continue

            # Get price forecast (48 hours for better coverage)
            forecast = amber_client.get_price_forecast(next_hours=48)
            if not forecast:
                logger.error(f"Failed to fetch price forecast for user {user.email}")
                error_count += 1
                continue

            # Convert Amber prices to Tesla tariff format
            converter = AmberTariffConverter()
            tariff = converter.convert_amber_to_tesla_tariff(forecast, manual_override=None, user=user)

            if not tariff:
                logger.error(f"Failed to convert tariff for user {user.email}")
                error_count += 1
                continue

            logger.info(f"Applying tariff for {user.email} with {len(tariff.get('energy_charges', {}).get('Summer', {}).get('rates', {}))} rate periods")

            # Apply tariff to Tesla
            result = tesla_client.set_tariff_rate(
                user.tesla_energy_site_id,
                tariff
            )

            if result:
                logger.info(f"✅ Successfully synced schedule for user {user.email}")

                # Update user's last_update timestamp
                from datetime import datetime
                user.last_update_time = datetime.utcnow()
                user.last_update_status = "Auto-sync successful"
                db.session.commit()

                success_count += 1
            else:
                logger.error(f"Failed to apply schedule to Tesla for user {user.email}")
                error_count += 1

        except Exception as e:
            logger.error(f"Error syncing schedule for user {user.email}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            error_count += 1
            continue

    logger.info(f"=== Automatic sync completed: {success_count} successful, {error_count} errors ===")
    return success_count, error_count
