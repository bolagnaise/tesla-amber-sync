# Tesla Amber Sync - Deployment Options

## Overview

Tesla Amber Sync is available in two deployment options:

1. **Flask Web App** (Docker/Unraid) - Standalone web application
2. **Home Assistant Integration** (HACS) - Native HA integration

You can use **either or both** depending on your needs.

---

## Option 1: Flask Web App (Docker)

### Architecture
- **Standalone Flask web server** with SQLite database
- **Background scheduler** for automatic TOU syncing
- **Energy charts** with Chart.js visualization
- **Web dashboard** accessible via browser

### Deployment Methods

#### Docker Compose
```yaml
services:
  tesla-amber-sync:
    image: benboller/tesla-amber-sync:latest
    container_name: tesla-amber-sync
    ports:
      - "5001:5000"
    volumes:
      - ./data:/app/instance
      - ./logs:/app/logs
    environment:
      - SECRET_KEY=your-secret-key
      - FERNET_ENCRYPTION_KEY=your-fernet-key
    restart: unless-stopped
```

#### Unraid Template
Available via Community Applications - search "Tesla Amber Sync"

### Features
- ✅ Web UI with login/authentication
- ✅ Real-time energy flow charts
- ✅ Historical price and energy tracking
- ✅ 24-hour energy usage graphs
- ✅ Daily energy summaries
- ✅ Auto-sync toggle
- ✅ Manual sync button
- ✅ Settings management

### When to Use
- You want detailed energy visualization
- You don't use Home Assistant
- You prefer a dedicated web interface
- You're comfortable with Docker/Unraid

### Access
- Web UI: `http://your-server:5001`
- Login with registered email/password
- Dashboard shows all data and charts

---

## Option 2: Home Assistant Integration

### Architecture
- **Custom integration** inside Home Assistant
- **Data coordinators** for Amber and Tesla data
- **Native HA entities** (sensors, switches)
- **No web server** - uses HA's UI

### Deployment Method

#### HACS Installation
1. Add custom repository to HACS
2. Install "Tesla Amber Sync"
3. Restart Home Assistant
4. Configure via UI

#### Manual Installation
1. Copy `custom_components/tesla_amber_sync/` to HA config
2. Restart Home Assistant
3. Add integration via Settings → Devices & Services

### Features
- ✅ Native HA sensor entities
- ✅ Auto-sync switch
- ✅ Current price monitoring
- ✅ Energy flow sensors
- ✅ HA automations support
- ✅ Energy Dashboard integration
- ✅ Manual sync services
- ⚠️ No built-in charts (use Lovelace cards)

### When to Use
- You use Home Assistant for automation
- You want native HA entities
- You want to trigger automations based on prices
- You want to avoid running a separate service

### Access
- Settings → Devices & Services → Tesla Amber Sync
- View entities in HA UI
- Use in Lovelace dashboards
- Trigger automations

---

## Comparison Table

| Feature | Flask Web App | HA Integration |
|---------|--------------|----------------|
| **Deployment** | Docker/Unraid | Inside Home Assistant |
| **Web Interface** | Dedicated web UI | Home Assistant UI |
| **Energy Charts** | Built-in Chart.js | Requires Lovelace card |
| **Authentication** | Separate login | Home Assistant login |
| **Database** | SQLite | Uses HA's storage |
| **Auto-Sync** | ✅ Yes | ✅ Yes |
| **Manual Sync** | ✅ Button | ✅ Service call |
| **Price Monitoring** | ✅ Dashboard | ✅ Sensor entities |
| **Energy Tracking** | ✅ Charts | ✅ Sensor entities |
| **Automations** | ❌ No | ✅ Native HA automations |
| **Dependencies** | None | Requires HA + Tesla Fleet |
| **Maintenance** | Docker updates | HACS updates |

---

## Running Both (Hybrid Setup)

You can run both deployments simultaneously for maximum flexibility.

### Architecture
```
┌─────────────────┐         ┌──────────────────┐
│  Flask App      │         │  Home Assistant  │
│  (Docker)       │         │  (Docker/VM)     │
│                 │         │                  │
│  - Web UI       │         │  - HA Integration│
│  - Charts       │         │  - Entities      │
│  - TOU Sync     │         │  - TOU Sync      │
└────────┬────────┘         └────────┬─────────┘
         │                           │
         └───────────┬───────────────┘
                     │
         ┌───────────▼────────────┐
         │  Amber API             │
         │  Tesla API             │
         └────────────────────────┘
```

### Important Configuration
**To avoid conflicts, you should:**

1. **Disable auto-sync on one deployment**
   - Either Flask app OR HA integration should have auto-sync enabled
   - Not both simultaneously
   - This prevents duplicate TOU updates

2. **Use different update intervals** (if both have auto-sync)
   - Flask: Every 5 minutes
   - HA: Every 10 minutes (stagger them)

### Benefits of Hybrid Setup
- ✅ Use Flask for detailed charts and monitoring
- ✅ Use HA for automations and native integration
- ✅ Backup sync capability if one service is down
- ✅ Compare data between both systems

### Recommended Hybrid Configuration

**Flask App (Docker)**:
- Enable auto-sync: **YES**
- Update interval: 5 minutes
- Use for: Charts, monitoring, historical data

**HA Integration**:
- Enable auto-sync: **NO** (to avoid duplicates)
- Update interval: 5 minutes (data only)
- Use for: Automations, dashboards, real-time sensors

### Example HA Automation with Flask Sync
```yaml
automation:
  - alias: "Notify on High Electricity Price"
    trigger:
      - platform: numeric_state
        entity_id: sensor.current_electricity_price
        above: 0.30
    action:
      - service: notify.mobile_app
        data:
          message: "High electricity price: {{ states('sensor.current_electricity_price') }}/kWh"
          title: "Price Alert"
      # View details in Flask dashboard
      - service: notify.mobile_app
        data:
          message: "View charts at http://your-server:5001/dashboard"
```

---

## Migration Paths

### From Flask to HA Integration
1. **Export data** from Flask SQLite database (if needed)
2. **Install HA integration** via HACS
3. **Configure** with same Amber/Tesla credentials
4. **Stop Flask container** when ready
5. **Remove Docker deployment** (optional)

### From HA Integration to Flask
1. **Deploy Flask app** via Docker
2. **Register account** in web UI
3. **Configure** Amber/Tesla credentials
4. **Verify sync working**
5. **Disable HA integration** (optional)

### Staying with Current Flask Setup
- ✅ No action needed
- ✅ Continue using Docker as before
- ✅ HA integration is completely optional
- ✅ All features remain available

---

## Decision Guide

### Choose Flask Web App If:
- ❓ Do you use Home Assistant? **NO**
- ❓ Do you want detailed energy charts? **YES**
- ❓ Do you prefer a dedicated web interface? **YES**
- ❓ Are you comfortable with Docker? **YES**

### Choose HA Integration If:
- ❓ Do you use Home Assistant? **YES**
- ❓ Do you want native HA entities? **YES**
- ❓ Do you want HA automations? **YES**
- ❓ Do you want to avoid running separate services? **YES**

### Choose Both If:
- ❓ Do you use Home Assistant? **YES**
- ❓ Do you want detailed energy charts? **YES**
- ❓ Do you want HA automations? **YES**
- ❓ Can you manage two deployments? **YES**

---

## System Requirements

### Flask Web App
- **CPU**: 1 core
- **RAM**: 512 MB
- **Storage**: 1 GB
- **Network**: Internet access
- **Platform**: Docker, Unraid, any Linux

### HA Integration
- **Depends on**: Home Assistant installation
- **Additional RAM**: ~50 MB
- **Storage**: Minimal (uses HA's storage)
- **Network**: Internet access
- **Platform**: Wherever Home Assistant runs

---

## Support & Updates

### Flask Web App
- **Updates**: Docker Hub (`benboller/tesla-amber-sync`)
- **Docs**: README.md, UNRAID_SETUP.md
- **Issues**: GitHub Issues
- **Logs**: `/app/logs` directory

### HA Integration
- **Updates**: HACS (automatic notifications)
- **Docs**: HA_README.md, HA_TESTING_GUIDE.md
- **Issues**: GitHub Issues
- **Logs**: Home Assistant logs

---

## Summary

Both deployment options are **fully supported** and provide the same core functionality:
- ✅ Amber price fetching
- ✅ Tesla TOU synchronization
- ✅ Energy monitoring
- ✅ Auto-sync capability

Choose based on your infrastructure preferences and feature needs. The Docker deployment continues to work exactly as before, while the HA integration provides a native Home Assistant experience.
