<div align="center">
  <img src="assets/images/logo.png" alt="Tesla Sync Logo" width="400"/>

  # Tesla Sync

  Intelligent Tesla Powerwall energy management for Australia. Automatically sync with Amber Electric dynamic pricing, create custom TOU schedules for any provider, and capitalize on AEMO wholesale price spikes to maximize your battery's earning potential.

  [![Docker Hub](https://img.shields.io/docker/v/bolagnaise/tesla-sync?label=docker%20hub&logo=docker)](https://hub.docker.com/r/bolagnaise/tesla-sync)
  [![Docker Pulls](https://img.shields.io/docker/pulls/bolagnaise/tesla-sync)](https://hub.docker.com/r/bolagnaise/tesla-sync)
  [![Build Status](https://github.com/bolagnaise/tesla-sync/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/bolagnaise/tesla-sync/actions)
</div>

## Screenshots

<div align="center">

### API Configuration
<img src="https://i.imgur.com/Lrk87Ti.png" alt="API Configuration - Amber and Teslemetry" width="80%"/>

*Configure Amber Electric and Teslemetry API credentials with secure encrypted storage*

### AEMO Wholesale Price Dashboard
<img src="https://i.imgur.com/dTksjzx.png" alt="AEMO Wholesale Price Dashboard" width="80%"/>

*Real-time AEMO wholesale electricity price monitoring with current price and threshold display*

### Amber Live 5 Min Price
<img src="https://i.imgur.com/TurU9f1.jpeg" alt="Amber Live 5 Min Price" width="80%"/>

*Live Amber Electric pricing with 5-minute rolling window showing current and upcoming rates*

### Tesla Powerwall Status Dashboard
<img src="https://i.imgur.com/ZxU4bgw.png" alt="Tesla Powerwall Status Dashboard" width="80%"/>

*Real-time Tesla Powerwall monitoring showing battery level, solar generation, battery power, grid power, and firmware version*

### Amber Electricity Tariff Schedule (24H)
<img src="https://i.imgur.com/PgkfMwH.png" alt="Amber Electricity Tariff Schedule" width="80%"/>

*Rolling 24-hour tariff schedule with hourly buy/sell rates and auto-sync to Tesla Powerwall*

### Price History (Last 24 Hours)
<img src="https://i.imgur.com/1fCrMsW.png" alt="Price History Chart" width="80%"/>

*Historical electricity price chart showing the last 24 hours of pricing data*

### Energy Usage History
<img src="https://i.imgur.com/1BEp6s7.png" alt="Energy Usage History Charts" width="80%"/>

*Comprehensive energy usage charts tracking solar generation, grid power, battery power, and home consumption*

### Energy Summaries
<img src="https://i.imgur.com/dskv5Os.png" alt="Energy Summaries" width="80%"/>

*Daily energy summaries showing total generation, consumption, grid import/export, and battery charge/discharge totals*

### AEMO Price Spike Settings
<img src="https://i.imgur.com/bpobhtd.png" alt="AEMO Price Spike Detection Settings" width="80%"/>

*Configure AEMO wholesale price monitoring with customizable thresholds and regional settings*

### AEMO Price Spike Detection Testing
<img src="https://i.imgur.com/MpLmELt.png" alt="AEMO Price Spike Detection Testing" width="80%"/>

*Test spike detection functionality with manual spike simulation*

---

**[View Full Screenshot Gallery →](https://imgur.com/a/TdzIgYT)**

</div>

## Features

### Core Functionality
- 🔋 **Automatic TOU Tariff Sync** - Updates Tesla Powerwall with Amber Electric pricing every 5 minutes
- 📊 **Real-time Pricing Dashboard** - Monitor current and historical electricity prices with live updates
- ⚡ **Near Real-Time Energy Monitoring** - Energy usage charts update every 30 seconds
- 🌏 **Timezone Support** - Configure your local timezone for accurate time display across all Australian states

### Advanced Features
- ⚡ **AEMO Spike Detection** - Automatically monitors Australian wholesale electricity prices and switches to spike tariff during extreme price events (configurable threshold)
- 🎯 **Custom TOU Schedules** - Create and manage custom time-of-use schedules for any electricity provider (not just Amber)
- 💾 **Saved TOU Profiles** - Backup, restore, and manage multiple tariff configurations
- 📈 **Demand Charge Tracking** - Monitor and track peak demand for electricity plans with capacity-based fees

### Technical Features
- 🔐 **Teslemetry Integration** - Secure Tesla API access via Teslemetry proxy service (no public domain required)
- 🔒 **Secure Credential Storage** - All API tokens encrypted at rest using Fernet encryption
- ⏱️ **Background Scheduler** - Automatic syncing every 5 minutes (aligned with Amber's forecast updates)
- 🐳 **Docker Ready** - Pre-built multi-architecture (amd64/arm64) images for easy deployment
- 🏠 **Home Assistant Integration** - Native HACS integration for seamless HA deployment

## Key Features Explained

### AEMO Spike Detection
Automatically monitors AEMO NEM wholesale electricity prices for your region (NSW1, QLD1, VIC1, SA1, TAS1). When prices exceed your configured threshold (e.g., $3000/MWh), the system:
- Saves your current tariff configuration
- Uploads a spike tariff with very high sell rates to encourage battery export
- Tesla Powerwall responds by exporting to grid during the spike
- Automatically restores your normal tariff when prices return to normal

Perfect for maximizing revenue during extreme price events!

### Custom TOU Schedules
Not using Amber Electric? No problem! Create custom time-of-use schedules for any Australian electricity provider:
- Define multiple seasonal periods (e.g., Summer, Winter)
- Set different rates for peak, shoulder, and off-peak periods
- Configure weekday/weekend variations
- Upload directly to Tesla Powerwall via Teslemetry

### Saved TOU Profiles
Backup and restore your tariff configurations:
- Save current Tesla tariff as named profile
- Restore previous configurations anytime
- Manage multiple tariff setups
- Pre-spike backup for AEMO spike detection

## Installation Options

Tesla Sync is available in two deployment options:

1. **[Home Assistant Integration](#home-assistant-integration)** - Native HA custom integration (Recommended for HA users)
2. **[Docker Application](#docker-deployment)** - Standalone web app with dashboard

---

## Home Assistant Integration

The easiest way to use Tesla Sync if you're already running Home Assistant.

### Features

- ✅ **Native HA Integration** - Seamless integration with your Home Assistant instance
- ✅ **HACS Installation** - Install and update via HACS (Home Assistant Community Store)
- ✅ **Automatic Discovery** - Auto-discovers Tesla energy sites from Teslemetry
- ✅ **Real-time Sensors** - Amber pricing and Tesla energy data as HA sensors
- ✅ **Automatic TOU Sync** - Background syncing every 5 minutes (just like Docker version)
- ✅ **Manual Services** - On-demand sync services for advanced automation
- ✅ **No External Services** - Runs entirely within Home Assistant

### Prerequisites

- Home Assistant installed and running
- HACS (Home Assistant Community Store) installed
- Teslemetry account with API token (https://teslemetry.com)
- Amber Electric account with API token (https://app.amber.com.au/developers)

### Installation Steps

1. **Install via HACS**
   - Open HACS in Home Assistant
   - Click the three dots in the top right
   - Select "Custom repositories"
   - Add repository URL: `https://github.com/bolagnaise/tesla-sync`
   - Category: `Integration`
   - Click "Add"
   - Click "Download" on the Tesla Sync integration
   - Restart Home Assistant

2. **Add Integration**
   - Go to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search for "Tesla Sync"
   - Click to add

3. **Configure**
   - **Step 1: Amber Electric**
     - Enter your Amber API token
     - Get token from: https://app.amber.com.au/developers

   - **Step 2: Teslemetry**
     - Enter your Teslemetry API token
     - Get token from: https://teslemetry.com

   - **Step 3: Site Selection**
     - Select your Tesla energy site from the dropdown
     - Select Amber site (if you have multiple)
     - Enable automatic TOU schedule syncing (recommended)

4. **Verify Setup**
   - Check that new sensors appear:
     - `sensor.current_electricity_price`
     - `sensor.solar_power`
     - `sensor.grid_power`
     - `sensor.battery_power`
     - `sensor.home_load`
     - `sensor.battery_level`
   - Check that the switch appears:
     - `switch.auto_sync_tou_schedule`

### Automatic TOU Syncing

**The integration automatically syncs your TOU schedule every 5 minutes** (aligned with Amber Electric's forecast updates) when the auto-sync switch is enabled.

**How it works:**
1. Enable the `switch.auto_sync_tou_schedule` switch (enabled by default during setup)
2. The integration runs a background timer that checks every 5 minutes
3. If auto-sync is enabled, it automatically:
   - Fetches the latest Amber pricing forecast
   - Converts it to Tesla TOU format
   - Sends it to your Powerwall via Teslemetry API
4. If auto-sync is disabled, the timer skips syncing

**No automation required!** Just leave the switch on and the integration handles everything automatically, just like the Docker version.

You can disable automatic syncing by turning off the switch, and re-enable it anytime.

### Available Services (Advanced)

```yaml
# Manually sync TOU schedule
service: tesla_amber_sync.sync_tou_schedule

# Refresh data from Amber and Teslemetry
service: tesla_amber_sync.sync_now
```

### Example Automations (Optional)

These are optional automations for advanced users. **Auto-sync is automatic and doesn't require any automations.**

**Force immediate sync on price spike:**
```yaml
automation:
  - alias: "Force TOU Sync on Price Spike"
    trigger:
      - platform: state
        entity_id: sensor.current_electricity_price
    condition:
      - condition: numeric_state
        entity_id: sensor.current_electricity_price
        above: 0.30
    action:
      - service: tesla_amber_sync.sync_tou_schedule
```

**Disable auto-sync during off-peak hours:**
```yaml
automation:
  - alias: "Disable Auto-Sync at Night"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.tesla_amber_sync_auto_sync

  - alias: "Enable Auto-Sync in Morning"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.tesla_amber_sync_auto_sync
```

### Troubleshooting

- **No sensors appearing**: Check that the integration is enabled in Settings → Devices & Services
- **Invalid API token**: Verify tokens at Amber and Teslemetry websites
- **No Tesla sites found**: Ensure your Tesla account is linked in Teslemetry
- **TOU sync failing**: Check Home Assistant logs for detailed error messages

---

## Docker Deployment

Standalone web application with dashboard for users who prefer Docker or don't use Home Assistant.

## Quick Start

### Method 1: Docker Hub (Recommended)

The easiest way to deploy is using the official pre-built image from Docker Hub.

**Option A: Using docker-compose (Recommended)**

```bash
# Download the docker-compose file
curl -O https://raw.githubusercontent.com/bolagnaise/tesla-sync/main/docker/docker-compose.hub.yml
curl -O https://raw.githubusercontent.com/bolagnaise/tesla-sync/main/.env.example
mv .env.example .env

# Edit .env with your Tesla credentials (encryption key auto-generated on first run)
nano .env

# Create data directory for persistence
mkdir -p ./data

# Start the container (note: file is in docker/ folder in repo, but we downloaded it to current dir)
docker-compose -f docker-compose.hub.yml up -d

# Access the app
open http://localhost:5001
```

**Option B: Using docker run**

```bash
# Create data directory first
mkdir -p $(pwd)/data

docker run -d \
  --name tesla-sync \
  -p 5001:5001 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  --restart unless-stopped \
  bolagnaise/tesla-sync:latest

# Note: Encryption key is auto-generated and saved to ./data/.fernet_key
# Tesla OAuth credentials can be configured via the Environment Settings page in the web UI
```

**Environment Variables:**

```bash
# Required
SECRET_KEY=your-random-secret-key-here

# Optional - Auto-generated if not provided
# FERNET_ENCRYPTION_KEY=your-custom-key-here
```

**Note on Configuration:**
- **Encryption Key:** Automatically generated and saved to `./data/.fernet_key` on first run. Only set `FERNET_ENCRYPTION_KEY` if you want to use a specific key (e.g., migrating from another instance).
- **Important:** Back up `./data/.fernet_key` - without it, you cannot decrypt stored credentials

**Docker Hub Image Details:**
- **Repository:** `bolagnaise/tesla-sync`
- **Multi-Architecture:** Supports `linux/amd64` and `linux/arm64`
- **Automated Builds:** Every push to main branch
- **Production Server:** Gunicorn with 4 workers

### Method 2: Build from Source

For development or customization:

1. **Clone the repository**
```bash
git clone https://github.com/bolagnaise/tesla-sync.git
cd tesla-sync
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
docker-compose -f docker/docker-compose.yml up -d
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
# Docker Compose (from source)
docker-compose -f docker/docker-compose.yml logs -f

# Docker Compose (pre-built, if using docker-compose.hub.yml)
docker-compose -f docker-compose.hub.yml logs -f

# Docker run
docker logs -f tesla-sync
```

### Update to Latest Version

**Pre-built Image:**
```bash
docker pull bolagnaise/tesla-sync:latest
docker restart tesla-sync

# Or with docker-compose
docker-compose -f docker-compose.hub.yml pull
docker-compose -f docker-compose.hub.yml up -d
```

**Built from Source:**
```bash
cd tesla-sync
git pull
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d --build
```

**Local Development (Python venv):**
```bash
cd tesla-sync
git pull
source venv/bin/activate
flask db upgrade  # Apply any database migrations
# Restart flask
```

> **Note:** Database migrations are automatically applied when using Docker. For local development, you must run `flask db upgrade` after pulling updates to ensure your database schema is current.

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
docker restart tesla-sync
```

📖 **See [DATABASE.md](DATABASE.md) for:**
- Detailed backup/restore instructions
- Automated backup scripts
- Troubleshooting database issues
- Unraid-specific setup

## Tesla API Authentication

This application uses **Teslemetry** for Tesla API access.

### Teslemetry Setup

Teslemetry is a third-party proxy service for Tesla API.

**Pros:**
- ✅ Simple setup
- ✅ Works with localhost
- ✅ Free for personal use
- ✅ Reliable and well-maintained

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

2. **Teslemetry API Key**
   - Get from: https://teslemetry.com
   - Used for: Tesla Powerwall communication

3. **Tesla Energy Site ID**
   - Your Powerwall/Solar site ID
   - Find in Teslemetry dashboard

### Dashboard Setup

After logging in:

1. **Configure Amber Electric**
   - Enter your Amber API token
   - Save settings

2. **Connect Teslemetry**
   - Enter your Teslemetry API key in settings form
   - Save settings

3. **Set Energy Site ID**
   - Enter your Tesla energy site ID from Teslemetry dashboard
   - Save settings

5. **Configure Timezone** (Optional)
   - Select your Australian timezone from the dropdown
   - All charts and timestamps will use your selected timezone
   - Defaults to Brisbane (AEST/AEDT)

6. **Verify Connection**
   - Check API status indicators turn green
   - View current prices and battery status

## Usage

### Automatic Sync

The app automatically:
- Syncs TOU tariff every 5 minutes (aligned with Amber Electric's forecast updates)
- Fetches latest pricing forecasts from Amber API
- Sends optimized rates to Tesla Powerwall

**Sync Timing:**
- **Frequency:** Every 5 minutes
- **Alignment:** Matches Amber Electric's pricing forecast update schedule (updated every 5 minutes)
- **Forecast Window:** 48 half-hour periods (24 hours ahead)
- **Tesla Format:** Tesla still receives 30-minute TOU schedules, but with the latest forecast data

### Monitoring

- **Current Prices**: Real-time Amber pricing with 5-minute interval updates
- **Battery Status**: Powerwall charge level, power flow
- **Energy Usage**: Near real-time charts (30-second updates) with enhanced hover tooltips
- **Price History**: 24-hour price chart with timezone-adjusted timestamps
- **TOU Schedule**: Upcoming 24-hour tariff plan (auto-refreshes every 30 minutes)
- **Timezone Configuration**: Set your local timezone for accurate time display across all charts

## Architecture

### Tech Stack

- **Backend**: Flask (Python)
- **Production Server**: Gunicorn (4 workers, 120s timeout)
- **Database**: SQLite (PostgreSQL supported)
- **Auth**: Flask-Login
- **Scheduler**: APScheduler (5-minute TOU sync, 5-minute data collection)
- **Encryption**: Fernet (cryptography)
- **Timezone Support**: Python zoneinfo (IANA timezones)
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
# Required
SECRET_KEY=strong-random-secret

# Optional
FERNET_ENCRYPTION_KEY=your-fernet-key
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Tesla OAuth Credentials (Optional - can be configured via web UI)
# TESLA_CLIENT_ID=your-client-id
# TESLA_CLIENT_SECRET=your-client-secret
# TESLA_REDIRECT_URI=https://yourdomain.com/tesla-fleet/callback
# APP_DOMAIN=https://yourdomain.com
```

**Note:** Tesla OAuth credentials can now be configured via the Environment Settings page in the web UI. This is recommended for easier management and eliminates the need to restart the container when updating credentials.

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

**"Teslemetry API connection failed"**
- Verify API key is correct
- Check that your Tesla account is connected to Teslemetry
- Ensure API key has proper permissions

**"No energy sites found"**
- Verify your Tesla Powerwall/Solar is connected to your Tesla account
- Check Teslemetry dashboard to confirm site is visible
- Ensure site is properly commissioned in Tesla app
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

- **[UNRAID_SETUP.md](docs/UNRAID_SETUP.md)** - Complete Unraid deployment guide
- **[TESLA_FLEET_SETUP.md](docs/TESLA_FLEET_SETUP.md)** - Complete Tesla Fleet API setup guide
- **[CLAUDE.md](docs/CLAUDE.md)** - Development guide for Claude Code
- **[Docker Hub](https://hub.docker.com/r/bolagnaise/tesla-sync)** - Pre-built container images
- **[GitHub Actions](https://github.com/bolagnaise/tesla-sync/actions)** - Automated build status
- **Tesla Developer Docs:** https://developer.tesla.com/docs/fleet-api
- **Amber API Docs:** https://api.amber.com.au/docs

## License

MIT

## Support

For issues or questions:
1. Review Flask logs for error details
2. Verify Teslemetry API key is correct
3. Check Teslemetry dashboard for connection status
4. Ensure Tesla Energy Site ID is correct

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Made with ⚡ by combining Tesla Powerwall optimization with Amber Electric dynamic pricing**
