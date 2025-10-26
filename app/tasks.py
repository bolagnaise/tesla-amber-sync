# app/tasks.py
"""Background tasks for automatic syncing"""
import logging
from datetime import datetime
from app.models import User, PriceRecord
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


def save_price_history():
    """
    Automatically save current Amber prices to database for historical tracking
    This runs periodically in the background to ensure continuous price history
    """
    from app import db

    logger.info("=== Starting automatic price history collection ===")

    users = User.query.all()

    if not users:
        logger.info("No users found for price history collection")
        return

    success_count = 0
    error_count = 0

    for user in users:
        try:
            # Skip users without Amber configuration
            if not user.amber_api_token_encrypted:
                logger.debug(f"Skipping user {user.email} - no Amber token")
                continue

            logger.debug(f"Collecting price history for user: {user.email}")

            # Get Amber client
            amber_client = get_amber_client(user)
            if not amber_client:
                logger.warning(f"Failed to get Amber client for user {user.email}")
                error_count += 1
                continue

            # Get current prices
            prices = amber_client.get_current_prices()
            if not prices:
                logger.warning(f"No current prices available for user {user.email}")
                error_count += 1
                continue

            # Save prices to database
            records_saved = 0
            for price_data in prices:
                try:
                    # Parse NEM time
                    nem_time = datetime.fromisoformat(price_data['nemTime'].replace('Z', '+00:00'))

                    # Check if we already have this exact price record (avoid duplicates)
                    existing = PriceRecord.query.filter_by(
                        user_id=user.id,
                        nem_time=nem_time,
                        channel_type=price_data.get('channelType')
                    ).first()

                    if existing:
                        logger.debug(f"Price record already exists for {user.email} at {nem_time}")
                        continue

                    # Create new price record
                    record = PriceRecord(
                        user_id=user.id,
                        per_kwh=price_data.get('perKwh'),
                        spot_per_kwh=price_data.get('spotPerKwh'),
                        wholesale_kwh_price=price_data.get('wholesaleKWHPrice'),
                        network_kwh_price=price_data.get('networkKWHPrice'),
                        market_kwh_price=price_data.get('marketKWHPrice'),
                        green_kwh_price=price_data.get('greenKWHPrice'),
                        channel_type=price_data.get('channelType'),
                        forecast=price_data.get('forecast', False),
                        nem_time=nem_time,
                        spike_status=price_data.get('spikeStatus'),
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(record)
                    records_saved += 1

                except Exception as e:
                    logger.error(f"Error saving individual price record for {user.email}: {e}")
                    continue

            # Commit all records for this user
            if records_saved > 0:
                db.session.commit()
                logger.info(f"✅ Saved {records_saved} price records for user {user.email}")
                success_count += 1
            else:
                logger.debug(f"No new price records to save for user {user.email}")

        except Exception as e:
            logger.error(f"Error collecting price history for user {user.email}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            error_count += 1
            continue

    logger.info(f"=== Price history collection completed: {success_count} users successful, {error_count} errors ===")
    return success_count, error_count
