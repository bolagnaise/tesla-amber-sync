# app/tasks.py
"""Background tasks for automatic syncing"""
import logging
from datetime import datetime
from app.models import User, PriceRecord, EnergyRecord, SavedTOUProfile
from app.api_clients import get_amber_client, get_tesla_client, AEMOAPIClient
from app.tariff_converter import AmberTariffConverter
import json

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
            # Skip users who have disabled syncing
            if not user.sync_enabled:
                logger.debug(f"Skipping user {user.email} - syncing disabled")
                continue

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


def save_energy_usage():
    """
    Automatically save Tesla Powerwall energy usage data to database for historical tracking
    This runs periodically in the background to capture solar, grid, battery, and load power
    """
    from app import db

    logger.debug("=== Starting automatic energy usage collection ===")

    users = User.query.all()

    if not users:
        logger.debug("No users found for energy usage collection")
        return

    success_count = 0
    error_count = 0

    for user in users:
        try:
            # Skip users without Tesla configuration
            if not user.tesla_energy_site_id:
                logger.debug(f"Skipping user {user.email} - no Tesla site ID")
                continue

            logger.debug(f"Collecting energy usage for user: {user.email}")

            # Get Tesla client
            tesla_client = get_tesla_client(user)
            if not tesla_client:
                logger.warning(f"Failed to get Tesla client for user {user.email}")
                error_count += 1
                continue

            # Get site status (contains power flow data)
            site_status = tesla_client.get_site_status(user.tesla_energy_site_id)
            if not site_status:
                logger.warning(f"No site status available for user {user.email}")
                error_count += 1
                continue

            # Extract power data (in watts)
            solar_power = site_status.get('solar_power', 0.0)
            battery_power = site_status.get('battery_power', 0.0)
            grid_power = site_status.get('grid_power', 0.0)
            load_power = site_status.get('load_power', 0.0)
            battery_level = site_status.get('percentage_charged', 0.0)

            # Create energy record
            record = EnergyRecord(
                user_id=user.id,
                solar_power=solar_power,
                battery_power=battery_power,
                grid_power=grid_power,
                load_power=load_power,
                battery_level=battery_level,
                timestamp=datetime.utcnow()
            )

            db.session.add(record)
            db.session.commit()

            logger.debug(f"✅ Saved energy record for user {user.email}: Solar={solar_power}W Grid={grid_power}W Battery={battery_power}W Load={load_power}W")
            success_count += 1

        except Exception as e:
            logger.error(f"Error collecting energy usage for user {user.email}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            error_count += 1
            continue

    logger.debug(f"=== Energy usage collection completed: {success_count} users successful, {error_count} errors ===")
    return success_count, error_count


def monitor_aemo_prices():
    """
    Monitor AEMO NEM wholesale electricity prices and trigger spike mode when threshold exceeded

    Flow:
    1. Check AEMO price for user's region
    2. If price >= threshold AND not in spike mode:
       - Save current Tesla tariff as backup
       - Upload spike tariff (very high sell rates to encourage export)
       - Mark user as in_spike_mode
    3. If price < threshold AND in spike mode:
       - Restore saved tariff from backup
       - Mark user as not in_spike_mode
    """
    from app import db

    logger.info("=== Starting AEMO price monitoring ===")

    users = User.query.filter_by(aemo_spike_detection_enabled=True).all()

    if not users:
        logger.debug("No users with AEMO spike detection enabled")
        return

    # Initialize AEMO client (no auth required)
    aemo_client = AEMOAPIClient()

    success_count = 0
    error_count = 0

    for user in users:
        try:
            # Validate user configuration
            if not user.aemo_region:
                logger.warning(f"User {user.email} has AEMO enabled but no region configured")
                continue

            if not user.tesla_energy_site_id or not user.teslemetry_api_key_encrypted:
                logger.warning(f"User {user.email} has AEMO enabled but missing Tesla configuration")
                continue

            logger.info(f"Checking AEMO prices for user: {user.email} (Region: {user.aemo_region})")

            # Check current price vs threshold
            is_spike, current_price, price_data = aemo_client.check_price_spike(
                user.aemo_region,
                user.aemo_spike_threshold or 300.0
            )

            if current_price is None:
                logger.error(f"Failed to fetch AEMO price for {user.email}")
                error_count += 1
                continue

            # Update user's last check data
            user.aemo_last_check = datetime.utcnow()
            user.aemo_last_price = current_price

            # Get Tesla client
            tesla_client = get_tesla_client(user)
            if not tesla_client:
                logger.error(f"Failed to get Tesla client for {user.email}")
                error_count += 1
                continue

            # SPIKE DETECTED - Enter spike mode
            if is_spike and not user.aemo_in_spike_mode:
                logger.warning(f"🚨 SPIKE DETECTED for {user.email}: ${current_price}/MWh >= ${user.aemo_spike_threshold}/MWh")

                # Step 1: Save current Tesla tariff as backup
                logger.info(f"Saving current Tesla tariff as backup for {user.email}")
                current_tariff = tesla_client.get_current_tariff(user.tesla_energy_site_id)

                if current_tariff:
                    # Save to database
                    backup_profile = SavedTOUProfile(
                        user_id=user.id,
                        name=f"Pre-Spike Backup - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                        description=f"Automatic backup before AEMO spike at ${current_price}/MWh",
                        source_type='aemo_backup',
                        tariff_name=current_tariff.get('name', 'Unknown'),
                        utility=current_tariff.get('utility', 'Unknown'),
                        tariff_json=json.dumps(current_tariff),
                        created_at=datetime.utcnow(),
                        fetched_from_tesla_at=datetime.utcnow()
                    )
                    db.session.add(backup_profile)
                    db.session.flush()  # Get the ID

                    user.aemo_saved_tariff_id = backup_profile.id
                    logger.info(f"✅ Saved backup tariff ID {backup_profile.id} for {user.email}")
                else:
                    logger.error(f"Failed to fetch current tariff for backup - {user.email}")

                # Step 2: Create and upload spike tariff
                logger.info(f"Creating spike tariff for {user.email}")
                spike_tariff = create_spike_tariff(current_price)

                result = tesla_client.set_tariff_rate(user.tesla_energy_site_id, spike_tariff)

                if result:
                    user.aemo_in_spike_mode = True
                    user.aemo_spike_start_time = datetime.utcnow()
                    logger.info(f"✅ Entered spike mode for {user.email} - uploaded spike tariff")
                    success_count += 1
                else:
                    logger.error(f"Failed to upload spike tariff for {user.email}")
                    error_count += 1

            # NO SPIKE - Exit spike mode if currently in it
            elif not is_spike and user.aemo_in_spike_mode:
                logger.info(f"✅ Price normalized for {user.email}: ${current_price}/MWh < ${user.aemo_spike_threshold}/MWh")

                # Restore saved tariff
                if user.aemo_saved_tariff_id:
                    logger.info(f"Restoring backup tariff ID {user.aemo_saved_tariff_id} for {user.email}")
                    backup_profile = SavedTOUProfile.query.get(user.aemo_saved_tariff_id)

                    if backup_profile:
                        tariff = json.loads(backup_profile.tariff_json)
                        result = tesla_client.set_tariff_rate(user.tesla_energy_site_id, tariff)

                        if result:
                            user.aemo_in_spike_mode = False
                            user.aemo_spike_start_time = None
                            backup_profile.last_restored_at = datetime.utcnow()
                            logger.info(f"✅ Exited spike mode for {user.email} - restored backup tariff")
                            success_count += 1
                        else:
                            logger.error(f"Failed to restore backup tariff for {user.email}")
                            error_count += 1
                    else:
                        logger.error(f"Backup tariff ID {user.aemo_saved_tariff_id} not found for {user.email}")
                        user.aemo_in_spike_mode = False  # Exit spike mode anyway
                        error_count += 1
                else:
                    logger.warning(f"No backup tariff saved for {user.email}, exiting spike mode anyway")
                    user.aemo_in_spike_mode = False
                    success_count += 1

            # ONGOING SPIKE or ONGOING NORMAL - No action needed
            else:
                if is_spike:
                    logger.debug(f"Price still spiking for {user.email}: ${current_price}/MWh (in spike mode)")
                else:
                    logger.debug(f"Price normal for {user.email}: ${current_price}/MWh (not in spike mode)")
                success_count += 1

            # Commit user updates
            db.session.commit()

        except Exception as e:
            logger.error(f"Error monitoring AEMO price for user {user.email}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            error_count += 1
            continue

    logger.info(f"=== AEMO monitoring completed: {success_count} users successful, {error_count} errors ===")
    return success_count, error_count


def create_spike_tariff(current_aemo_price_mwh):
    """
    Create a Tesla tariff optimized for exporting during price spikes

    Args:
        current_aemo_price_mwh: Current AEMO price in $/MWh (e.g., 500)

    Returns:
        dict: Tesla tariff JSON with very high sell rates
    """
    # Convert $/MWh to $/kWh (divide by 1000)
    # Add 20% margin to encourage export
    sell_rate = (current_aemo_price_mwh / 1000.0) * 1.2

    # Very low buy rate to discourage import
    buy_rate = 0.01

    logger.info(f"Creating spike tariff: Buy=${buy_rate}/kWh, Sell=${sell_rate}/kWh (based on ${current_aemo_price_mwh}/MWh)")

    # Build rates dictionaries for all 48 x 30-minute periods (24 hours)
    buy_rates = {}
    sell_rates = {}
    tou_periods = {}

    for i in range(48):
        hour = i // 2
        minute = 30 if i % 2 else 0
        period_name = f"{hour:02d}:{minute:02d}"

        # Rates are simple floats, not objects
        buy_rates[period_name] = buy_rate
        sell_rates[period_name] = sell_rate

        # Calculate end time (30 minutes later)
        if minute == 0:
            to_hour = hour
            to_minute = 30
        else:  # minute == 30
            to_hour = (hour + 1) % 24  # Wrap around at midnight
            to_minute = 0

        # TOU period definition for seasons
        tou_periods[period_name] = {
            "fromDayOfWeek": 0,
            "toDayOfWeek": 6,
            "fromHour": hour,
            "fromMinute": minute,
            "toHour": to_hour,
            "toMinute": to_minute
        }

    # Create Tesla tariff structure with separate buy and sell tariffs
    tariff = {
        "name": f"AEMO Spike - ${current_aemo_price_mwh}/MWh",
        "utility": "AEMO",
        "code": f"SPIKE_{int(current_aemo_price_mwh)}",
        "currency": "AUD",
        "daily_charges": [{"name": "Supply Charge"}],
        "demand_charges": {
            "ALL": {"rates": {"ALL": 0}},
            "Summer": {},
            "Winter": {}
        },
        "energy_charges": {
            "ALL": {"rates": {"ALL": 0}},
            "Summer": {"rates": buy_rates},
            "Winter": {}
        },
        "seasons": {
            "Summer": {
                "fromMonth": 1,
                "toMonth": 12,
                "fromDay": 1,
                "toDay": 31,
                "tou_periods": tou_periods
            },
            "Winter": {
                "fromDay": 0,
                "toDay": 0,
                "fromMonth": 0,
                "toMonth": 0,
                "tou_periods": {}
            }
        },
        "sell_tariff": {
            "name": f"AEMO Spike Feed-in - ${current_aemo_price_mwh}/MWh",
            "utility": "AEMO",
            "daily_charges": [{"name": "Charge"}],
            "demand_charges": {
                "ALL": {"rates": {"ALL": 0}},
                "Summer": {},
                "Winter": {}
            },
            "energy_charges": {
                "ALL": {"rates": {"ALL": 0}},
                "Summer": {"rates": sell_rates},
                "Winter": {}
            },
            "seasons": {
                "Summer": {
                    "fromMonth": 1,
                    "toMonth": 12,
                    "fromDay": 1,
                    "toDay": 31,
                    "tou_periods": tou_periods
                },
                "Winter": {
                    "fromDay": 0,
                    "toDay": 0,
                    "fromMonth": 0,
                    "toMonth": 0,
                    "tou_periods": {}
                }
            }
        }
    }

    return tariff
