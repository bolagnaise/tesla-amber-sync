# Tesla Sync - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration that synchronizes Amber Electric pricing with Tesla Powerwall Time-of-Use (TOU) schedules, enabling cost-optimized battery management.

## Features

### Core Functionality
- **Automatic TOU Synchronization**: Continuously syncs Amber Electric's pricing to your Tesla Powerwall every 5 minutes
- **Real-time Price Monitoring**: Track current electricity prices including wholesale and network components
- **Energy Flow Monitoring**: Monitor solar generation, grid usage, battery power, and home consumption
- **Cost Optimization**: Tesla Powerwall automatically charges during low-price periods and discharges during high-price periods
- **Easy Configuration**: Simple setup through Home Assistant's UI
- **Leverages Official Integration**: Uses the official Home Assistant Tesla Fleet integration

### Technical Excellence
- 🌏 **Australia-Wide Compatibility**: Auto-detects timezone from Amber data, works in all Australian states (QLD, NSW, VIC, SA, TAS, WA, NT)
- 📊 **Intelligent Price Averaging**: Averages 5-minute Amber intervals into 30-minute Tesla periods for maximum accuracy
- 🎯 **Period Alignment**: Correctly aligns with Amber's forecast labels (e.g., "18:00 forecast" → Tesla PERIOD_17_30)
- 🔄 **Rolling 24-Hour Window**: Always provides Tesla with 9-24 hours lookahead for optimal battery management
- 🎚️ **Precision Matching**: 4 decimal place pricing with trailing zeros removed

## Prerequisites

Before installing this integration, you need:

1. **Home Assistant** (version 2024.8.0 or newer)
2. **Tesla Fleet Integration** configured in Home Assistant with:
   - Tesla account with Powerwall or Powerwall+
   - Tesla Developer account and application
   - Virtual keys configured
3. **Amber Electric Account** with:
   - Active electricity plan
   - API token from [Amber Developer Portal](https://app.amber.com.au/developers)

## Installation

### Method 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/bolagnaise/tesla-sync`
6. Select category: "Integration"
7. Click "Add"
8. Find "Tesla Sync" in HACS and click "Install"
9. Restart Home Assistant

### Method 2: Manual Installation

1. Download the `custom_components/tesla_amber_sync` folder from this repository
2. Copy the folder to your Home Assistant `custom_components` directory:
   ```
   <config_dir>/custom_components/tesla_amber_sync/
   ```
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Tesla Sync**
4. Follow the configuration steps:
   - **Step 1**: Confirmation that Tesla Fleet is configured
   - **Step 2**: Enter your Amber Electric API token
   - **Step 3**: Select your Tesla energy site and enable/disable auto-sync

## Entities

Once configured, the integration creates the following entities:

### Sensors

- **Current Electricity Price** ($/kWh)
  - Attributes: Price spike status, wholesale price, network price
- **Solar Power** (W)
- **Grid Power** (W)
- **Battery Power** (W)
- **Home Load** (W)
- **Battery Level** (%)

### Switches

- **Auto-Sync TOU Schedule**
  - Enable/disable automatic TOU schedule synchronization
  - Attributes: Last sync time, sync status

## Services

The integration provides the following services:

### `tesla_amber_sync.sync_tou_schedule`

Manually trigger a sync of the Time-of-Use schedule from Amber to Tesla.

```yaml
service: tesla_amber_sync.sync_tou_schedule
```

### `tesla_amber_sync.sync_now`

Immediately refresh data from Amber Electric and Tesla.

```yaml
service: tesla_amber_sync.sync_now
```

## Automations

You can create automations based on price data. For example, to notify when prices spike:

```yaml
automation:
  - alias: "Notify on Price Spike"
    trigger:
      - platform: state
        entity_id: sensor.current_electricity_price
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.current_electricity_price', 'price_spike') == 'spike' }}"
    action:
      - service: notify.mobile_app
        data:
          message: "Electricity price spike detected!"
```

## How It Works

### Intelligent Price Conversion

Tesla Sync uses sophisticated algorithms to convert Amber Electric's dynamic pricing into Tesla-compatible TOU (Time-of-Use) tariffs:

#### 1. **Smart Period Mapping**
Amber Electric labels their forecasts using **END time** convention (e.g., "18:00 forecast" = 17:30-18:00 period), while Tesla uses **START time** labels (e.g., PERIOD_17_30 = 17:30-18:00). Tesla Sync automatically aligns these conventions so prices match exactly what you see in the Amber app.

#### 2. **5-Minute Averaging**
- **Recent/Current Prices:** Amber provides 5-minute actual intervals with high precision
- **Conversion:** Tesla Sync averages six 5-minute intervals into each 30-minute Tesla period
- **Result:** More accurate pricing that captures real market volatility
- **Example:** Period 20:00-20:30 averages prices from 20:05, 20:10, 20:15, 20:20, 20:25, 20:30

#### 3. **Rolling 24-Hour Window**
Tesla requires a static 24-hour tariff structure, but Tesla Sync makes it "roll" forward:
- **Future periods** (not yet reached today): Use today's forecast prices
- **Past periods** (already passed today): Use tomorrow's forecast prices
- **Benefit:** Tesla always has 9-24 hours of lookahead for every period, enabling optimal battery decisions

**Example at 2:15 PM:**
```
PERIOD_00_00 → Tomorrow's 00:00 forecast (+9h 45m lookahead)
PERIOD_14_00 → Today's 14:30 forecast    (+15m lookahead - current)
PERIOD_23_30 → Tomorrow's 00:00 forecast (+9h 45m lookahead)
```

#### 4. **Timezone Auto-Detection**
Works anywhere in Australia without configuration:
- **Brisbane (AEST UTC+10:00):** No DST
- **Sydney/Melbourne (AEDT UTC+11:00):** DST in summer
- **Adelaide (ACDT UTC+10:30):** Unique 30-minute offset + DST
- **Perth (AWST UTC+8:00):** No DST
- **Darwin (ACST UTC+9:30):** No DST

The system automatically extracts timezone information from Amber's API data, ensuring correct "past vs future" period detection for all locations.

#### 5. **Precision Matching**
Prices are rounded to **4 decimal places** with trailing zeros automatically removed:
- `0.2014191` → `0.2014` (4 decimals)
- `0.1990000` → `0.199` (3 decimals, trailing zeros dropped)

### Sync Process

1. **Price Fetching**: Every 5 minutes, the integration fetches current and forecast prices from Amber Electric
2. **Tariff Conversion**: Prices are intelligently converted to Tesla's TOU tariff format using the algorithms above
3. **TOU Upload**: The tariff is uploaded to your Tesla Powerwall via the Tesla Fleet API
4. **Battery Optimization**: Tesla's onboard algorithms automatically optimize battery charge/discharge based on the TOU schedule

## Energy Flow Charts

The integration provides real-time power flow data that can be visualized using Home Assistant's Energy Dashboard or custom Lovelace cards.

Example Lovelace card configuration:

```yaml
type: entities
title: Energy Flow
entities:
  - entity: sensor.solar_power
  - entity: sensor.grid_power
  - entity: sensor.battery_power
  - entity: sensor.home_load
  - entity: sensor.battery_level
```

## Troubleshooting

### Integration Not Showing Up

- Ensure Tesla Fleet integration is configured first
- Check Home Assistant logs for errors
- Restart Home Assistant after installation

### No Price Data

- Verify your Amber API token is correct
- Check that your Amber account has an active electricity plan
- Ensure you have internet connectivity

### TOU Not Syncing to Tesla

- Verify Tesla Fleet integration is working (check Tesla entities)
- Enable debug logging to see detailed sync information
- Check Tesla Developer Dashboard for API usage limits

### Enable Debug Logging

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tesla_amber_sync: debug
```

## Cost Savings

By syncing Amber's real-time pricing to your Tesla Powerwall:

- **Charge during cheap periods**: Battery charges when grid prices are low
- **Discharge during expensive periods**: Battery powers your home when grid prices are high
- **Export optimization**: Sell excess solar at the best prices
- **Spike protection**: Automatically avoid high-price periods

Typical savings range from 20-40% on electricity bills compared to fixed-rate plans, depending on your usage patterns and solar generation.

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/bolagnaise/tesla-sync/issues
- Home Assistant Community: https://community.home-assistant.io/

## License

This project is licensed under the MIT License.

## Acknowledgments

- Built for the Home Assistant community
- Uses the official Home Assistant Tesla Fleet integration
- Integrates with Amber Electric's real-time pricing API

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Tesla, Inc. or Amber Electric. Use at your own risk.
