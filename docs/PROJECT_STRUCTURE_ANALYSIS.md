# Tesla Sync Project Structure Analysis

## Executive Summary

**You're correct** - Flask and Home Assistant are **completely separate entities** that can operate independently. This project contains TWO distinct applications:

1. **Flask Web Application** - Standalone web interface with dashboard
2. **Home Assistant Custom Integration** - Native HA integration installable via HACS

They share similar functionality but are **architecturally independent**.

---

## 1. Flask Web Application

### Location
```
/app/                           # Flask application root
├── __init__.py                 # App factory pattern
├── routes.py                   # Main web routes
├── custom_tou_routes.py        # Custom TOU scheduler routes
├── models.py                   # SQLAlchemy models
├── forms.py                    # WTForms
├── api_clients.py              # Amber + Tesla API clients
├── tariff_converter.py         # Amber → Tesla format conversion
├── custom_tou_builder.py       # Custom TOU → Tesla format
├── scheduler.py                # APScheduler for 5-min sync
├── tasks.py                    # Background tasks
├── utils.py                    # Encryption/key utilities
└── templates/                  # Jinja2 HTML templates
```

### Purpose
- **Standalone web application** for users who want a dashboard
- Runs in Docker container (port 5001)
- Multi-user support with authentication (Flask-Login)
- Persistent SQLite database (`./data/app.db`)

### Key Features
- **Web UI Dashboard**: Real-time pricing charts, battery status, energy monitoring
- **User Management**: Login/registration system, encrypted credential storage
- **Custom TOU Scheduler**: Create/edit/sync custom fixed-rate schedules (what we just built!)
- **Automatic Sync**: Background scheduler runs every 5 minutes
- **Tesla Auth Options**: Supports both Fleet API (OAuth + Virtual Keys) and Teslemetry
- **API Status Monitoring**: Visual indicators for Amber/Tesla connectivity

### Deployment
```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data        # Persistent database
    environment:
      - SECRET_KEY=...
      - FERNET_ENCRYPTION_KEY=...
```

### Database Models
```python
# app/models.py
User:
  - email, password_hash
  - amber_api_token (encrypted)
  - teslemetry_api_token (encrypted)
  - tesla_site_id
  - tesla_oauth_access_token (encrypted)
  - timezone

CustomTOUSchedule:
  - name, utility, code
  - daily_charge, monthly_charge
  - seasons (one-to-many)

TOUSeason:
  - name, from_month, to_month
  - periods (one-to-many)

TOUPeriod:
  - name, time ranges
  - energy_rate, sell_rate, demand_rate
```

---

## 2. Home Assistant Custom Integration

### Location
```
/custom_components/tesla_amber_sync/   # HA integration root
├── __init__.py                         # Integration setup/teardown
├── manifest.json                       # Integration metadata
├── config_flow.py                      # Configuration UI flow
├── const.py                            # Constants
├── coordinator.py                      # Data coordinators
├── sensor.py                           # Sensor entities
├── switch.py                           # Switch entities (auto-sync)
├── tariff_converter.py                 # Amber → Tesla format
├── services.yaml                       # Service definitions
└── translations/                       # UI translations
```

### Purpose
- **Home Assistant native integration** for HA users
- Installed via HACS (Home Assistant Community Store)
- No separate database or web interface
- Uses HA's built-in entity registry and configuration

### Key Features
- **Sensor Entities**: Current price, battery level, solar power, grid power, home load
- **Switch Entity**: `switch.auto_sync_tou_schedule` (enable/disable 5-min sync)
- **Services**: `sync_tou_schedule`, `sync_now` for manual control
- **Automatic Sync**: Built-in 5-minute timer (same as Flask app)
- **Config Flow**: Multi-step configuration wizard in HA UI
- **No Multi-User Support**: Single HA instance configuration

### Integration Type
```json
// manifest.json
{
  "domain": "tesla_amber_sync",
  "integration_type": "hub",       // Hub integration with coordinators
  "iot_class": "cloud_polling",    // Polls cloud APIs
  "config_flow": true              // Configuration via UI
}
```

### Data Coordinators
```python
# coordinator.py
AmberPriceCoordinator:
  - Fetches Amber price forecasts
  - Updates every 5 minutes
  - Provides data to sensors

TeslaEnergyCoordinator:
  - Fetches Tesla Powerwall data
  - Updates every 30 seconds
  - Provides data to sensors
```

### Automatic Sync Implementation
```python
# __init__.py (lines 167-188)
async def auto_sync_tou(now):
    """Automatically sync TOU schedule if enabled."""
    switch_entity_id = f"switch.{DOMAIN}_auto_sync"
    switch_state = hass.states.get(switch_entity_id)

    if switch_state and switch_state.state == "on":
        await handle_sync_tou(None)

# Timer runs every 5 minutes
cancel_timer = async_track_time_interval(
    hass,
    auto_sync_tou,
    timedelta(minutes=5),
)
```

---

## 3. Shared Code vs. Separate Code

### Shared Functionality (Duplicated)
Both implementations include:
- **Tariff Conversion**: `tariff_converter.py` exists in both `/app/` and `/custom_components/`
- **API Communication**: Both talk to Amber API and Tesla/Teslemetry APIs
- **5-Minute Sync Logic**: Same sync interval and logic

### Flask-Only Features
- ✅ Multi-user support with authentication
- ✅ Web dashboard with charts
- ✅ **Custom TOU Scheduler** (create/edit fixed-rate schedules)
- ✅ Manual control modes
- ✅ Price/energy history tracking (PriceRecord, EnergyRecord models)
- ✅ Environment settings management
- ✅ Tesla Fleet API OAuth flow with virtual keys

### HA Integration-Only Features
- ✅ Native HA entities (sensors, switches)
- ✅ Integration with HA automations/scenes
- ✅ HA services for manual control
- ✅ HACS installation/updates
- ✅ HA device registry integration
- ✅ No separate database needed

---

## 4. How They Relate (or Don't)

### Independence
- **No shared runtime** - They never communicate with each other
- **Separate deployments** - Run in completely different environments
- **Different databases** - Flask uses SQLite, HA uses its own registry
- **Different architectures**:
  - Flask: Synchronous with APScheduler
  - HA: Async with coordinators and event loops

### User Choice
Users can run:
1. **Flask only** - Docker deployment, no Home Assistant required
2. **HA integration only** - HACS installation, no Docker required
3. **Both simultaneously** - They won't conflict (different APIs, different databases)

---

## 5. Demand Charge Feature Analysis

### Where to Add Demand Charge Tracking?

#### Option 1: Flask Web Application
**Pros:**
- Already has database models and UI framework
- Can create dedicated pages for configuration
- Easier to add custom forms and visualizations
- No HA dependency

**Cons:**
- Only available to Flask users
- Would need to build entire UI from scratch

**Implementation Path:**
```python
# app/models.py - Add new models
DemandChargeConfig:
  - user_id
  - start_time, end_time
  - rate_per_kw
  - billing_day
  - active_days

DemandChargePeak:
  - timestamp
  - peak_kw
  - cost

# app/routes.py - Add new routes
/demand-charges/configure
/demand-charges/dashboard
/demand-charges/history
```

#### Option 2: Home Assistant Integration
**Pros:**
- Already have the YAML configuration (`home_assistant_demand_charges.yaml`)
- Can leverage HA's built-in helpers and automations
- No custom UI needed (uses HA's entity cards)
- Better integration with existing HA users

**Cons:**
- Only available to HA users
- Limited to HA's UI capabilities

**Implementation Path:**
```python
# custom_components/tesla_amber_sync/sensor.py
# Add new sensors
- sensor.in_demand_charge_period
- sensor.peak_demand_this_cycle
- sensor.demand_charge_cost_this_month
- sensor.days_until_demand_reset

# custom_components/tesla_amber_sync/config_flow.py
# Add demand charge configuration step
- Demand charge rate input
- Start/end time inputs
- Billing day input
- Active days selection
```

#### Option 3: Standalone YAML Configuration (Current)
**Pros:**
- Already complete and ready to use
- Most flexible (users can customize)
- No code changes needed
- Works immediately for HA users

**Cons:**
- Manual setup required (copy/paste YAML)
- Not integrated into either application
- Flask users can't use it

---

## 6. Recommendation for Demand Charges

### Short-Term (Immediate)
**Use the standalone YAML configuration (`home_assistant_demand_charges.yaml`)**
- Already complete and functional
- Users can add to their HA configuration now
- No development work needed
- Provides full functionality:
  - Input helpers for configuration
  - Template sensors for tracking
  - Automations for peak detection
  - Monthly reset functionality

### Medium-Term (If Integration Needed)
**Add to Home Assistant Custom Integration**
- Most HA users already using the integration
- Can reuse existing configuration flow
- Add as optional feature during setup
- Store config in HA's config entry (not separate database)

**Implementation:**
```python
# config_flow.py - Add step 4
class ConfigFlow:
    async def async_step_demand_charges(self, user_input):
        # Optional demand charge configuration
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.config_data,
                    "demand_charge_enabled": True,
                    "demand_charge_rate": user_input["rate"],
                    "demand_charge_start": user_input["start_time"],
                    # ...
                }
            )
```

### Long-Term (If Flask Users Need It)
**Add to Flask Web Application**
- Build dedicated demand charge management pages
- Add database models for tracking
- Create charts for peak demand visualization
- Only if there's demand from Flask users

---

## 7. Project File Structure Summary

```
tesla-sync/
├── app/                                    # FLASK WEB APPLICATION
│   ├── __init__.py                         # App factory
│   ├── routes.py                           # Main routes
│   ├── custom_tou_routes.py                # Custom TOU routes ✨ (New feature)
│   ├── custom_tou_builder.py               # Custom TOU builder ✨ (New feature)
│   ├── models.py                           # SQLAlchemy models
│   ├── forms.py                            # WTForms
│   ├── api_clients.py                      # API clients
│   ├── tariff_converter.py                 # Tariff conversion
│   ├── scheduler.py                        # Background scheduler
│   ├── tasks.py                            # Background tasks
│   ├── utils.py                            # Utilities
│   └── templates/                          # Jinja2 templates
│       ├── base.html
│       ├── dashboard.html
│       └── custom_tou/                     # Custom TOU UI ✨ (New feature)
│           ├── index.html
│           ├── create_schedule_wizard.html
│           └── preview.html
│
├── custom_components/                      # HOME ASSISTANT INTEGRATION
│   └── tesla_amber_sync/
│       ├── __init__.py                     # HA integration entry
│       ├── manifest.json                   # HA metadata
│       ├── config_flow.py                  # Configuration UI
│       ├── coordinator.py                  # Data coordinators
│       ├── sensor.py                       # Sensor entities
│       ├── switch.py                       # Switch entities
│       ├── tariff_converter.py             # Tariff conversion (duplicate)
│       ├── const.py                        # Constants
│       └── services.yaml                   # Service definitions
│
├── migrations/                             # Flask database migrations
├── data/                                   # Flask persistent data
│   └── app.db                              # SQLite database
│
├── home_assistant_demand_charges.yaml      # Standalone HA config ✨ (New feature)
├── docker-compose.yml                      # Docker deployment (Flask)
├── Dockerfile                              # Flask container
├── requirements.txt                        # Python dependencies (Flask)
├── run.py                                  # Flask entry point
├── config.py                               # Flask configuration
│
├── README.md                               # Documentation
├── CLAUDE.md                               # Development guide
├── TESLA_FLEET_SETUP.md                    # Tesla API setup
└── UNRAID_SETUP.md                         # Unraid deployment

```

---

## 8. Key Takeaways

### They Are Separate
✅ Flask and HA integration are **completely independent**
✅ No shared runtime or dependencies
✅ Users choose one OR both (they don't conflict)

### Flask App Is For...
- Users who want a **standalone dashboard**
- Users who don't have Home Assistant
- Multi-user deployments
- Custom TOU scheduling (fixed-rate providers)

### HA Integration Is For...
- Users who **already have Home Assistant**
- Native HA entity integration
- HA automations and scenes
- HACS installation/updates

### Demand Charges Should Be...
- **Immediate**: Use standalone YAML (already complete)
- **Future**: Add to HA integration (better fit for HA users)
- **Optional**: Add to Flask if users request it

---

## 9. Development Context

### Recent Work Completed (This Session)
- ✅ Built complete Custom TOU Scheduler for Flask app
- ✅ Single-page wizard for creating/editing schedules
- ✅ Fixed time dropdown visibility issues
- ✅ Fixed Tesla tariff code to use utility name
- ✅ Created standalone HA demand charge configuration YAML

### What Was NOT Done
- ❌ Integrating demand charges into HA custom integration (user said "stop")
- ❌ Integrating demand charges into Flask app

### Why We Stopped
User asked: "flask and the HA are seperate entities arent they, analyse the prject"
- Confirmed separation
- Analyzed project structure
- This document is the result

---

## Conclusion

You were absolutely correct - **Flask and Home Assistant are separate entities**. This project cleverly provides TWO deployment options for different user needs:

1. **Docker/Flask** - Full-featured web application
2. **HACS/HA** - Native Home Assistant integration

Both do the same core job (sync Amber prices to Tesla), but serve different audiences. The demand charge tracking you wanted can be added to either (or both), but the standalone YAML configuration is ready to use right now.
