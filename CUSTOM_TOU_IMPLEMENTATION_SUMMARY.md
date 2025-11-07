# Custom TOU Scheduler - Implementation Summary

## ✅ What Was Built

I've created a comprehensive custom TOU (Time-of-Use) scheduler for your Flask/Docker app that allows you to create fixed-rate electricity plans for Australian providers with complex pricing structures.

### Core Features

**✅ Unlimited Time Periods**
- Not limited to Tesla's 4-tier system (Super Off-Peak, Off-Peak, Mid-Peak, Peak)
- Support for complex plans with 5, 6, or more different rate periods
- Perfect for providers like Origin Energy, AGL, Energy Australia

**✅ 30-Minute Granularity**
- Aligned with Australian NEM (National Electricity Market) intervals
- Precise scheduling down to 30-minute blocks

**✅ Multiple Seasons**
- Summer/winter rate variations
- Supports any number of seasonal periods throughout the year

**✅ Demand Charges**
- Capacity-based fees ($/kW) for plans that charge based on peak power draw
- Common in Ausgrid, Endeavour Energy, and other network areas

**✅ Day-of-Week Control**
- Different rates for weekdays vs weekends
- Fine-grained control over when each rate applies

**✅ Full Tesla API Compliance**
- Automatic validation against Tesla restrictions
- No negative prices (clamped to 0)
- Buy rate >= Sell rate enforcement
- Compatible with both Tesla Fleet API and Teslemetry

## Files Created/Modified

### New Files

1. **`app/models.py`** (Modified)
   - Added `CustomTOUSchedule` model
   - Added `TOUSeason` model
   - Added `TOUPeriod` model

2. **`app/custom_tou_builder.py`** (New)
   - `CustomTOUBuilder` class - converts schedules to Tesla tariff format
   - Validation logic for Tesla API restrictions
   - Preview generation for human-readable display

3. **`app/custom_tou_routes.py`** (New)
   - Complete CRUD routes for schedules, seasons, and periods
   - Preview and sync functionality
   - Blueprint registered at `/custom-tou`

4. **`app/forms.py`** (Modified)
   - Added `CustomTOUScheduleForm`
   - Added `TOUSeasonForm`
   - Added `TOUPeriodForm`

5. **`app/__init__.py`** (Modified)
   - Registered custom TOU blueprint

6. **`app/templates/custom_tou/index.html`** (New)
   - Main listing page for custom TOU schedules
   - Cards showing schedule details
   - Actions: Edit, Preview, Sync, Delete, Activate

7. **`CUSTOM_TOU_README.md`** (New)
   - Complete implementation guide
   - Template examples for remaining views
   - Usage examples
   - Common Australian TOU patterns

### Database Migration

✅ Migration created and applied: `23ae28338b34_add_custom_tou_schedule_models.py`

Tables created:
- `custom_tou_schedule`
- `tou_season`
- `tou_period`

## How to Use

### 1. Access the Scheduler
Navigate to: `http://localhost:5000/custom-tou`

### 2. Create a Schedule
Click "Create New Schedule" and fill in:
- Schedule name (e.g., "Origin Energy TOU")
- Utility name (e.g., "Origin Energy")
- Tariff code (optional)
- Daily supply charge
- Monthly charge

### 3. Add Seasons
For each schedule, add one or more seasons:
- Name (e.g., "Summer", "Winter", "All Year")
- Date range (from/to month and day)

### 4. Add Time Periods
For each season, add rate periods:
- Period name (e.g., "Peak", "Shoulder", "Off-Peak")
- Time range (from/to hour and minute - 30min increments)
- Day range (Monday-Sunday)
- Buy rate ($/kWh) - what you pay to import
- Sell rate ($/kWh) - what you get paid to export
- Demand rate ($/kW) - optional capacity charge

### 5. Preview
Click "Preview" to see:
- Human-readable summary
- Complete Tesla API JSON format

### 6. Sync to Tesla
Click "Sync to Tesla" to upload the tariff to your Powerwall.

**Note:** Unlike Amber integration (which updates every 5 minutes), custom schedules are designed to be set once and only updated when your provider changes rates.

## Remaining Tasks

To complete the implementation, you need to create the following template files (examples provided in `CUSTOM_TOU_README.md`):

1. ⏳ `app/templates/custom_tou/create_schedule.html`
2. ⏳ `app/templates/custom_tou/edit_schedule.html`
3. ⏳ `app/templates/custom_tou/add_season.html`
4. ⏳ `app/templates/custom_tou/edit_season.html`
5. ⏳ `app/templates/custom_tou/add_period.html`
6. ⏳ `app/templates/custom_tou/edit_period.html`
7. ⏳ `app/templates/custom_tou/preview.html`

All template examples are provided in `CUSTOM_TOU_README.md` with complete HTML/Jinja2 code ready to copy-paste.

## Example: Origin Energy TOU Plan

Here's how you'd configure a typical Origin Energy TOU plan:

### Schedule Details
- **Name:** Origin Energy Single Rate + TOU
- **Utility:** Origin Energy
- **Code:** EA205
- **Daily Charge:** $1.1770/day

### Season: All Year (1/1 - 12/31)

#### Periods:
1. **Peak**
   - Time: 14:00 - 20:00
   - Days: Monday - Friday
   - Buy: $0.3500/kWh
   - Sell: $0.0500/kWh

2. **Shoulder**
   - Time: 07:00 - 14:00
   - Days: Monday - Friday
   - Buy: $0.2500/kWh
   - Sell: $0.0500/kWh

3. **Off-Peak Weekday**
   - Time: 20:00 - 07:00
   - Days: Monday - Friday
   - Buy: $0.1500/kWh
   - Sell: $0.0500/kWh

4. **Weekend All Day**
   - Time: 00:00 - 00:00
   - Days: Saturday - Sunday
   - Buy: $0.2000/kWh
   - Sell: $0.0500/kWh

## Tesla API Validation

The system automatically validates your schedule against Tesla's requirements:

✅ **No Negative Prices** - All prices clamped to $0 minimum
✅ **Buy >= Sell** - Ensures sell rate never exceeds buy rate
✅ **30-Minute Alignment** - All periods use proper time slots
✅ **No Gaps/Overlaps** - Complete 24-hour coverage

## Advantages Over Tesla's Built-In Rate Plan

| Feature | Tesla Built-In | Custom TOU |
|---------|---------------|------------|
| Maximum rate periods | 4 | Unlimited |
| Time granularity | 1 hour | 30 minutes |
| Seasons | 2 (Summer/Winter) | Unlimited |
| Demand charges | Limited | Full support |
| Complex schedules | ❌ | ✅ |
| Australian NEM aligned | ❌ | ✅ |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (Web)                      │
│  /custom-tou - List, Create, Edit, Preview, Sync Schedules  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Flask Routes (custom_tou_routes.py)            │
│  CRUD operations, Preview generation, Tesla sync            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│          Tariff Builder (custom_tou_builder.py)             │
│  Converts DB models → Tesla API JSON format                 │
│  Validates Tesla restrictions                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
┌────────▼──────────┐              ┌────────▼──────────┐
│  Database Models  │              │   Tesla API       │
│  - Schedule       │              │  - Fleet API      │
│  - Season         │              │  - Teslemetry     │
│  - Period         │              │                   │
└───────────────────┘              └───────────────────┘
```

## Technical Details

### Database Schema

```
custom_tou_schedule
├── id (PK)
├── user_id (FK → user.id)
├── name
├── utility
├── code
├── daily_charge
├── monthly_charge
├── active
├── created_at
├── updated_at
└── last_synced

tou_season
├── id (PK)
├── schedule_id (FK → custom_tou_schedule.id)
├── name
├── from_month
├── from_day
├── to_month
└── to_day

tou_period
├── id (PK)
├── season_id (FK → tou_season.id)
├── name
├── display_order
├── from_hour
├── from_minute (0 or 30)
├── to_hour
├── to_minute (0 or 30)
├── from_day_of_week (0=Mon, 6=Sun)
├── to_day_of_week
├── energy_rate (buy $/kWh)
├── sell_rate (sell $/kWh)
└── demand_rate ($/kW)
```

### Tesla API Format

The builder generates tariffs matching Tesla's exact format:

```json
{
  "version": 1,
  "code": "EA205",
  "name": "Origin Energy TOU",
  "utility": "Origin Energy",
  "currency": "AUD",
  "daily_charges": [{"name": "Supply Charge", "amount": 1.177}],
  "demand_charges": { "Summer": {"rates": {...}} },
  "energy_charges": { "Summer": {"rates": {
    "PERIOD_14_00": 0.35,
    "PERIOD_14_30": 0.35,
    ...
  }}},
  "seasons": {
    "Summer": {
      "fromMonth": 1, "toMonth": 12,
      "fromDay": 1, "toDay": 31,
      "tou_periods": {
        "PERIOD_14_00": {
          "periods": [{
            "fromDayOfWeek": 0,
            "toDayOfWeek": 4,
            "fromHour": 14,
            "toHour": 14,
            "toMinute": 30
          }]
        }
      }
    }
  },
  "sell_tariff": { ... }
}
```

## Testing

To test the implementation:

1. Start the Flask app: `flask run`
2. Navigate to `/custom-tou`
3. Create a test schedule
4. Add a season (e.g., "All Year", 1/1 - 12/31)
5. Add a few time periods
6. Click "Preview" to see the generated JSON
7. Click "Sync to Tesla" (if Tesla is configured)
8. Check Tesla app to confirm rates are displayed correctly

## Support

- Tesla API Documentation: https://developer.tesla.com/docs/fleet-api
- Example Tariff: https://digitalassets-energy.tesla.com/raw/upload/app/fleet-api/example-tariff/PGE-EV2-A.json
- Detailed README: `CUSTOM_TOU_README.md`

## Future Enhancements

Potential additions:
- 📊 Visual schedule editor (drag-and-drop time periods)
- 📈 Cost comparison tools (compare different rate plans)
- 🔄 Import from EnergyMadeEasy API (auto-populate from provider)
- 📱 Mobile-responsive templates
- 🧪 Schedule validation before sync
- 📋 Clone existing schedules
- 🗓️ Schedule history/versioning
