# app/routes.py
from flask import render_template, flash, redirect, url_for, request, Blueprint, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, PriceRecord
from app.forms import LoginForm, RegistrationForm, SettingsForm, EnvironmentForm, DemandChargeForm
from app.utils import encrypt_token, decrypt_token
from app.api_clients import get_amber_client, get_tesla_client
from app.scheduler import TOUScheduler
import os
import requests
import time
import logging
from datetime import datetime

def get_tesla_config(user=None):
    """
    Get Tesla OAuth configuration from database (user settings) or environment variables (fallback).

    Priority:
    1. User's database settings (if user is logged in)
    2. Environment variables (backward compatibility)
    3. Default values

    Args:
        user: Current user object (optional, defaults to current_user if in request context)

    Returns:
        dict: Dictionary with tesla_client_id, tesla_client_secret, tesla_redirect_uri, app_domain
    """
    config = {
        'tesla_client_id': None,
        'tesla_client_secret': None,
        'tesla_redirect_uri': None,
        'app_domain': None
    }

    # Use provided user or current_user
    if user is None:
        try:
            user = current_user if current_user.is_authenticated else None
        except:
            user = None

    # Try to get from database first
    if user and user.is_authenticated:
        try:
            if user.tesla_client_id_encrypted:
                config['tesla_client_id'] = decrypt_token(user.tesla_client_id_encrypted)
            if user.tesla_client_secret_encrypted:
                config['tesla_client_secret'] = decrypt_token(user.tesla_client_secret_encrypted)
            if user.tesla_redirect_uri:
                config['tesla_redirect_uri'] = user.tesla_redirect_uri
            if user.app_domain:
                config['app_domain'] = user.app_domain
        except Exception as e:
            logger.error(f"Error reading Tesla config from database: {e}")

    # Fallback to environment variables
    if not config['tesla_client_id']:
        config['tesla_client_id'] = os.environ.get('TESLA_CLIENT_ID')
    if not config['tesla_client_secret']:
        config['tesla_client_secret'] = os.environ.get('TESLA_CLIENT_SECRET')
    if not config['tesla_redirect_uri']:
        config['tesla_redirect_uri'] = os.environ.get('TESLA_REDIRECT_URI')
    if not config['app_domain']:
        config['app_domain'] = os.environ.get('APP_DOMAIN', request.host_url.rstrip('/') if request else None)

    return config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    logger.info("Index page accessed")
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"Login page accessed - Method: {request.method}")
    if current_user.is_authenticated:
        logger.info(f"User already authenticated: {current_user.email}")
        return redirect(url_for('main.dashboard'))

    # Check if registration should be allowed (single-user mode)
    allow_registration = User.query.count() == 0

    form = LoginForm()
    if form.validate_on_submit():
        logger.info(f"Login form submitted for email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            logger.warning(f"Failed login attempt for email: {form.email.data}")
            flash('Invalid email or password')
            return redirect(url_for('main.login'))
        logger.info(f"Successful login for user: {user.email}")
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', title='Sign In', form=form, allow_registration=allow_registration)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Check if any users already exist (single-user mode)
    existing_user_count = User.query.count()
    if existing_user_count > 0:
        logger.warning(f"Registration attempt blocked - user already exists (count: {existing_user_count})")
        flash('Registration is disabled. This application only supports a single user account.')
        return redirect(url_for('main.login'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Double-check in case of race condition
        if User.query.count() > 0:
            logger.warning("Registration blocked during form submission - user already exists")
            flash('Registration is disabled. A user account already exists.')
            return redirect(url_for('main.login'))

        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        logger.info(f"First user account created: {user.email}")
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@bp.route('/dashboard')
@login_required
def dashboard():
    logger.info(f"Dashboard accessed by user: {current_user.email}")
    return render_template('dashboard.html', title='Dashboard')


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    logger.info(f"Settings page accessed by user: {current_user.email} - Method: {request.method}")
    form = SettingsForm()
    if form.validate_on_submit():
        logger.info(f"Settings form submitted by user: {current_user.email}")

        if form.amber_token.data:
            logger.info("Encrypting and saving Amber API token")
            current_user.amber_api_token_encrypted = encrypt_token(form.amber_token.data)

        if form.tesla_site_id.data:
            logger.info(f"Saving Tesla Site ID: {form.tesla_site_id.data}")
            current_user.tesla_energy_site_id = form.tesla_site_id.data

        if form.teslemetry_api_key.data:
            logger.info("Encrypting and saving Teslemetry API key")
            current_user.teslemetry_api_key_encrypted = encrypt_token(form.teslemetry_api_key.data)

        try:
            db.session.commit()
            logger.info("Settings saved successfully to database")
            flash('Your settings have been saved.')
        except Exception as e:
            logger.error(f"Error saving settings to database: {e}")
            flash('Error saving settings. Please try again.')
            db.session.rollback()

        return redirect(url_for('main.settings'))

    # Pre-populate form with existing data (decrypted)
    logger.debug("Decrypting and pre-populating form data")
    try:
        form.amber_token.data = decrypt_token(current_user.amber_api_token_encrypted)
        logger.debug(f"Amber token decrypted: {'Yes' if form.amber_token.data else 'No'}")
    except Exception as e:
        logger.error(f"Error decrypting amber token: {e}")
        form.amber_token.data = None

    form.tesla_site_id.data = current_user.tesla_energy_site_id
    logger.debug(f"Tesla Site ID: {form.tesla_site_id.data}")

    try:
        form.teslemetry_api_key.data = decrypt_token(current_user.teslemetry_api_key_encrypted)
        logger.debug(f"Teslemetry API key decrypted: {'Yes' if form.teslemetry_api_key.data else 'No'}")
    except Exception as e:
        logger.error(f"Error decrypting teslemetry api key: {e}")
        form.teslemetry_api_key.data = None

    logger.info(f"Rendering settings page - Has Amber token: {bool(current_user.amber_api_token_encrypted)}, Has Teslemetry key: {bool(current_user.teslemetry_api_key_encrypted)}, Tesla Site ID: {current_user.tesla_energy_site_id}")
    return render_template('settings.html', title='Settings', form=form)


@bp.route('/demand-charges', methods=['GET', 'POST'])
@login_required
def demand_charges():
    """Configure demand charge periods and rates"""
    logger.info(f"Demand charges page accessed by user: {current_user.email} - Method: {request.method}")
    form = DemandChargeForm()

    if form.validate_on_submit():
        logger.info(f"Demand charge form submitted by user: {current_user.email}")

        # Update user's demand charge configuration
        current_user.enable_demand_charges = form.enable_demand_charges.data
        current_user.peak_demand_rate = form.peak_rate.data if form.peak_rate.data else 0.0
        current_user.peak_start_hour = form.peak_start_hour.data if form.peak_start_hour.data is not None else 14
        current_user.peak_start_minute = form.peak_start_minute.data if form.peak_start_minute.data is not None else 0
        current_user.peak_end_hour = form.peak_end_hour.data if form.peak_end_hour.data is not None else 20
        current_user.peak_end_minute = form.peak_end_minute.data if form.peak_end_minute.data is not None else 0
        current_user.peak_days = form.peak_days.data
        current_user.offpeak_demand_rate = form.offpeak_rate.data if form.offpeak_rate.data else 0.0
        current_user.shoulder_demand_rate = form.shoulder_rate.data if form.shoulder_rate.data else 0.0
        current_user.shoulder_start_hour = form.shoulder_start_hour.data if form.shoulder_start_hour.data is not None else 7
        current_user.shoulder_start_minute = form.shoulder_start_minute.data if form.shoulder_start_minute.data is not None else 0
        current_user.shoulder_end_hour = form.shoulder_end_hour.data if form.shoulder_end_hour.data is not None else 14
        current_user.shoulder_end_minute = form.shoulder_end_minute.data if form.shoulder_end_minute.data is not None else 0

        try:
            db.session.commit()
            logger.info("Demand charge settings saved successfully to database")
            flash('Demand charge settings have been saved.')
        except Exception as e:
            logger.error(f"Error saving demand charge settings to database: {e}")
            flash('Error saving demand charge settings. Please try again.')
            db.session.rollback()

        return redirect(url_for('main.demand_charges'))

    # Pre-populate form with existing data
    logger.debug("Pre-populating demand charge form data")
    form.enable_demand_charges.data = current_user.enable_demand_charges
    form.peak_rate.data = current_user.peak_demand_rate
    form.peak_start_hour.data = current_user.peak_start_hour
    form.peak_start_minute.data = current_user.peak_start_minute
    form.peak_end_hour.data = current_user.peak_end_hour
    form.peak_end_minute.data = current_user.peak_end_minute
    form.peak_days.data = current_user.peak_days
    form.offpeak_rate.data = current_user.offpeak_demand_rate
    form.shoulder_rate.data = current_user.shoulder_demand_rate
    form.shoulder_start_hour.data = current_user.shoulder_start_hour
    form.shoulder_start_minute.data = current_user.shoulder_start_minute
    form.shoulder_end_hour.data = current_user.shoulder_end_hour
    form.shoulder_end_minute.data = current_user.shoulder_end_minute

    logger.info(f"Rendering demand charges page - Enabled: {current_user.enable_demand_charges}, Peak rate: {current_user.peak_demand_rate}")
    return render_template('demand_charges.html', title='Demand Charges', form=form)


# API Status and Data Routes
@bp.route('/api/status')
@login_required
def api_status():
    """Get connection status for both Amber and Tesla APIs"""
    logger.info(f"API status check requested by user: {current_user.email}")

    status = {
        'amber': {'connected': False, 'message': 'Not configured'},
        'tesla': {'connected': False, 'message': 'Not configured'}
    }

    # Check Amber connection
    amber_client = get_amber_client(current_user)
    if amber_client:
        connected, message = amber_client.test_connection()
        status['amber'] = {'connected': connected, 'message': message}
    else:
        status['amber']['message'] = 'No API token configured'

    # Check Tesla connection
    tesla_client = get_tesla_client(current_user)
    if tesla_client:
        connected, message = tesla_client.test_connection()
        status['tesla'] = {'connected': connected, 'message': message}
    else:
        status['tesla']['message'] = 'No access token configured'

    logger.info(f"API status: Amber={status['amber']['connected']}, Tesla={status['tesla']['connected']}")
    return jsonify(status)


@bp.route('/api/security-keys')
@login_required
def security_keys():
    """Get information about security keys for display in settings"""
    from app.utils import get_security_keys_info
    logger.info(f"Security keys info requested by user: {current_user.email}")
    keys_info = get_security_keys_info()
    return jsonify(keys_info)


@bp.route('/api/amber/current-price')
@login_required
def amber_current_price():
    """Get current Amber electricity price"""
    logger.info(f"Current price requested by user: {current_user.email}")

    amber_client = get_amber_client(current_user)
    if not amber_client:
        logger.warning("Amber client not available")
        return jsonify({'error': 'Amber API not configured'}), 400

    prices = amber_client.get_current_prices()
    if not prices:
        logger.error("Failed to fetch current prices")
        return jsonify({'error': 'Failed to fetch prices'}), 500

    # Store prices in database
    try:
        for price_data in prices:
            # Check if we already have this price record
            nem_time = datetime.fromisoformat(price_data['nemTime'].replace('Z', '+00:00'))

            record = PriceRecord(
                user_id=current_user.id,
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

        db.session.commit()
        logger.info(f"Saved {len(prices)} price records to database")
    except Exception as e:
        logger.error(f"Error saving price records: {e}")
        db.session.rollback()

    return jsonify(prices)


@bp.route('/api/amber/5min-forecast')
@login_required
def amber_5min_forecast():
    """Get 5-minute interval forecast for the next hour"""
    logger.info(f"5-minute forecast requested by user: {current_user.email}")

    amber_client = get_amber_client(current_user)
    if not amber_client:
        logger.warning("Amber client not available for 5-min forecast")
        return jsonify({'error': 'Amber API not configured'}), 400

    # Get 1 hour of forecast data at 5-minute resolution
    forecast = amber_client.get_price_forecast(next_hours=1, resolution=5)
    if not forecast:
        logger.error("Failed to fetch 5-minute forecast")
        return jsonify({'error': 'Failed to fetch 5-minute forecast'}), 500

    # Group by channel type and return
    general_intervals = [i for i in forecast if i.get('channelType') == 'general']
    feedin_intervals = [i for i in forecast if i.get('channelType') == 'feedIn']

    result = {
        'fetch_time': datetime.utcnow().isoformat(),
        'total_intervals': len(forecast),
        'general': general_intervals,
        'feedIn': feedin_intervals
    }

    logger.info(f"5-min forecast: {len(general_intervals)} general, {len(feedin_intervals)} feedIn intervals")
    return jsonify(result)


@bp.route('/api/amber/debug-forecast')
@login_required
def amber_debug_forecast():
    """
    Debug endpoint to fetch raw Amber forecast data for comparison with Netzero.
    Returns all available price fields from Amber API for the next 48 hours.
    """
    logger.info(f"Debug forecast requested by user: {current_user.email}")

    amber_client = get_amber_client(current_user)
    if not amber_client:
        logger.warning("Amber client not available")
        return jsonify({'error': 'Amber API not configured'}), 400

    # Get 48 hours of forecast data
    forecast = amber_client.get_price_forecast(next_hours=48)
    if not forecast:
        logger.error("Failed to fetch price forecast")
        return jsonify({'error': 'Failed to fetch price forecast'}), 500

    # Format the data for easy comparison
    debug_data = {
        'total_intervals': len(forecast),
        'fetch_time': datetime.utcnow().isoformat(),
        'intervals': []
    }

    for interval in forecast:
        # Extract all available fields
        interval_data = {
            'nemTime': interval.get('nemTime'),
            'startTime': interval.get('startTime'),
            'endTime': interval.get('endTime'),
            'duration': interval.get('duration'),
            'channelType': interval.get('channelType'),
            'descriptor': interval.get('descriptor'),

            # All price fields
            'perKwh': interval.get('perKwh'),
            'spotPerKwh': interval.get('spotPerKwh'),
            'wholesaleKWHPrice': interval.get('wholesaleKWHPrice'),
            'networkKWHPrice': interval.get('networkKWHPrice'),
            'marketKWHPrice': interval.get('marketKWHPrice'),
            'greenKWHPrice': interval.get('greenKWHPrice'),
            'lossFactor': interval.get('lossFactor'),

            # Metadata
            'spikeStatus': interval.get('spikeStatus'),
            'forecast': interval.get('forecast'),
            'renewables': interval.get('renewables'),
            'estimate': interval.get('estimate')
        }
        debug_data['intervals'].append(interval_data)

    # Group by channel type for easier analysis
    general_intervals = [i for i in debug_data['intervals'] if i['channelType'] == 'general']
    feedin_intervals = [i for i in debug_data['intervals'] if i['channelType'] == 'feedIn']

    summary = {
        'total_intervals': debug_data['total_intervals'],
        'fetch_time': debug_data['fetch_time'],
        'general_channel_count': len(general_intervals),
        'feedin_channel_count': len(feedin_intervals),
        'general_intervals': general_intervals,
        'feedin_intervals': feedin_intervals,
        'sample_fields': list(debug_data['intervals'][0].keys()) if debug_data['intervals'] else []
    }

    logger.info(f"Debug forecast: {len(general_intervals)} general, {len(feedin_intervals)} feedIn intervals")
    return jsonify(summary)


@bp.route('/api/tesla/status')
@login_required
def tesla_status():
    """Get Tesla Powerwall status"""
    logger.info(f"Tesla status requested by user: {current_user.email}")

    tesla_client = get_tesla_client(current_user)
    if not tesla_client:
        logger.warning("Tesla client not available")
        return jsonify({'error': 'Tesla API not configured'}), 400

    if not current_user.tesla_energy_site_id:
        logger.warning("No Tesla site ID configured")
        return jsonify({'error': 'No Tesla site ID configured'}), 400

    site_status = tesla_client.get_site_status(current_user.tesla_energy_site_id)
    if not site_status:
        logger.error("Failed to fetch Tesla site status")
        return jsonify({'error': 'Failed to fetch site status'}), 500

    return jsonify(site_status)


@bp.route('/api/price-history')
@login_required
def price_history():
    """Get historical price data"""
    logger.info(f"Price history requested by user: {current_user.email}")

    # Get last 24 hours of price data
    records = PriceRecord.query.filter_by(
        user_id=current_user.id,
        channel_type='general'
    ).order_by(
        PriceRecord.timestamp.desc()
    ).limit(48).all()

    data = [{
        'timestamp': record.timestamp.isoformat(),
        'per_kwh': record.per_kwh,
        'spike_status': record.spike_status,
        'forecast': record.forecast
    } for record in reversed(records)]

    logger.info(f"Returning {len(data)} price history records")
    return jsonify(data)


@bp.route('/api/tou-schedule')
@login_required
def tou_schedule():
    """Get the rolling 24-hour tariff schedule that will be sent to Tesla"""
    logger.info(f"TOU tariff schedule requested by user: {current_user.email}")

    amber_client = get_amber_client(current_user)
    if not amber_client:
        logger.warning("Amber client not available for tariff schedule")
        return jsonify({'error': 'Amber API not configured'}), 400

    # Get price forecast for next 48 hours (to build rolling 24h window)
    forecast = amber_client.get_price_forecast(next_hours=48)
    if not forecast:
        logger.error("Failed to fetch price forecast")
        return jsonify({'error': 'Failed to fetch price forecast'}), 500

    # Convert to Tesla tariff format
    from app.tariff_converter import AmberTariffConverter
    converter = AmberTariffConverter()
    tariff = converter.convert_amber_to_tesla_tariff(forecast, manual_override=None, user=current_user)

    if not tariff:
        logger.error("Failed to convert tariff")
        return jsonify({'error': 'Failed to convert tariff'}), 500

    # Extract tariff periods for display
    energy_rates = tariff.get('energy_charges', {}).get('Summer', {}).get('rates', {})
    feedin_rates = tariff.get('sell_tariff', {}).get('energy_charges', {}).get('Summer', {}).get('rates', {})

    # Build periods for display
    periods = []
    for hour in range(24):
        for minute in [0, 30]:
            period_key = f"PERIOD_{hour:02d}_{minute:02d}"
            if period_key in energy_rates:
                periods.append({
                    'time': f"{hour:02d}:{minute:02d}",
                    'hour': hour,
                    'minute': minute,
                    'buy_price': energy_rates[period_key] * 100,  # Convert back to cents
                    'sell_price': feedin_rates.get(period_key, 0) * 100
                })

    # Calculate stats
    buy_prices = [p['buy_price'] for p in periods if p['buy_price'] > 0]
    sell_prices = [p['sell_price'] for p in periods if p['sell_price'] > 0]

    stats = {
        'buy': {
            'min': min(buy_prices) if buy_prices else 0,
            'max': max(buy_prices) if buy_prices else 0,
            'avg': sum(buy_prices) / len(buy_prices) if buy_prices else 0
        },
        'sell': {
            'min': min(sell_prices) if sell_prices else 0,
            'max': max(sell_prices) if sell_prices else 0,
            'avg': sum(sell_prices) / len(sell_prices) if sell_prices else 0
        },
        'total_periods': len(periods)
    }

    logger.info(f"Generated tariff schedule with {len(periods)} periods")

    return jsonify({
        'periods': periods,
        'stats': stats,
        'tariff_name': tariff.get('name', 'Unknown')
    })


@bp.route('/api/sync-tesla-schedule', methods=['POST'])
@login_required
def sync_tesla_schedule():
    """Apply the TOU schedule to Tesla Powerwall"""
    logger.info(f"Tesla schedule sync requested by user: {current_user.email}")

    # Get both clients
    amber_client = get_amber_client(current_user)
    tesla_client = get_tesla_client(current_user)

    if not amber_client:
        logger.warning("Amber client not available for schedule sync")
        return jsonify({'error': 'Amber API not configured'}), 400

    if not tesla_client:
        logger.warning("Tesla client not available for schedule sync")
        return jsonify({'error': 'Tesla/Teslemetry API not configured'}), 400

    if not current_user.tesla_energy_site_id:
        logger.warning("No Tesla site ID configured")
        return jsonify({'error': 'Tesla Site ID not configured'}), 400

    site_id = current_user.tesla_energy_site_id

    try:
        # Get price forecast (48 hours for better coverage)
        forecast = amber_client.get_price_forecast(next_hours=48)
        if not forecast:
            logger.error("Failed to fetch price forecast for sync")
            return jsonify({'error': 'Failed to fetch price forecast'}), 500

        # Convert Amber prices to Tesla tariff format
        from app.tariff_converter import AmberTariffConverter
        converter = AmberTariffConverter()
        tariff = converter.convert_amber_to_tesla_tariff(forecast, manual_override=None, user=current_user)

        if not tariff:
            logger.error("Failed to convert tariff")
            return jsonify({'error': 'Failed to convert Amber prices to Tesla tariff format'}), 500

        num_periods = len(tariff.get('energy_charges', {}).get('Summer', {}).get('rates', {}))
        logger.info(f"Applying TESLA SYNC tariff with {num_periods} rate periods")

        # Apply tariff to Tesla
        result = tesla_client.set_tariff_rate(site_id, tariff)

        if not result:
            logger.error("Failed to apply tariff to Tesla")
            return jsonify({'error': 'Failed to apply tariff to Tesla Powerwall'}), 500

        logger.info("Successfully synced Amber tariff to Tesla Powerwall")

        return jsonify({
            'success': True,
            'message': 'TESLA SYNC tariff applied successfully',
            'rate_periods': num_periods,
            'tariff_name': tariff.get('name', 'Unknown')
        })

    except Exception as e:
        logger.error(f"Error syncing schedule to Tesla: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error syncing schedule: {str(e)}'}), 500


# Tesla Fleet API Routes (Virtual Keys Method)

@bp.route('/.well-known/appspecific/com.tesla.3p.public-key.pem')
def tesla_public_key():
    """
    Serve the Tesla Fleet API public key
    This endpoint is required by Tesla to validate domain ownership
    """
    logger.info("Public key requested")

    # Get the first user's public key (for single-user setups)
    # For multi-user, you'd need a different approach
    user = User.query.first()

    if not user or not user.tesla_fleet_public_key:
        logger.warning("No public key available")
        return "Public key not configured", 404

    logger.info("Serving Tesla Fleet API public key")
    return user.tesla_fleet_public_key, 200, {'Content-Type': 'application/x-pem-file'}


@bp.route('/tesla-fleet/setup', methods=['POST'])
@login_required
def tesla_fleet_setup():
    """Initialize Tesla Fleet API integration by generating keys"""
    try:
        logger.info(f"Tesla Fleet setup initiated by user: {current_user.email}")

        # Check if keys already exist
        if current_user.tesla_fleet_public_key:
            logger.info("Keys already exist for user")
            return jsonify({'error': 'Tesla Fleet keys already configured'}), 400

        # Generate EC key pair
        from app.utils import generate_tesla_key_pair
        private_pem, public_pem = generate_tesla_key_pair()

        # Store keys (encrypt private key, public key stays in plaintext)
        current_user.tesla_fleet_private_key_encrypted = encrypt_token(private_pem)
        current_user.tesla_fleet_public_key = public_pem

        db.session.commit()

        logger.info(f"Tesla Fleet keys generated and stored for user: {current_user.email}")

        return jsonify({
            'success': True,
            'public_key': public_pem,
            'message': 'Keys generated successfully'
        })

    except Exception as e:
        logger.error(f"Error during Tesla Fleet setup: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@bp.route('/tesla-fleet/connect')
@login_required
def tesla_fleet_connect():
    """Initiate Tesla Fleet OAuth flow"""
    try:
        logger.info(f"Tesla Fleet OAuth connect requested by user: {current_user.email}")

        # Ensure keys are generated
        if not current_user.tesla_fleet_public_key:
            flash('Please set up Tesla Fleet keys first')
            return redirect(url_for('main.dashboard'))

        # Tesla OAuth2 endpoints
        auth_base_url = "https://auth.tesla.com/oauth2/v3/authorize"

        # Get Tesla config from database or environment
        tesla_config = get_tesla_config(current_user)

        # Build authorization URL
        params = {
            'client_id': tesla_config['tesla_client_id'],
            'redirect_uri': tesla_config['tesla_redirect_uri'],
            'response_type': 'code',
            'scope': 'openid email offline_access vehicle_device_data vehicle_cmds vehicle_charging_cmds energy_device_data energy_cmds',
            'state': str(current_user.id)  # Pass user ID as state for verification
        }

        # Build query string
        from urllib.parse import urlencode
        query_string = urlencode(params)
        auth_url = f"{auth_base_url}?{query_string}"

        logger.info(f"Redirecting to Tesla OAuth: {auth_url}")
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error initiating Tesla Fleet OAuth: {e}")
        flash('Error connecting to Tesla. Please try again.')
        return redirect(url_for('main.dashboard'))


@bp.route('/tesla-fleet/callback')
@login_required
def tesla_fleet_callback():
    """Handle Tesla Fleet OAuth callback and register public key"""
    try:
        # Get authorization code from callback
        code = request.args.get('code')
        error = request.args.get('error')
        state = request.args.get('state')

        if error:
            logger.error(f"Tesla OAuth error: {error}")
            flash(f'Tesla authorization failed: {error}')
            return redirect(url_for('main.dashboard'))

        if not code:
            logger.error("No authorization code received from Tesla")
            flash('No authorization code received from Tesla')
            return redirect(url_for('main.dashboard'))

        # Verify state matches current user
        if state != str(current_user.id):
            logger.error(f"OAuth state mismatch: expected {current_user.id}, got {state}")
            flash('Invalid OAuth state. Please try again.')
            return redirect(url_for('main.dashboard'))

        logger.info(f"Tesla OAuth callback received for user: {current_user.email}")

        # Get Tesla config from database or environment
        tesla_config = get_tesla_config(current_user)

        # Exchange authorization code for tokens
        token_url = "https://auth.tesla.com/oauth2/v3/token"

        token_data = {
            'grant_type': 'authorization_code',
            'client_id': tesla_config['tesla_client_id'],
            'client_secret': tesla_config['tesla_client_secret'],
            'code': code,
            'redirect_uri': tesla_config['tesla_redirect_uri'],
            'audience': 'https://fleet-api.prd.na.vn.cloud.tesla.com'
        }

        logger.info("Exchanging authorization code for access token")
        response = requests.post(token_url, data=token_data, timeout=10)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            flash('Failed to obtain access token from Tesla')
            return redirect(url_for('main.dashboard'))

        tokens = response.json()

        # Encrypt and store tokens
        current_user.tesla_access_token_encrypted = encrypt_token(tokens['access_token'])
        current_user.tesla_refresh_token_encrypted = encrypt_token(tokens['refresh_token'])
        current_user.tesla_token_expiry = int(time.time() + tokens.get('expires_in', 3600))

        # Use manually configured region (default to 'na' if not set)
        region_to_use = current_user.tesla_region or 'na'
        logger.info(f"Using Tesla Fleet API region: {region_to_use}")
        logger.info("Domain registration should have been completed in Environment Settings")

        # Automatically retrieve energy site ID using the configured region
        try:
            from app.api_clients import TeslaFleetAPIClient
            region_to_use = current_user.tesla_region or 'na'
            fleet_client = TeslaFleetAPIClient(tokens['access_token'], tokens['refresh_token'], region_to_use)
            energy_sites = fleet_client.get_energy_sites()

            if energy_sites:
                # Get the first energy site ID
                site_id = energy_sites[0].get('energy_site_id')
                if site_id:
                    current_user.tesla_energy_site_id = str(site_id)
                    logger.info(f"Auto-detected Tesla Energy Site ID: {site_id}")
                    flash(f'Successfully connected to Tesla Fleet API ({region_to_use.upper()})! Energy Site ID {site_id} detected.')
                else:
                    logger.warning("No energy_site_id found in energy sites")
                    flash(f'Successfully connected to Tesla Fleet API ({region_to_use.upper()})! Please set your Energy Site ID in settings.')
            else:
                logger.warning("No energy sites found in Tesla account")
                flash(f'Successfully connected to Tesla Fleet API ({region_to_use.upper()})! No energy sites found - please check your Tesla account.')
        except Exception as e:
            logger.error(f"Error fetching energy sites during OAuth callback: {e}")
            flash('Successfully connected to Tesla Fleet API! Please set your Energy Site ID manually in settings.')

        db.session.commit()

        logger.info(f"Tesla Fleet OAuth tokens saved for user: {current_user.email}")
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        logger.error(f"Error during Tesla Fleet OAuth callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error completing Tesla authorization. Please try again.')
        return redirect(url_for('main.dashboard'))


@bp.route('/tesla-fleet/disconnect', methods=['POST'])
@login_required
def tesla_fleet_disconnect():
    """Disconnect Tesla Fleet API"""
    try:
        logger.info(f"Tesla Fleet disconnect requested by user: {current_user.email}")

        # Clear Tesla OAuth tokens but keep keys
        current_user.tesla_access_token_encrypted = None
        current_user.tesla_refresh_token_encrypted = None
        current_user.tesla_token_expiry = None

        db.session.commit()

        logger.info(f"Tesla Fleet OAuth tokens cleared for user: {current_user.email}")
        flash('Tesla Fleet API disconnected successfully')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        logger.error(f"Error disconnecting Tesla Fleet: {e}")
        flash('Error disconnecting Tesla. Please try again.')
        return redirect(url_for('main.dashboard'))


@bp.route('/tesla-fleet/reset-keys', methods=['POST'])
@login_required
def tesla_fleet_reset_keys():
    """Reset Tesla Fleet keys (regenerate)"""
    try:
        logger.info(f"Tesla Fleet key reset requested by user: {current_user.email}")

        # Clear all Tesla Fleet data
        current_user.tesla_fleet_private_key_encrypted = None
        current_user.tesla_fleet_public_key = None
        current_user.tesla_access_token_encrypted = None
        current_user.tesla_refresh_token_encrypted = None
        current_user.tesla_token_expiry = None

        db.session.commit()

        logger.info(f"Tesla Fleet keys and tokens cleared for user: {current_user.email}")
        flash('Tesla Fleet keys reset. You can now generate new keys.')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        logger.error(f"Error resetting Tesla Fleet keys: {e}")
        flash('Error resetting keys. Please try again.')
        return redirect(url_for('main.dashboard'))


# Teslemetry Routes
@bp.route('/teslemetry/disconnect', methods=['POST'])
@login_required
def teslemetry_disconnect():
    """Disconnect Teslemetry"""
    try:
        logger.info(f"Teslemetry disconnect requested by user: {current_user.email}")

        # Clear Teslemetry API key
        current_user.teslemetry_api_key_encrypted = None

        db.session.commit()

        logger.info(f"Teslemetry API key cleared for user: {current_user.email}")
        flash('Teslemetry disconnected successfully')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        logger.error(f"Error disconnecting Teslemetry: {e}")
        flash('Error disconnecting Teslemetry. Please try again.')
        return redirect(url_for('main.dashboard'))


@bp.route('/environment-settings', methods=['GET', 'POST'])
@login_required
def environment_settings():
    """Update Tesla OAuth credentials (saved to database, not environment variables)"""
    form = EnvironmentForm()

    if form.validate_on_submit():
        try:
            logger.info(f"Tesla OAuth settings update requested by user: {current_user.email}")

            # Encrypt and save Tesla Client ID
            if form.tesla_client_id.data:
                logger.info("Encrypting and saving Tesla Client ID")
                current_user.tesla_client_id_encrypted = encrypt_token(form.tesla_client_id.data)

            # Encrypt and save Tesla Client Secret
            if form.tesla_client_secret.data:
                logger.info("Encrypting and saving Tesla Client Secret")
                current_user.tesla_client_secret_encrypted = encrypt_token(form.tesla_client_secret.data)

            # Save redirect URI and app domain (not encrypted)
            if form.tesla_redirect_uri.data:
                logger.info("Saving Tesla Redirect URI")
                current_user.tesla_redirect_uri = form.tesla_redirect_uri.data

            if form.app_domain.data:
                logger.info("Saving App Domain")
                current_user.app_domain = form.app_domain.data

            # Save Tesla Fleet API region
            if form.tesla_region.data:
                logger.info(f"Saving Tesla region: {form.tesla_region.data}")
                current_user.tesla_region = form.tesla_region.data

            # Automatically register domain with Tesla Fleet API if all required fields are present
            if (form.tesla_client_id.data and form.tesla_client_secret.data and
                form.app_domain.data and form.tesla_region.data):

                try:
                    logger.info("Attempting automatic partner account registration")

                    # Region-specific endpoints
                    region = form.tesla_region.data
                    region_urls = {
                        'na': 'https://fleet-api.prd.na.vn.cloud.tesla.com',
                        'eu': 'https://fleet-api.prd.eu.vn.cloud.tesla.com',
                        'cn': 'https://fleet-api.prd.cn.vn.cloud.tesla.cn'
                    }
                    fleet_api_url = region_urls.get(region, region_urls['na'])

                    # Step 1: Generate partner authentication token using client_credentials
                    logger.info(f"Generating partner authentication token for region: {region}")
                    token_url = "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token"
                    token_data = {
                        'grant_type': 'client_credentials',
                        'client_id': form.tesla_client_id.data,
                        'client_secret': form.tesla_client_secret.data,
                        'audience': fleet_api_url
                    }

                    token_response = requests.post(token_url, data=token_data, timeout=10)

                    if token_response.status_code == 200:
                        partner_token = token_response.json()['access_token']
                        logger.info("Partner authentication token generated successfully")

                        # Step 2: Register domain with partner token
                        register_url = f"{fleet_api_url}/api/1/partner_accounts"
                        register_headers = {
                            "Authorization": f"Bearer {partner_token}",
                            "Content-Type": "application/json"
                        }
                        register_data = {"domain": form.app_domain.data}

                        logger.info(f"Registering domain with Tesla Fleet API ({region}): {register_url}")
                        register_response = requests.post(register_url, json=register_data, headers=register_headers, timeout=10)

                        if register_response.status_code in [200, 201]:
                            logger.info(f"Domain successfully registered with Tesla Fleet API ({region})")
                            flash(f'Tesla OAuth settings saved and domain registered with Fleet API ({region.upper()})!')
                        else:
                            logger.warning(f"Domain registration returned {register_response.status_code}: {register_response.text}")
                            flash(f'Settings saved, but domain registration returned status {register_response.status_code}. Check logs.')
                    else:
                        logger.error(f"Failed to generate partner token: {token_response.status_code} - {token_response.text}")
                        flash('Settings saved, but failed to generate partner authentication token. Check credentials.')

                except Exception as e:
                    logger.error(f"Error during automatic partner registration: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    flash('Settings saved, but automatic registration failed. You may need to register manually.')

            db.session.commit()
            logger.info("Tesla OAuth settings saved successfully")
            if not form.app_domain.data:
                flash('Tesla OAuth settings saved successfully. No restart required!')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            logger.error(f"Error saving Tesla OAuth settings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            flash(f'Error saving Tesla OAuth settings: {str(e)}')
            db.session.rollback()
            return redirect(url_for('main.dashboard'))

    # Pre-populate form with current database values (fallback to env vars for migration)
    try:
        if current_user.tesla_client_id_encrypted:
            form.tesla_client_id.data = decrypt_token(current_user.tesla_client_id_encrypted)
        elif os.environ.get('TESLA_CLIENT_ID'):
            form.tesla_client_id.data = os.environ.get('TESLA_CLIENT_ID')

        if current_user.tesla_client_secret_encrypted:
            form.tesla_client_secret.data = decrypt_token(current_user.tesla_client_secret_encrypted)
        elif os.environ.get('TESLA_CLIENT_SECRET'):
            form.tesla_client_secret.data = os.environ.get('TESLA_CLIENT_SECRET')

        form.tesla_redirect_uri.data = current_user.tesla_redirect_uri or os.environ.get('TESLA_REDIRECT_URI', '')
        form.app_domain.data = current_user.app_domain or os.environ.get('APP_DOMAIN', '')
        form.tesla_region.data = current_user.tesla_region or 'na'
    except Exception as e:
        logger.error(f"Error decrypting Tesla OAuth settings: {e}")

    return render_template('environment_settings.html', title='Tesla OAuth Settings', form=form)
