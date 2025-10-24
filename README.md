<div align="center">
  <img src="assets/images/logo.png" alt="Tesla-Amber-Sync Logo" width="400"/>

  # Tesla-Amber-Sync

  Synchronize Tesla Powerwall energy management with Amber Electric dynamic pricing to optimize battery charging and discharging based on real-time electricity prices.

  [![Docker Hub](https://img.shields.io/docker/v/bolagnaise/tesla-amber-sync?label=docker%20hub&logo=docker)](https://hub.docker.com/r/bolagnaise/tesla-amber-sync)
  [![Docker Pulls](https://img.shields.io/docker/pulls/bolagnaise/tesla-amber-sync)](https://hub.docker.com/r/bolagnaise/tesla-amber-sync)
  [![Build Status](https://github.com/bolagnaise/tesla-amber-sync/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/bolagnaise/tesla-amber-sync/actions)
</div>

## Features

- 🔋 **Automatic TOU Tariff Sync** - Updates Tesla Powerwall with Amber Electric pricing every 30 minutes
- 📊 **Real-time Pricing Dashboard** - Monitor current and historical electricity prices
- 🔐 **Dual Tesla Authentication** - Support for both Tesla Fleet API and Teslemetry (recommended)
- 🔒 **Secure Credential Storage** - All API tokens encrypted at rest
- ⏱️ **Background Scheduler** - Automatic syncing runs every 30 minutes (aligned with Amber's update cycle)
- 🐳 **Docker Ready** - Pre-built multi-architecture images for easy deployment

## Quick Start

### Method 1: Docker Hub (Recommended)

The easiest way to deploy is using the official pre-built image from Docker Hub.

**Option A: Using docker-compose (Recommended)**

```bash
# Download the docker-compose file
curl -O https://raw.githubusercontent.com/bolagnaise/tesla-amber-sync/main/docker-compose.hub.yml
curl -O https://raw.githubusercontent.com/bolagnaise/tesla-amber-sync/main/.env.example
mv .env.example .env

# Edit .env with your Tesla credentials (encryption key auto-generated on first run)
nano .env

# Create data directory for persistence
mkdir -p ./data

# Start the container
docker-compose -f docker-compose.hub.yml up -d

# Access the app
open http://localhost:5001
```

**Option B: Using docker run**

```bash
# Create data directory first
mkdir -p $(pwd)/data

docker run -d \
  --name tesla-amber-sync \
  -p 5001:5001 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  -e TESLA_CLIENT_ID=your-client-id \
  -e TESLA_CLIENT_SECRET=ta-secret.your-secret \
  -e TESLA_REDIRECT_URI=http://localhost:5001/tesla-fleet/callback \
  -e APP_DOMAIN=http://localhost:5001 \
  --restart unless-stopped \
  bolagnaise/tesla-amber-sync:latest

# Note: Encryption key is auto-generated and saved to ./data/.fernet_key
```

**Environment Variables:**

```bash
# Required
SECRET_KEY=your-random-secret-key-here

# Optional - Auto-generated if not provided
# FERNET_ENCRYPTION_KEY=your-custom-key-here

# Tesla Developer Credentials (optional - can use Teslemetry instead)
TESLA_CLIENT_ID=your-tesla-client-id
TESLA_CLIENT_SECRET=ta-secret.your-secret
TESLA_REDIRECT_URI=http://localhost:5001/tesla-fleet/callback
APP_DOMAIN=http://localhost:5001
```

**Note on Encryption Key:**
- The app automatically generates and saves an encryption key to `./data/.fernet_key` on first run
- Only set `FERNET_ENCRYPTION_KEY` if you want to use a specific key (e.g., migrating from another instance)
- **Important:** Back up `./data/.fernet_key` - without it, you cannot decrypt stored credentials

**Docker Hub Image Details:**
- **Repository:** `bolagnaise/tesla-amber-sync`
- **Multi-Architecture:** Supports `linux/amd64` and `linux/arm64`
- **Automated Builds:** Every push to main branch
- **Production Server:** Gunicorn with 4 workers

### Method 2: Build from Source

For development or customization:

1. **Clone the repository**
```bash
git clone https://github.com/bolagnaise/tesla-amber-sync.git
cd tesla-amber-sync
```

2. **Create `.env` file**
```bash
cp .env.example .env
```

3. **Edit `.env` with your credentials** (see environment variables above)
   - Encryption key will be auto-generated on first run

4. **Create data directory**
```bash
mkdir -p ./data
```

5. **Start with Docker Compose**
```bash
docker-compose up -d
```

6. **Access the dashboard**
```
http://localhost:5001
```

### Method 3: Python Virtual Environment (Advanced)

For local development without Docker:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database
flask db upgrade

# Run application
flask run
```

Navigate to http://localhost:5001

---

## Docker Management

### View Logs
```bash
# Docker Compose
docker-compose logs -f

# Docker run
docker logs -f tesla-amber-sync
```

### Update to Latest Version

**Pre-built Image:**
```bash
docker pull bolagnaise/tesla-amber-sync:latest
docker restart tesla-amber-sync

# Or with docker-compose
docker-compose -f docker-compose.hub.yml pull
docker-compose -f docker-compose.hub.yml up -d
```

**Built from Source:**
```bash
cd tesla-amber-sync
git pull
docker-compose down
docker-compose up -d --build
```

### Data Persistence

⚠️ **IMPORTANT**: Your database is stored in the `./data` directory. **Create this directory before first run** to prevent data loss during upgrades:

```bash
mkdir -p ./data
```

**Your data:**
- Database: `./data/app.db` (user accounts, API credentials, settings)
- This directory is mounted as a Docker volume for persistence
- **If `./data` doesn't exist, a fresh database is created on each restart**

**Quick backup:**
```bash
# Backup database
cp ./data/app.db ./data/app.db.backup-$(date +%Y%m%d)

# Restore database
cp ./data/app.db.backup-YYYYMMDD ./data/app.db
docker restart tesla-amber-sync
```

📖 **See [DATABASE.md](DATABASE.md) for:**
- Detailed backup/restore instructions
- Automated backup scripts
- Troubleshooting database issues
- Unraid-specific setup

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
- Syncs TOU tariff every 30 minutes (aligned with Amber Electric's update cycle)
- Fetches latest pricing forecasts from Amber API
- Sends optimized rates to Tesla Powerwall

**Sync Timing:**
- **Frequency:** Every 30 minutes
- **Alignment:** Matches Amber Electric's pricing update schedule
- **Forecast Window:** 48 half-hour periods (24 hours ahead)

### Monitoring

- **Current Prices**: Real-time Amber pricing
- **Battery Status**: Powerwall charge level, power flow
- **Price History**: 24-hour price chart
- **TOU Schedule**: Upcoming 24-hour tariff plan

## Architecture

### Tech Stack

- **Backend**: Flask (Python)
- **Production Server**: Gunicorn (4 workers, 120s timeout)
- **Database**: SQLite (PostgreSQL supported)
- **Auth**: Flask-Login
- **Scheduler**: APScheduler (30-minute intervals)
- **Encryption**: Fernet (cryptography)
- **Containerization**: Docker (multi-arch: amd64, arm64)
- **CI/CD**: GitHub Actions (automated builds)

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

- **[UNRAID_SETUP.md](UNRAID_SETUP.md)** - Complete Unraid deployment guide
- **[TESLA_FLEET_SETUP.md](TESLA_FLEET_SETUP.md)** - Complete Tesla Fleet API setup guide
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code
- **[Docker Hub](https://hub.docker.com/r/bolagnaise/tesla-amber-sync)** - Pre-built container images
- **[GitHub Actions](https://github.com/bolagnaise/tesla-amber-sync/actions)** - Automated build status
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
