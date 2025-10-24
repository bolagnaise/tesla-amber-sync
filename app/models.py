# app/models.py
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    # Encrypted Credentials
    amber_api_token_encrypted = db.Column(db.LargeBinary)
    tesla_energy_site_id = db.Column(db.String(50))
    tesla_access_token_encrypted = db.Column(db.LargeBinary)
    tesla_refresh_token_encrypted = db.Column(db.LargeBinary)
    tesla_token_expiry = db.Column(db.Integer)
    teslemetry_api_key_encrypted = db.Column(db.LargeBinary)

    # Tesla Fleet API Virtual Keys (for direct vehicle commands)
    tesla_fleet_private_key_encrypted = db.Column(db.LargeBinary)  # EC private key (encrypted)
    tesla_fleet_public_key = db.Column(db.Text)  # EC public key (PEM format, not encrypted - needs to be publicly accessible)

    # Tesla OAuth Configuration (stored in database instead of environment variables)
    tesla_client_id_encrypted = db.Column(db.LargeBinary)  # Tesla OAuth Client ID
    tesla_client_secret_encrypted = db.Column(db.LargeBinary)  # Tesla OAuth Client Secret
    tesla_redirect_uri = db.Column(db.String(255))  # OAuth redirect URI
    app_domain = db.Column(db.String(255))  # App domain for OAuth callbacks
    tesla_region = db.Column(db.String(10))  # Tesla Fleet API region ('na', 'eu', 'cn')

    # Status Tracking
    last_update_status = db.Column(db.String(255))
    last_update_time = db.Column(db.DateTime)

    # Manual Control Override
    manual_control_mode = db.Column(db.String(20))  # 'charge', 'discharge', or None
    manual_control_end_time = db.Column(db.DateTime)  # When manual control expires

    # Demand Charge Configuration
    enable_demand_charges = db.Column(db.Boolean, default=False)
    peak_demand_rate = db.Column(db.Float, default=0.0)
    peak_start_hour = db.Column(db.Integer, default=14)
    peak_start_minute = db.Column(db.Integer, default=0)
    peak_end_hour = db.Column(db.Integer, default=20)
    peak_end_minute = db.Column(db.Integer, default=0)
    peak_days = db.Column(db.String(20), default='weekdays')  # 'weekdays', 'all', 'weekends'
    offpeak_demand_rate = db.Column(db.Float, default=0.0)
    shoulder_demand_rate = db.Column(db.Float, default=0.0)
    shoulder_start_hour = db.Column(db.Integer, default=7)
    shoulder_start_minute = db.Column(db.Integer, default=0)
    shoulder_end_hour = db.Column(db.Integer, default=14)
    shoulder_end_minute = db.Column(db.Integer, default=0)

    # Relationships
    price_records = db.relationship('PriceRecord', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PriceRecord(db.Model):
    """Stores historical Amber electricity pricing data"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Timestamp
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    # Amber pricing data
    per_kwh = db.Column(db.Float)  # Price per kWh in cents
    spot_per_kwh = db.Column(db.Float)  # Spot price per kWh
    wholesale_kwh_price = db.Column(db.Float)  # Wholesale price
    network_kwh_price = db.Column(db.Float)  # Network price
    market_kwh_price = db.Column(db.Float)  # Market price
    green_kwh_price = db.Column(db.Float)  # Green/renewable price

    # Price type (general usage, controlled load, feed-in)
    channel_type = db.Column(db.String(50))

    # Forecast or actual
    forecast = db.Column(db.Boolean, default=False)

    # Period start/end
    nem_time = db.Column(db.DateTime)
    period_start = db.Column(db.DateTime)
    period_end = db.Column(db.DateTime)

    # Spike status
    spike_status = db.Column(db.String(20))

    def __repr__(self):
        return f'<PriceRecord {self.timestamp} - {self.per_kwh}c/kWh>'
