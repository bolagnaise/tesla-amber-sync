# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tesla-Amber-Sync is a Flask web application that synchronizes Tesla Powerwall energy data with Amber Electric pricing. Users authenticate via a web interface, securely store their Tesla and Amber Electric credentials, and enable automated integration between the two services.

## Architecture

### Application Factory Pattern
The app uses Flask's application factory pattern in `app/__init__.py`:
- `create_app()` initializes Flask extensions (SQLAlchemy, Flask-Migrate, Flask-Login)
- Database, migrations, and login manager are initialized separately and bound to the app instance
- The main blueprint is registered from `app/routes.py`

### Database & Models
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Database**: SQLite (`app.db` in project root)
- **Migrations**: Flask-Migrate (Alembic) in `migrations/` directory
- **User Model** (`app/models.py`):
  - Stores user email and password hash
  - Stores encrypted API tokens (Amber and Tesla) using Fernet encryption
  - Stores Tesla energy site ID and token expiry
  - Tracks last update status and time

### Authentication & Security
- Flask-Login handles user sessions
- Passwords are hashed using Werkzeug's `generate_password_hash` and `check_password_hash`
- API tokens are encrypted at rest using Fernet symmetric encryption
- Encryption key is stored in `.env` file as `FERNET_ENCRYPTION_KEY`
- Encryption/decryption utilities are in `app/utils.py`

### Routes & Views
All routes are in `app/routes.py` as a Blueprint named 'main':
- Public: `/`, `/login`, `/register`
- Protected: `/dashboard` (requires authentication)
- Tesla OAuth: `/tesla/connect`, `/tesla/callback`

**Note**: `app/routes.py` contains duplicate code sections (the same routes are repeated multiple times). This should be cleaned up by removing duplicates.

### Forms
WTForms with Flask-WTF (`app/forms.py`):
- `LoginForm`: Email/password with remember me
- `RegistrationForm`: Email/password with confirmation, validates unique email
- `SettingsForm`: Amber token and Tesla site ID input

### Templates
Jinja2 templates in `app/templates/`:
- `base.html`: Base template with common layout
- `index.html`, `login.html`, `register.html`, `dashboard.html`

## Development Commands

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Edit .env with your SECRET_KEY, FERNET_ENCRYPTION_KEY, Tesla credentials
```

### Database
```bash
# Initialize migrations (if starting fresh)
flask db init

# Create a migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

### Running the Application
```bash
# Development server
flask run
# Or
python run.py

# With specific host/port
flask run --host=0.0.0.0 --port=5000

# Production (using gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

### Flask Shell
```bash
flask shell
# Shell context includes: db, User
```

## Environment Variables

Required in `.env`:
- `SECRET_KEY`: Flask session secret
- `FERNET_ENCRYPTION_KEY`: Fernet key for token encryption (generate with `Fernet.generate_key().decode()`)
- `TESLA_CLIENT_ID`: Tesla OAuth client ID
- `TESLA_CLIENT_SECRET`: Tesla OAuth client secret
- `TESLA_REDIRECT_URI`: Tesla OAuth callback URL (e.g., `http://localhost:5000/tesla/callback`)

## Key Implementation Details

### Token Encryption Flow
1. User enters API tokens via `SettingsForm` in dashboard
2. `encrypt_token()` in `app/utils.py` encrypts plaintext tokens using Fernet
3. Encrypted bytes are stored in database (`LargeBinary` columns)
4. `decrypt_token()` retrieves plaintext when needed for API calls

### Tesla Authentication Methods

The app supports **two authentication methods** for Tesla API access:

#### 1. Tesla Fleet API (Direct OAuth with Virtual Keys)
**Setup Flow:**
1. User clicks "Generate Keys" → creates EC key pair (prime256v1)
2. Private key encrypted and stored, public key stored in plaintext
3. Public key served at `/.well-known/appspecific/com.tesla.3p.public-key.pem`
4. User clicks "Connect to Tesla" → redirected to `/tesla-fleet/connect`
5. OAuth flow with scopes: `vehicle_device_data`, `vehicle_cmds`, `energy_device_data`, `energy_cmds`
6. Tesla redirects to `/tesla-fleet/callback` with authorization code
7. App exchanges code for tokens and registers public key with Tesla Partner Account API
8. User pairs vehicle via Tesla mobile app using deep link: `https://tesla.com/_ak/{domain}`

**Routes:**
- `POST /tesla-fleet/setup` - Generate EC key pair
- `GET /tesla-fleet/connect` - Initiate OAuth
- `GET /tesla-fleet/callback` - Handle OAuth callback
- `POST /tesla-fleet/disconnect` - Clear tokens (keep keys)
- `POST /tesla-fleet/reset-keys` - Remove all Fleet API data
- `GET /.well-known/appspecific/com.tesla.3p.public-key.pem` - Serve public key

**Requirements:**
- Tesla Developer account with registered application
- HTTPS domain (for production/vehicle pairing)
- See `TESLA_FLEET_SETUP.md` for detailed setup instructions

#### 2. Teslemetry (Third-Party Proxy)
**Setup Flow:**
1. User signs up at teslemetry.com
2. User enters Teslemetry API key via settings form
3. API key encrypted and stored in database

**Routes:**
- `POST /teslemetry/disconnect` - Clear Teslemetry API key

**Client Priority:**
The `get_tesla_client()` function tries Fleet API first, then falls back to Teslemetry:
```python
# 1. Try Tesla Fleet API (if OAuth tokens exist)
# 2. Fallback to Teslemetry (if API key exists)
# 3. Return None if neither configured
```

### Virtual Keys (Tesla Fleet API)
- Uses elliptic curve cryptography (prime256v1/secp256r1)
- `generate_tesla_key_pair()` in `app/utils.py` creates key pair
- Public key must be publicly accessible for Tesla to validate
- Private key used to sign vehicle commands (future feature)
- Keys can be reset/regenerated via `/tesla-fleet/reset-keys`

### Login Flow
- `login.login_view` is set to `'main.login'` in `app/__init__.py`
- `@login_required` decorator redirects unauthenticated users
- User loader function in `app/models.py` retrieves user by ID for Flask-Login

## Important Notes

- The `app/routes.py` file has significant code duplication - the same routes and Tesla integration code are repeated multiple times. Clean this up before adding new features.
- API tokens are encrypted using Fernet symmetric encryption. Keep `FERNET_ENCRYPTION_KEY` secure and never commit it to version control.
- Database uses SQLite for simplicity. For production, consider PostgreSQL (DATABASE_URL is referenced in `.env` but not currently used).
