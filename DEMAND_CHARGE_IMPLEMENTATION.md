# Demand Charge Tracking - Home Assistant Integration

## Overview

Demand charge tracking has been successfully integrated into the Tesla Amber Sync Home Assistant custom integration. This feature allows users to track peak power demand during configurable time periods and calculate associated demand charges.

## Version

- **Integration Version**: 1.3.0 (updated from 1.2.1)
- **Date**: November 7, 2024

## What Was Implemented

### 1. Configuration Flow (Optional Step)

A new optional configuration step was added to the integration setup:

**Step 4: Demand Charge Configuration**
- Enable/disable demand charge tracking
- Configure demand charge rate ($/kW)
- Set demand period start and end times (HH:MM:SS format)
- Select active days (All Days, Weekdays Only, Weekends Only)
- Set billing cycle day (1-28)

**Default Values:**
- Rate: $0.2162/kW
- Start Time: 16:00:00 (4 PM)
- End Time: 23:00:00 (11 PM)
- Active Days: All Days
- Billing Day: 1st of month

### 2. New Sensors

When demand charge tracking is enabled, five new sensors are created:

#### `sensor.grid_import_power`
- **Unit**: kW
- **Purpose**: Tracks only positive grid power (import only, ignores export)
- **Update**: Real-time from Tesla coordinator

#### `sensor.in_demand_charge_period`
- **Type**: Boolean
- **Purpose**: Indicates if currently within configured demand charge period
- **Logic**: Considers both time range and day-of-week settings

#### `sensor.peak_demand_this_cycle`
- **Unit**: kW
- **Purpose**: Tracks the highest grid import power during demand periods
- **Behavior**:
  - Only updates during configured demand periods
  - Automatically resets on billing cycle day
  - Persists peak value throughout the month
- **Attributes**:
  - `timestamp`: When peak occurred
  - `peak_kw`: Peak value

#### `sensor.demand_charge_cost_this_month`
- **Unit**: $
- **Purpose**: Calculates estimated demand charge cost
- **Formula**: `peak_demand × demand_rate`
- **Attributes**:
  - `peak_kw`: Current peak demand
  - `rate`: Configured demand charge rate

#### `sensor.days_until_demand_reset`
- **Unit**: days
- **Purpose**: Countdown to next billing cycle reset
- **Logic**: Calculates days until configured billing day

## Technical Implementation

### Files Modified

1. **`const.py`**
   - Added 6 new configuration constants
   - Added 5 new sensor type constants

2. **`config_flow.py`**
   - Added `async_step_demand_charges()` method
   - Modified site selection flow to redirect to demand charges step
   - Added demand charge data to final config entry

3. **`sensor.py`**
   - Created `DEMAND_CHARGE_SENSORS` tuple with 5 sensor descriptions
   - Implemented `DemandChargeSensor` class with:
     - Peak tracking state management
     - Automatic monthly reset logic
     - Time period validation
     - Day-of-week filtering
     - Billing cycle calculations

4. **`strings.json` & `translations/en.json`**
   - Added demand_charges step translations
   - Added sensor entity name translations

5. **`manifest.json`**
   - Bumped version to 1.3.0

### Key Features

#### Automatic Peak Tracking
- Monitors grid import power every time the Tesla coordinator updates
- Only tracks peaks during configured demand periods
- Compares current import to stored peak and updates if higher
- Logs new peaks to Home Assistant logs

#### Smart Reset Logic
- Checks billing day on every sensor update
- Automatically resets peak to 0.0 kW on billing day
- Handles month changes (including year transitions)
- Preserves reset state to prevent multiple resets

#### Time Period Validation
- Supports periods within single day (e.g., 16:00-23:00)
- Supports periods crossing midnight (e.g., 22:00-06:00)
- Day-of-week filtering:
  - "All Days": Mon-Sun
  - "Weekdays Only": Mon-Fri
  - "Weekends Only": Sat-Sun

## Usage

### Installation

1. Install via HACS or manually copy files
2. Restart Home Assistant
3. Go to Settings → Devices & Services
4. Click "Add Integration"
5. Search for "Tesla Amber Sync"
6. Follow the setup wizard:
   - Step 1: Enter Amber API token
   - Step 2: Enter Teslemetry API token
   - Step 3: Select sites and enable auto-sync
   - **Step 4 (NEW): Configure demand charges** ⬅️ Optional step

### Configuration

If you want demand charge tracking:
1. Check "Enable Demand Charge Tracking"
2. Enter your electricity plan's demand charge rate
3. Configure the time period when demand charges apply
4. Select which days are active
5. Set your billing cycle day

If you don't want demand charge tracking:
1. Leave "Enable Demand Charge Tracking" unchecked
2. Click Submit (no demand charge sensors will be created)

### Monitoring

After setup, the demand charge sensors will appear under the integration's device:

```
Tesla Amber Sync
├── Current Electricity Price
├── Solar Power
├── Grid Power
├── Battery Power
├── Home Load
├── Battery Level
├── Grid Import Power                    ⬅️ NEW
├── In Demand Charge Period              ⬅️ NEW
├── Peak Demand This Cycle               ⬅️ NEW
├── Demand Charge Cost This Month        ⬅️ NEW
└── Days Until Demand Reset              ⬅️ NEW
```

### Dashboard Card Example

```yaml
type: entities
title: Demand Charge Tracking
show_header_toggle: false
entities:
  - entity: sensor.in_demand_charge_period
    name: Currently in Demand Period
  - entity: sensor.grid_import_power
    name: Current Grid Import
  - entity: sensor.peak_demand_this_cycle
    name: Peak This Cycle
  - entity: sensor.demand_charge_cost_this_month
    name: Estimated Cost
  - entity: sensor.days_until_demand_reset
    name: Days Until Reset
```

### Automation Examples

**Alert on New Peak:**
```yaml
automation:
  - alias: "Notify on New Demand Peak"
    trigger:
      - platform: state
        entity_id: sensor.peak_demand_this_cycle
    condition:
      - condition: numeric_state
        entity_id: sensor.peak_demand_this_cycle
        above: 5.0
    action:
      - service: notify.notify
        data:
          title: "New Demand Peak!"
          message: "Peak demand reached {{ states('sensor.peak_demand_this_cycle') }} kW"
```

**Daily Summary:**
```yaml
automation:
  - alias: "Daily Demand Charge Summary"
    trigger:
      - platform: time
        at: "23:30:00"
    action:
      - service: notify.notify
        data:
          title: "Demand Charge Summary"
          message: >
            Peak today: {{ states('sensor.peak_demand_this_cycle') }} kW
            Current cost: ${{ states('sensor.demand_charge_cost_this_month') }}
            Days until reset: {{ states('sensor.days_until_demand_reset') }}
```

## Comparison with Standalone YAML

### What's Different?

The standalone YAML configuration (`home_assistant_demand_charges.yaml`) provided:
- Input helpers for manual configuration
- Template sensors for calculations
- Automations for peak tracking and alerts
- Utility meter for monthly tracking

The integrated version provides:
- **Config flow UI** instead of manual YAML editing
- **Built-in sensors** instead of template sensors
- **Automatic state management** (no input_number needed)
- **Native entity IDs** under the integration device
- **Professional sensor classes** with proper device class and state class

### What's the Same?

- Peak tracking logic
- Time period validation
- Billing cycle reset functionality
- Cost calculations
- Days until reset countdown

### Migration Path

Users who were using the standalone YAML can:
1. Remove the YAML configuration
2. Re-add the integration (or configure options if already installed)
3. Enable demand charge tracking in the config flow
4. Update any automations to use new entity IDs

## Testing Checklist

- [ ] Integration installs successfully
- [ ] Config flow displays demand charges step
- [ ] Can skip demand charges (leave unchecked)
- [ ] Can enable demand charges with custom values
- [ ] Sensors appear when enabled
- [ ] Sensors don't appear when disabled
- [ ] Grid import power tracks correctly
- [ ] In demand period sensor matches configured times
- [ ] Peak updates during demand periods
- [ ] Peak doesn't update outside demand periods
- [ ] Cost calculation is accurate
- [ ] Days until reset countdown works
- [ ] Peak resets on billing day
- [ ] Handles month boundaries correctly
- [ ] Handles weekday/weekend filtering
- [ ] Handles midnight-crossing periods

## Future Enhancements

Possible additions for future versions:

1. **History Charts**: Built-in cards showing peak history over time
2. **Peak Shaving Alerts**: Proactive notifications when approaching current peak
3. **Battery Optimization**: Integration with auto-sync to prioritize peak shaving
4. **Multiple Demand Periods**: Support for plans with different rates at different times
5. **Peak Demand Forecast**: Predict likely peak based on historical patterns
6. **Export to CSV**: Download monthly demand charge history

## Troubleshooting

### Sensors Not Appearing
- Check that "Enable Demand Charge Tracking" was checked during setup
- Verify Home Assistant logs for any errors
- Try reloading the integration

### Peak Not Updating
- Verify "In Demand Charge Period" is True during expected times
- Check that grid import power is positive (importing from grid)
- Ensure Tesla coordinator is receiving data

### Peak Not Resetting
- Check configured billing day matches your electricity bill
- Verify Home Assistant system time is correct
- Check logs for reset messages

### Cost Calculation Wrong
- Verify demand charge rate is correct ($/kW, not $/MWh)
- Check peak demand value is in kW
- Confirm rate matches your electricity plan

## Support

For issues or questions:
1. Check Home Assistant logs for detailed errors
2. Verify configuration values match your electricity plan
3. Ensure Tesla Powerwall data is flowing correctly
4. Open an issue on GitHub with logs and configuration details

## License

MIT - Same as Tesla Amber Sync project

---

**Implementation completed by Claude Code on November 7, 2024**
