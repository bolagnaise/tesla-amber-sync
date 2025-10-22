# Tesla-Amber-Sync

Synchronize Tesla Powerwall energy management with Amber Electric dynamic pricing to optimize battery charging and discharging based on real-time electricity prices.

## Features

- 🔋 **Automatic TOU Tariff Sync** - Updates Tesla Powerwall with Amber Electric pricing every 30 minutes
- ⚡ **Manual Battery Control** - Force charge or discharge on demand - WIP - FLAKY
- 📊 **Real-time Pricing Dashboard** - Monitor current and historical electricity prices
- 🔐 **Dual Tesla Authentication** - Support for both Tesla Fleet API and Teslemetry (reccomended)
- 🔒 **Secure Credential Storage** - All API tokens encrypted at rest
- ⏱️ **Background Scheduler** - Automatic syncing runs hourly

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required
SECRET_KEY=your-random-secret-key
FERNET_ENCRYPTION_KEY=your-fernet-key

# Tesla Developer Credentials (for Fleet API)
TESLA_CLIENT_ID=your-client-id
TESLA_CLIENT_SECRET=your-client-secret
TESLA_REDIRECT_URI=http://localhost:5001/tesla-fleet/callback
APP_DOMAIN=http://localhost:5001
```

**Generate encryption key:**
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 3. Initialize Database

```bash
flask db upgrade
```

### 4. Run Application

```bash
flask run
```

Navigate to http://localhost:5001

## Docker Deployment (Recommended)

The easiest way to run Tesla-Amber-Sync is with Docker.

### Prerequisites

- Docker and Docker Compose installed
- Tesla Developer credentials (optional, can use Teslemetry instead)

### Quick Start with Docker

1. **Clone the repository**
```bash
git clone https://github.com/bolagnaise/tesla-amber-sync.git
cd tesla-amber-sync
```

2. **Create `.env` file**
```bash
cp .env.example .env
```

3. **Generate encryption key**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

4. **Edit `.env` with your credentials**
```bash
# Required
SECRET_KEY=your-random-secret-key-here
FERNET_ENCRYPTION_KEY=paste-generated-key-here

# Tesla Developer Credentials (optional - can use Teslemetry instead)
TESLA_CLIENT_ID=your-tesla-client-id
TESLA_CLIENT_SECRET=ta-secret.your-secret
TESLA_REDIRECT_URI=http://localhost:5001/tesla-fleet/callback
APP_DOMAIN=http://localhost:5001
```

5. **Start the application**
```bash
docker-compose up -d
```

6. **Access the dashboard**
```
http://localhost:5001
```

### Docker Commands

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View running containers
docker ps

# Access shell in container
docker-compose exec web sh
```

### Data Persistence

Your data is stored in the `./data` directory:
- Database: `./data/app.db`
- This directory is mounted as a Docker volume for persistence

**Backup your data:**
```bash
# Backup database
cp ./data/app.db ./data/app.db.backup

# Restore database
cp ./data/app.db.backup ./data/app.db
docker-compose restart
```

## Tesla API Authentication

You can choose **one or both** methods:

### Option 1: Tesla Fleet API (Recommended)

Direct connection to Tesla with OAuth2 and virtual keys.

**Pros:**
- ✅ Direct connection (no third-party)
- ✅ Enhanced security with cryptographic keys
- ✅ No additional service fees

**Cons:**
- ❌ Requires HTTPS domain for production
- ❌ More complex setup

**Setup:**
1. Create Tesla Developer account at https://developer.tesla.com/
2. Register your application
3. Get Client ID and Client Secret
4. See **[TESLA_FLEET_SETUP.md](TESLA_FLEET_SETUP.md)** for detailed instructions

### Option 2: Teslemetry (Easier)

Third-party proxy service for Tesla API.

**Pros:**
- ✅ Simple setup
- ✅ Works with localhost
- ✅ Free for personal use

**Cons:**
- ❌ Requires third-party service
- ❌ Less direct control

**Setup:**
1. Sign up at https://teslemetry.com
2. Connect your Tesla account
3. Copy your API key
4. Paste into dashboard settings

## Configuration

### Required Credentials

1. **Amber Electric API Token**
   - Get from: Amber developer settings
   - Used for: Fetching real-time electricity prices

2. **Tesla Authentication** (choose one or both)
   - Fleet API: OAuth credentials from Tesla Developer Portal
   - Teslemetry: API key from teslemetry.com

3. **Tesla Energy Site ID**
   - Your Powerwall/Solar site ID
   - Find in Teslemetry dashboard or Tesla Fleet API

### Dashboard Setup

After logging in:

1. **Configure Amber Electric**
   - Enter your Amber API token
   - Save settings

2. **Connect Tesla** (choose method)
   - **Fleet API**: Click "Generate Keys" → "Connect to Tesla"
   - **Teslemetry**: Enter API key in settings form

3. **Set Energy Site ID**
   - Enter your Tesla energy site ID
   - Save settings

4. **Verify Connection**
   - Check API status indicators turn green
   - View current prices and battery status

## Usage

### Automatic Sync

The app automatically:
- Syncs TOU tariff every hour
- Updates pricing every 30 minutes
- Sends optimized rates to Tesla Powerwall

### Manual Control

**Force Charge:**
- Artificially lowers buy prices
- Tesla sees cheap electricity
- Battery charges from grid

**Force Discharge:**
- Artificially raises sell prices
- Tesla sees high export value
- Battery discharges to grid

**Duration:** 30min - 4 hours

### Monitoring

- **Current Prices**: Real-time Amber pricing
- **Battery Status**: Powerwall charge level, power flow
- **Price History**: 24-hour price chart
- **TOU Schedule**: Upcoming 24-hour tariff plan

## Architecture

### Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (PostgreSQL supported)
- **Auth**: Flask-Login
- **Scheduler**: APScheduler
- **Encryption**: Fernet (cryptography)

### Key Components

```
app/
├── __init__.py          # App factory, extensions
├── models.py            # User, PriceRecord models
├── routes.py            # All endpoints
├── forms.py             # WTForms
├── api_clients.py       # Amber, Tesla, Teslemetry clients
├── utils.py             # Encryption, key generation
├── scheduler.py         # Background TOU sync
├── tariff_converter.py  # Amber → Tesla format
└── templates/           # Jinja2 templates
```

### Authentication Flow

**Tesla Fleet API:**
1. Generate EC key pair (prime256v1)
2. Host public key at `/.well-known/appspecific/com.tesla.3p.public-key.pem`
3. OAuth2 flow with Tesla
4. Register public key with Partner Account API
5. Pair vehicle via Tesla mobile app

**Teslemetry:**
1. User enters API key
2. Key encrypted and stored
3. Proxied API calls via Teslemetry

**Client Priority:**
- Tries Fleet API first (if configured)
- Falls back to Teslemetry (if configured)
- Returns None if neither available

## Development

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade

# Rollback
flask db downgrade
```

### Flask Shell

```bash
flask shell
# Available: db, User, PriceRecord
```

### Debug Mode

```bash
export FLASK_DEBUG=1
flask run
```

## Production Deployment

### Requirements

- HTTPS domain with valid SSL certificate
- PostgreSQL database (recommended)
- Reverse proxy (nginx/Apache)
- Process manager (systemd/supervisor)

### Example Nginx Config

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /.well-known/appspecific/com.tesla.3p.public-key.pem {
        proxy_pass http://localhost:5001/.well-known/appspecific/com.tesla.3p.public-key.pem;
        add_header Content-Type application/x-pem-file;
    }
}
```

### Environment Variables (Production)

```bash
SECRET_KEY=strong-random-secret
FERNET_ENCRYPTION_KEY=your-fernet-key
DATABASE_URL=postgresql://user:pass@localhost/dbname

TESLA_CLIENT_ID=your-client-id
TESLA_CLIENT_SECRET=your-client-secret
TESLA_REDIRECT_URI=https://yourdomain.com/tesla-fleet/callback
APP_DOMAIN=https://yourdomain.com
```

### Run with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5001 run:app
```

## Security

- ✅ All API tokens encrypted with Fernet
- ✅ Passwords hashed with Werkzeug
- ✅ CSRF protection via Flask-WTF
- ✅ Private keys never exposed publicly
- ✅ OAuth2 state parameter validation

**Best Practices:**
- Never commit `.env` file
- Rotate credentials periodically
- Use HTTPS in production
- Enable Tesla two-factor authentication
- Review active virtual keys regularly

## Troubleshooting

### Common Issues

**"Invalid Client ID"**
- Verify credentials in Tesla Developer Portal
- Check for extra spaces/quotes in `.env`

**"Redirect URI mismatch"**
- Must exactly match Tesla Developer Portal settings
- Check http vs https, port numbers, trailing slashes

**"Public key not found"**
- Click "Generate Keys" first
- Verify endpoint: `http://localhost:5001/.well-known/appspecific/com.tesla.3p.public-key.pem`

**Virtual key pairing fails:**
- Requires HTTPS and public domain
- Won't work with localhost
- Check public key is accessible externally

### Logs

Check Flask logs for detailed errors:
```bash
tail -f flask.log
```

Enable debug mode for more details:
```bash
export FLASK_DEBUG=1
flask run
```

## Documentation

- **[TESLA_FLEET_SETUP.md](TESLA_FLEET_SETUP.md)** - Complete Tesla Fleet API setup guide
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code
- **Tesla Developer Docs:** https://developer.tesla.com/docs/fleet-api
- **Amber API Docs:** https://api.amber.com.au/docs

## License

MIT

## Support

For issues or questions:
1. Check [TESLA_FLEET_SETUP.md](TESLA_FLEET_SETUP.md) for setup help
2. Review Flask logs for error details
3. Verify API credentials are correct
4. Test with both authentication methods

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Made with ⚡ by combining Tesla Powerwall optimization with Amber Electric dynamic pricing**
