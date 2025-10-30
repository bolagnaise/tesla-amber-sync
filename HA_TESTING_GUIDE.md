# Tesla Amber Sync - Home Assistant Integration Testing Guide

## Overview

The Home Assistant integration has been created in the `custom_components/tesla_amber_sync/` directory. This guide will help you test it locally before pushing to GitHub.

## File Structure

```
custom_components/tesla_amber_sync/
├── __init__.py              # Main integration setup
├── manifest.json            # Integration metadata
├── const.py                 # Constants and configuration keys
├── config_flow.py           # UI configuration flow
├── coordinator.py           # Data fetching coordinators
├── sensor.py                # Sensor entities (prices, energy)
├── switch.py                # Auto-sync switch entity
├── tariff_converter.py      # Amber to Tesla tariff conversion
├── services.yaml            # Service definitions
├── strings.json             # UI strings
└── translations/
    └── en.json              # English translations

Additional files:
├── hacs.json                # HACS configuration
└── HA_README.md             # User documentation
```

## Testing Steps

### 1. Copy to Home Assistant

Copy the integration to your Home Assistant instance:

```bash
# If running Home Assistant locally
cp -r custom_components/tesla_amber_sync /path/to/homeassistant/config/custom_components/

# If running Home Assistant in Docker/Unraid
# Copy to your Home Assistant config volume
```

### 2. Restart Home Assistant

After copying, restart Home Assistant to load the custom integration.

### 3. Check Logs

Monitor the Home Assistant logs for any errors during startup:

```bash
# In Home Assistant UI: Settings → System → Logs
# Or via command line:
tail -f /path/to/homeassistant/home-assistant.log
```

Look for log lines mentioning `tesla_amber_sync`.

### 4. Configure the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Tesla Amber Sync**
4. Follow the configuration wizard:
   - Verify Tesla Fleet is configured
   - Enter Amber API token
   - Select Tesla site
   - Enable/disable auto-sync

### 5. Verify Entities

After configuration, check that entities are created:

1. Go to **Settings** → **Devices & Services** → **Tesla Amber Sync**
2. You should see:
   - **Sensors**: Current Electricity Price, Solar Power, Grid Power, Battery Power, Home Load, Battery Level
   - **Switch**: Auto-Sync TOU Schedule

### 6. Test Services

Test the integration services:

```yaml
# In Developer Tools → Services

# Test sync TOU schedule
service: tesla_amber_sync.sync_tou_schedule

# Test sync now (refresh data)
service: tesla_amber_sync.sync_now
```

### 7. Monitor Data Updates

Watch the sensor entities to ensure data is being fetched:

- **Current Electricity Price** should update every 5 minutes
- **Energy sensors** (solar, grid, battery) should update every minute

## Known Issues & Notes

### 1. Tesla Fleet API Interaction

The current implementation attempts to call Tesla Fleet services for TOU sync. You may need to:

- Verify the Tesla Fleet integration provides the necessary services
- Consider using direct Tesla API calls if services aren't available
- Check `__init__.py` line 92-100 for the Tesla service call

**Potential Fix**: If `tesla_fleet.set_scheduled_charging` doesn't exist, you'll need to:

1. Use the Tesla Fleet API directly with HTTP requests
2. Access Tesla Fleet's internal methods (if exposed)
3. Or defer to the existing Flask app's Tesla client (`app/api_clients.py`)

### 2. Entity Discovery

The `TeslaEnergyCoordinator` attempts to discover Tesla Fleet entities by unique_id. If Tesla Fleet uses different naming:

- Check `coordinator.py` line 110-132
- Adjust entity matching logic based on actual Tesla Fleet entity names
- Use Developer Tools → States to see all available Tesla entities

### 3. Amber API Site ID

If you have multiple Amber sites, ensure the correct site ID is selected during configuration.

### 4. Data Availability

Initial data fetch might take a few minutes. Be patient and check logs for any API errors.

## Debug Logging

Enable detailed logging by adding to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tesla_amber_sync: debug
```

Then restart Home Assistant and check logs for detailed information.

## Comparison with Flask App

The Home Assistant integration provides:

**Same Functionality:**
- ✅ Amber price fetching and monitoring
- ✅ Tesla energy data monitoring
- ✅ TOU schedule synchronization
- ✅ Auto-sync toggle
- ✅ Tariff conversion with rolling 24h window

**Integration Benefits:**
- ✅ Native Home Assistant UI
- ✅ Leverages official Tesla Fleet integration
- ✅ No separate web server needed
- ✅ HACS installable
- ✅ Home Assistant automations support
- ✅ Energy Dashboard integration

**Current Limitations:**
- ⚠️ No energy history charts (would need custom Lovelace card)
- ⚠️ No demand charge configuration (simplified for HA)
- ⚠️ No manual charge/discharge modes (could be added as services)

## Testing Checklist

- [ ] Integration loads without errors
- [ ] Configuration flow completes successfully
- [ ] All sensor entities are created
- [ ] Auto-sync switch works
- [ ] Current price updates every 5 minutes
- [ ] Energy sensors update every minute
- [ ] Manual sync service works
- [ ] Sync now service works
- [ ] Auto-sync can be enabled/disabled
- [ ] Logs show successful API calls
- [ ] No error messages in logs
- [ ] Tesla TOU schedule is updated

## Next Steps After Testing

Once local testing is successful:

1. **Document any issues found** and fixes applied
2. **Create a GitHub branch** for the HA integration
3. **Push the changes** to the branch (NOT main)
4. **Update main README.md** to reference both Flask and HA versions
5. **Consider creating separate repositories**:
   - `tesla-amber-sync` (Flask web app)
   - `hacs-tesla-amber-sync` (HA integration)

## API Rate Limits

Remember the constraints:

- **Amber API**: Updates every 5 minutes
- **Tesla API**: ~$0.40/day if polling frequently
- **Teslemetry**: 1 site data update/minute, 1 history update/5 minutes

The integration is configured to stay within these limits:
- Amber: 5-minute polling
- Tesla: 1-minute polling (via Tesla Fleet entities, not direct API)

## Support

If you encounter issues:

1. Check Home Assistant logs
2. Enable debug logging
3. Verify Tesla Fleet integration is working independently
4. Verify Amber API token is valid
5. Check network connectivity

## Architecture Notes

The integration follows Home Assistant best practices:

- **Config Flow**: User-friendly setup via UI
- **Coordinators**: Efficient data polling with `DataUpdateCoordinator`
- **Entities**: Proper sensor and switch implementations
- **Services**: Custom services for manual operations
- **Dependencies**: Declares Tesla Fleet as a dependency
- **HACS**: Fully compatible with Home Assistant Community Store

This architecture ensures the integration is maintainable, efficient, and follows Home Assistant conventions.
