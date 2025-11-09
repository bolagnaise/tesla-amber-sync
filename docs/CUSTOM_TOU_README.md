# Custom TOU Scheduler - Implementation Guide

## Overview

The Custom TOU (Time-of-Use) Scheduler allows users to create fixed-rate electricity plans for Australian providers that have complex pricing structures beyond Tesla's built-in 4-tier limitation (Super Off-Peak, Off-Peak, Mid-Peak, Peak).

### Key Features
- ✅ **Unlimited time periods** - Not limited to 4 rate tiers
- ✅ **30-minute granularity** - Precise scheduling aligned with Australian NEM intervals
- ✅ **Multiple seasons** - Support summer/winter rate variations
- ✅ **Demand charges** - Capacity-based fees ($/kW)
- ✅ **Day-of-week control** - Different rates for weekdays/weekends
- ✅ **Full Tesla API compliance** - Validated against Tesla's requirements

## What's Been Implemented

### ✅ Backend (Complete)

1. **Database Models** (`app/models.py`)
   - `CustomTOUSchedule` - Main schedule definition
   - `TOUSeason` - Seasonal periods (e.g., Summer, Winter)
   - `TOUPeriod` - Individual time slots with rates

2. **Tariff Builder** (`app/custom_tou_builder.py`)
   - Converts custom schedules to Tesla API format
   - Validates Tesla restrictions (no negative prices, buy >= sell)
   - Generates 30-minute time slots
   - Handles demand charges

3. **Routes** (`app/custom_tou_routes.py`)
   - CRUD operations for schedules, seasons, periods
   - Preview functionality
   - Sync to Tesla Powerwall

4. **Forms** (`app/forms.py`)
   - `CustomTOUScheduleForm`
   - `TOUSeasonForm`
   - `TOUPeriodForm`

5. **Blueprint Registration** (`app/__init__.py`)
   - Custom TOU blueprint registered at `/custom-tou`

### ⚠️ Templates (Partially Complete)

**Completed:**
- ✅ `templates/custom_tou/index.html` - Main listing page

**To Create:**
- ⏳ `templates/custom_tou/create_schedule.html`
- ⏳ `templates/custom_tou/edit_schedule.html`
- ⏳ `templates/custom_tou/add_season.html`
- ⏳ `templates/custom_tou/edit_season.html`
- ⏳ `templates/custom_tou/add_period.html`
- ⏳ `templates/custom_tou/edit_period.html`
- ⏳ `templates/custom_tou/preview.html`

### ⏳ Remaining Tasks

1. **Database Migration**
   ```bash
   flask db migrate -m "Add custom TOU schedule models"
   flask db upgrade
   ```

2. **Create Remaining Templates** (see templates section below)

3. **Add Navigation Link**
   - Update `templates/base.html` to include link to `/custom-tou`

4. **Update Tesla API Client**
   - Ensure `set_tou_tariff()` method exists in `TeslaEnergyClient` and `TeslemetryClient`

## Database Migration

Run these commands to create the new tables:

```bash
cd /Users/benboller/Downloads/tesla-amber-sync
flask db migrate -m "Add custom TOU schedule models"
flask db upgrade
```

This will create three new tables:
- `custom_tou_schedule`
- `tou_season`
- `tou_period`

## Template Creation Guide

All templates should extend `base.html` and use Bootstrap 5 classes. Here's what each template needs:

### 1. `create_schedule.html`

Simple form to create a new schedule:

```html
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Create Custom TOU Schedule</h2>
    <form method="POST">
        {{ form.hidden_tag() }}

        <div class="mb-3">
            {{ form.name.label(class="form-label") }}
            {{ form.name(class="form-control") }}
        </div>

        <div class="mb-3">
            {{ form.utility.label(class="form-label") }}
            {{ form.utility(class="form-control") }}
        </div>

        <div class="mb-3">
            {{ form.code.label(class="form-label") }}
            {{ form.code(class="form-control") }}
        </div>

        <div class="row">
            <div class="col-md-6 mb-3">
                {{ form.daily_charge.label(class="form-label") }}
                {{ form.daily_charge(class="form-control") }}
            </div>
            <div class="col-md-6 mb-3">
                {{ form.monthly_charge.label(class="form-label") }}
                {{ form.monthly_charge(class="form-control") }}
            </div>
        </div>

        <div class="mb-3 form-check">
            <input type="checkbox" name="set_active" class="form-check-input" id="setActive">
            <label class="form-check-label" for="setActive">Set as active schedule</label>
        </div>

        {{ form.submit(class="btn btn-primary") }}
        <a href="{{ url_for('custom_tou.index') }}" class="btn btn-secondary">Cancel</a>
    </form>
</div>
{% endblock %}
```

### 2. `edit_schedule.html`

Edit schedule + show/manage seasons and periods:

```html
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Edit Schedule: {{ schedule.name }}</h2>

    <!-- Schedule Details Form -->
    <div class="card mb-4">
        <div class="card-header"><h5>Schedule Details</h5></div>
        <div class="card-body">
            <form method="POST">
                {{ form.hidden_tag() }}
                <!-- Same fields as create_schedule.html -->
                {{ form.submit(class="btn btn-primary") }}
            </form>
        </div>
    </div>

    <!-- Seasons List -->
    <div class="card mb-4">
        <div class="card-header d-flex justify-content-between">
            <h5>Seasons</h5>
            <a href="{{ url_for('custom_tou.add_season', schedule_id=schedule.id) }}" class="btn btn-sm btn-primary">
                Add Season
            </a>
        </div>
        <div class="card-body">
            {% for season in seasons %}
                <div class="border p-3 mb-3">
                    <h6>{{ season.name }}</h6>
                    <p>{{ season.from_month }}/{{ season.from_day }} - {{ season.to_month }}/{{ season.to_day }}</p>

                    <!-- Periods in this season -->
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Time</th>
                                <th>Days</th>
                                <th>Buy Rate</th>
                                <th>Sell Rate</th>
                                <th>Demand</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for period in season.periods.order_by('display_order') %}
                            <tr>
                                <td>{{ period.name }}</td>
                                <td>{{ '%02d:%02d'|format(period.from_hour, period.from_minute) }} -
                                    {{ '%02d:%02d'|format(period.to_hour, period.to_minute) }}</td>
                                <td><!-- Format day range --></td>
                                <td>${{ '%.4f'|format(period.energy_rate) }}</td>
                                <td>${{ '%.4f'|format(period.sell_rate) }}</td>
                                <td>{% if period.demand_rate > 0 %}${{ '%.2f'|format(period.demand_rate) }}{% else %}-{% endif %}</td>
                                <td>
                                    <a href="{{ url_for('custom_tou.edit_period', period_id=period.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
                                    <form method="POST" action="{{ url_for('custom_tou.delete_period', period_id=period.id) }}" class="d-inline">
                                        <button type="submit" class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete?')">Delete</button>
                                    </form>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>

                    <a href="{{ url_for('custom_tou.add_period', season_id=season.id) }}" class="btn btn-sm btn-success">
                        Add Period to {{ season.name }}
                    </a>
                    <a href="{{ url_for('custom_tou.edit_season', season_id=season.id) }}" class="btn btn-sm btn-outline-primary">Edit Season</a>
                    <form method="POST" action="{{ url_for('custom_tou.delete_season', season_id=season.id) }}" class="d-inline">
                        <button type="submit" class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete season?')">Delete Season</button>
                    </form>
                </div>
            {% endfor %}
        </div>
    </div>

    <a href="{{ url_for('custom_tou.index') }}" class="btn btn-secondary">Back to Schedules</a>
</div>
{% endblock %}
```

### 3. `add_season.html` / `edit_season.html`

Simple form with date range:

```html
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>{% if season %}Edit{% else %}Add{% endif %} Season</h2>
    <form method="POST">
        {{ form.hidden_tag() }}

        <div class="mb-3">
            {{ form.name.label(class="form-label") }}
            {{ form.name(class="form-control", placeholder="e.g., Summer, Winter, All Year") }}
        </div>

        <div class="row">
            <div class="col-md-6 mb-3">
                {{ form.from_month.label(class="form-label") }}
                {{ form.from_month(class="form-control") }}
            </div>
            <div class="col-md-6 mb-3">
                {{ form.from_day.label(class="form-label") }}
                {{ form.from_day(class="form-control") }}
            </div>
        </div>

        <div class="row">
            <div class="col-md-6 mb-3">
                {{ form.to_month.label(class="form-label") }}
                {{ form.to_month(class="form-control") }}
            </div>
            <div class="col-md-6 mb-3">
                {{ form.to_day.label(class="form-label") }}
                {{ form.to_day(class="form-control") }}
            </div>
        </div>

        {{ form.submit(class="btn btn-primary") }}
        <a href="{{ url_for('custom_tou.edit_schedule', schedule_id=schedule.id) }}" class="btn btn-secondary">Cancel</a>
    </form>
</div>
{% endblock %}
```

### 4. `add_period.html` / `edit_period.html`

Form with time ranges and rates:

```html
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>{% if period %}Edit{% else %}Add{% endif %} Time Period</h2>
    <form method="POST">
        {{ form.hidden_tag() }}

        <div class="mb-3">
            {{ form.name.label(class="form-label") }}
            {{ form.name(class="form-control", placeholder="e.g., Peak, Shoulder, Off-Peak 1") }}
        </div>

        <div class="row">
            <div class="col-md-6">
                <h5>Time Range</h5>
                <div class="row">
                    <div class="col-6 mb-3">
                        {{ form.from_hour.label(class="form-label") }}
                        {{ form.from_hour(class="form-control") }}
                    </div>
                    <div class="col-6 mb-3">
                        {{ form.from_minute.label(class="form-label") }}
                        {{ form.from_minute(class="form-select") }}
                    </div>
                </div>
                <div class="row">
                    <div class="col-6 mb-3">
                        {{ form.to_hour.label(class="form-label") }}
                        {{ form.to_hour(class="form-control") }}
                    </div>
                    <div class="col-6 mb-3">
                        {{ form.to_minute.label(class="form-label") }}
                        {{ form.to_minute(class="form-select") }}
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <h5>Day Range</h5>
                <div class="mb-3">
                    {{ form.from_day_of_week.label(class="form-label") }}
                    {{ form.from_day_of_week(class="form-select") }}
                </div>
                <div class="mb-3">
                    {{ form.to_day_of_week.label(class="form-label") }}
                    {{ form.to_day_of_week(class="form-select") }}
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4 mb-3">
                {{ form.energy_rate.label(class="form-label") }}
                {{ form.energy_rate(class="form-control", step="0.0001") }}
                <small class="text-muted">What you pay to import from grid</small>
            </div>
            <div class="col-md-4 mb-3">
                {{ form.sell_rate.label(class="form-label") }}
                {{ form.sell_rate(class="form-control", step="0.0001") }}
                <small class="text-muted">What you get paid to export</small>
            </div>
            <div class="col-md-4 mb-3">
                {{ form.demand_rate.label(class="form-label") }}
                {{ form.demand_rate(class="form-control", step="0.0001") }}
                <small class="text-muted">Capacity charge (optional)</small>
            </div>
        </div>

        <div class="alert alert-warning">
            <strong>Tesla Restriction:</strong> Sell rate must be ≤ Buy rate. Negative prices not allowed.
        </div>

        {{ form.submit(class="btn btn-primary") }}
        <a href="{{ url_for('custom_tou.edit_schedule', schedule_id=season.schedule_id) }}" class="btn btn-secondary">Cancel</a>
    </form>
</div>
{% endblock %}
```

### 5. `preview.html`

Show human-readable preview + JSON tariff:

```html
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Preview: {{ schedule.name }}</h2>

    <div class="card mb-4">
        <div class="card-header"><h5>Human-Readable Preview</h5></div>
        <div class="card-body">
            <p><strong>Utility:</strong> {{ preview.utility }}</p>
            <p><strong>Code:</strong> {{ preview.code or 'N/A' }}</p>
            <p><strong>Daily Charge:</strong> ${{ '%.4f'|format(preview.daily_charge) }}</p>

            {% for season in preview.seasons %}
                <h6>{{ season.name }} ({{ season.date_range }})</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>Time</th>
                            <th>Days</th>
                            <th>Buy Rate</th>
                            <th>Sell Rate</th>
                            <th>Demand</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for period in season.periods %}
                        <tr>
                            <td>{{ period.name }}</td>
                            <td>{{ period.time }}</td>
                            <td>{{ period.days }}</td>
                            <td>{{ period.energy_rate }}</td>
                            <td>{{ period.sell_rate }}</td>
                            <td>{{ period.demand_rate }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% endfor %}
        </div>
    </div>

    <div class="card mb-4">
        <div class="card-header"><h5>Tesla API JSON</h5></div>
        <div class="card-body">
            <pre class="bg-light p-3" style="max-height: 500px; overflow-y: auto;">{{ tariff_json | tojson(indent=2) }}</pre>
        </div>
    </div>

    <a href="{{ url_for('custom_tou.edit_schedule', schedule_id=schedule.id) }}" class="btn btn-secondary">Back to Edit</a>
    <form method="POST" action="{{ url_for('custom_tou.sync_to_tesla', schedule_id=schedule.id) }}" class="d-inline">
        <button type="submit" class="btn btn-success">Sync to Tesla Now</button>
    </form>
</div>
{% endblock %}
```

## Adding Navigation Link

Update `templates/base.html` to add a link to the custom TOU scheduler in the navigation menu:

```html
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('custom_tou.index') }}">
        <i class="bi bi-calendar-range"></i> Custom TOU
    </a>
</li>
```

## Tesla API Client Updates

Ensure both `TeslaEnergyClient` and `TeslemetryClient` in `app/api_clients.py` have the `set_tou_tariff()` method:

```python
def set_tou_tariff(self, site_id, tariff_data):
    """Set TOU tariff for an energy site"""
    try:
        payload = {
            "tou_settings": {
                "tariff_content_v2": tariff_data
            }
        }

        response = requests.post(
            f"{self.base_url}/api/1/energy_sites/{site_id}/time_of_use_settings",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error setting TOU tariff: {e}")
        return False
```

## Utility Provider & Rate Plan Settings

The system now includes a dedicated section for setting your Utility Provider and Rate Plan Name, which map directly to Tesla's API fields:

### Tesla API Fields

1. **Utility Provider** (`utility` in API)
   - Your electricity company name
   - Examples: "Origin Energy", "AGL", "Energy Australia", "EnergyAustralia"
   - This appears in the Tesla app as the provider name
   - **Required field**

2. **Rate Plan Name** (`name` in API)
   - Descriptive name for your specific tariff
   - Examples: "Single Rate + TOU", "Residential Demand TOU", "EV Charging Plan"
   - This appears in the Tesla app as the tariff/plan name
   - **Required field**

3. **Tariff Code** (`code` in API)
   - Official tariff code from your provider (optional)
   - Examples: "EA205", "DMO1", "TOU-GS", "C1R"
   - Find this on your electricity bill
   - **Optional field**

### How It Appears in Tesla App

```
Tesla App Display:
┌─────────────────────────────────────┐
│ Utility Rate Plan                   │
├─────────────────────────────────────┤
│ Origin Energy                       │ ← Utility Provider
│ Single Rate + TOU (EA205)           │ ← Rate Plan Name (Code)
│                                     │
│ Daily Supply: $1.18                 │
│ Time-of-Use Rates: 4 periods        │
└─────────────────────────────────────┘
```

## Usage Example

1. **Navigate to Custom TOU** - `/custom-tou`

2. **Create Schedule** - Set Utility Provider & Rate Plan:
   - **Utility Provider:** "Origin Energy"
   - **Rate Plan Name:** "Single Rate + TOU"
   - **Tariff Code:** "EA205" (optional)
   - **Daily Charge:** $1.1770
   - **Monthly Charge:** $0.00

3. **Add Season** - "All Year" (1/1 to 12/31)

4. **Add Periods:**
   - Peak: 14:00-20:00, Mon-Fri, $0.35/kWh buy, $0.05/kWh sell
   - Shoulder: 07:00-14:00, Mon-Fri, $0.25/kWh buy, $0.05/kWh sell
   - Off-Peak 1: 20:00-07:00, Mon-Fri, $0.15/kWh buy, $0.05/kWh sell
   - Weekend: 00:00-00:00, Sat-Sun, $0.20/kWh buy, $0.05/kWh sell

5. **Preview** - Check the generated tariff

6. **Sync to Tesla** - One-time upload to Powerwall

## Tesla API Validation

The system automatically validates:
- ✅ No negative prices (clamped to 0)
- ✅ Buy rate >= Sell rate for all periods
- ✅ All time periods use 30-minute alignment
- ✅ No gaps or overlaps in TOU periods

## Common Australian TOU Patterns

### Pattern 1: Simple 3-Tier (Origin Energy Single Rate + TOU)
- Peak: 14:00-20:00 weekdays
- Shoulder: 07:00-14:00 & 20:00-22:00 weekdays
- Off-Peak: All other times

### Pattern 2: 5-Period Complex (AGL)
- Peak: 15:00-21:00 weekdays (summer)
- Peak: 17:00-21:00 weekdays (winter)
- Shoulder AM: 07:00-09:00 weekdays
- Shoulder PM: 17:00-20:00 weekdays
- Off-Peak: All other times

### Pattern 3: Demand + TOU (Ausgrid/Endeavour)
- Energy rates: Standard 3-tier
- Demand charge: Peak period only ($/kW for maximum draw)

## Testing Checklist

- [ ] Run database migration
- [ ] Create a test schedule
- [ ] Add seasons and periods
- [ ] Preview tariff JSON
- [ ] Sync to Tesla (check Tesla app shows correct rates)
- [ ] Delete test schedule

## Support

For Tesla API documentation:
- https://developer.tesla.com/docs/fleet-api/endpoints/energy
- Example tariff: https://digitalassets-energy.tesla.com/raw/upload/app/fleet-api/example-tariff/PGE-EV2-A.json
