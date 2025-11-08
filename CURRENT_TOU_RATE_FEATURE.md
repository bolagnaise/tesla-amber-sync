# Current TOU Rate Feature - Implementation Summary

## Overview

A new "Current TOU Rate" feature has been added to the Flask web application. This feature allows users to:
1. **View** the current TOU (Time-of-Use) tariff programmed in their Tesla Powerwall
2. **Save** snapshots of tariff configurations to the database
3. **Restore** previously saved tariffs back to Tesla
4. **Manage** a library of saved tariff profiles

## Implementation Date
November 8, 2024

## Database Changes

### New Model: `SavedTOUProfile`

**Location:** `app/models.py`

**Fields:**
- `id` - Primary key
- `user_id` - Foreign key to User
- `name` - User-provided name for the profile
- `description` - Optional description
- `source_type` - Type of tariff ('tesla', 'custom', 'amber')
- `tariff_name` - Name from the tariff structure
- `utility` - Utility company name
- `tariff_json` - Complete Tesla tariff JSON (Text field)
- `created_at` - When the profile was saved
- `fetched_from_tesla_at` - When it was retrieved from Tesla
- `last_restored_at` - When it was last restored to Tesla
- `is_current` - Boolean flag indicating if this is the current tariff

**Migration:**
- File: `migrations/versions/9d453fbea5d9_add_savedtouprofile_model_for_backing_.py`
- Status: ✅ Applied successfully

## API Client Changes

### TeslemetryAPIClient

**New Method:** `get_current_tariff(site_id)`

**Location:** `app/api_clients.py` (line 351-385)

**Purpose:** Fetches the current TOU tariff from Tesla Powerwall via site_info endpoint

**Returns:** Complete tariff structure dictionary or None if error

**How it works:**
1. Calls `get_site_info(site_id)`
2. Extracts `utility_tariff_content_v2` from the response
3. Returns the complete tariff JSON

### TeslaFleetAPIClient

**New Method:** `get_current_tariff(site_id)`

**Location:** `app/api_clients.py` (line 744-778)

**Purpose:** Same functionality for Tesla Fleet API users

## Routes Added

### Main Route: `/current_tou_rate`

**Handler:** `current_tou_rate()`
**Methods:** GET
**Purpose:** Display current tariff and list saved profiles

**What it does:**
1. Fetches current tariff from Tesla using `get_current_tariff()`
2. Queries all saved profiles for the current user
3. Renders the `current_tou_rate.html` template

### Save Route: `/current_tou_rate/save`

**Handler:** `save_current_tou_rate()`
**Methods:** POST
**Purpose:** Save current tariff to database

**Form Fields:**
- `profile_name` (required) - Name for this saved profile
- `description` (optional) - Description of the profile

**What it does:**
1. Validates profile name is provided
2. Fetches current tariff from Tesla
3. Creates new `SavedTOUProfile` record
4. Marks all other profiles as `is_current=False`
5. Marks this new profile as `is_current=True`
6. Stores complete tariff JSON

### Restore Route: `/current_tou_rate/restore/<profile_id>`

**Handler:** `restore_tou_rate(profile_id)`
**Methods:** POST
**Purpose:** Restore a saved tariff back to Tesla

**What it does:**
1. Loads the saved profile from database
2. Parses the tariff JSON
3. Calls `tesla_client.set_tariff_rate()` to upload to Tesla
4. Updates `last_restored_at` timestamp
5. Marks profile as `is_current=True`

### Delete Route: `/current_tou_rate/delete/<profile_id>`

**Handler:** `delete_tou_profile(profile_id)`
**Methods:** POST
**Purpose:** Delete a saved profile

### API Route: `/api/current_tou_rate/raw`

**Handler:** `api_current_tou_rate_raw()`
**Methods:** GET
**Purpose:** Returns raw JSON of current tariff (for debugging/integration)

## User Interface

### New Page: `current_tou_rate.html`

**Location:** `app/templates/current_tou_rate.html`

**Sections:**

1. **Current Tariff from Tesla Powerwall**
   - Displays tariff name, utility, code, currency
   - Shows daily charges, number of seasons, rate periods
   - Expandable raw JSON view
   - Form to save current tariff with name and description

2. **Saved TOU Rate Profiles**
   - Table listing all saved profiles
   - Columns: Name, Tariff, Utility, Saved Date, Last Restored, Status
   - Actions: Restore button, Delete button
   - "Current" badge for the active tariff

3. **Help Section**
   - Explains how the feature works
   - Use cases for saving profiles
   - Note about Amber auto-sync

### Navigation

**Updated:** `app/templates/base.html` (line 27)

**Added menu item:** "Current TOU Rate" between "Custom TOU" and "API Testing"

## Use Cases

### 1. Before Switching to Amber

```
1. User is on AGL fixed-rate tariff
2. User clicks "Current TOU Rate"
3. User sees their current AGL tariff
4. User saves it as "Original AGL Tariff"
5. User switches to Amber
6. If they want to switch back, they restore the saved profile
```

### 2. Seasonal Rate Changes

```
1. User has summer rates configured
2. User saves current tariff as "Summer 2024"
3. Winter comes, utility changes rates
4. User manually updates tariff or syncs from utility
5. User saves as "Winter 2024"
6. Next summer, user restores "Summer 2024" profile
```

### 3. Testing Custom TOU Schedules

```
1. User saves current tariff as "Backup before testing"
2. User creates and syncs custom TOU schedule
3. If it doesn't work well, user restores "Backup before testing"
```

### 4. Multiple Utility Comparison

```
1. User saves "Origin Energy Current"
2. User saves "AGL Proposed"
3. User tests each by restoring and monitoring battery behavior
4. User picks the best one
```

## Technical Details

### Tariff Storage Format

The complete Tesla tariff JSON is stored as text in the `tariff_json` field. Example structure:

```json
{
  "version": 1,
  "code": "GLOBIRD",
  "name": "VPP",
  "utility": "GLOBIRD",
  "currency": "AUD",
  "daily_charges": [
    {
      "name": "Supply Charge",
      "amount": 0.85
    }
  ],
  "seasons": {
    "ALL_YEAR": {
      "fromMonth": 1,
      "toMonth": 12,
      "tou_periods": {
        "PERIOD_16_00": {
          "periods": [
            {
              "fromHour": 16,
              "fromMinute": 0,
              "toHour": 16,
              "toMinute": 30
            }
          ]
        }
      }
    }
  },
  "energy_charges": {
    "ALL_YEAR": {
      "rates": {
        "PERIOD_16_00": 0.25
      }
    }
  }
}
```

### Data Flow

**Fetching Current Tariff:**
```
User clicks "Current TOU Rate"
  ↓
Route: current_tou_rate()
  ↓
get_tesla_client(current_user)
  ↓
tesla_client.get_current_tariff(site_id)
  ↓
tesla_client.get_site_info(site_id)
  ↓
Teslemetry/Fleet API: GET /api/1/energy_sites/{id}/site_info
  ↓
Extract response['utility_tariff_content_v2']
  ↓
Return to template
```

**Saving Profile:**
```
User fills form and clicks "Save"
  ↓
POST /current_tou_rate/save
  ↓
Fetch current tariff from Tesla
  ↓
Create SavedTOUProfile record
  ↓
Store JSON in tariff_json field
  ↓
Mark as is_current=True
  ↓
Commit to database
  ↓
Redirect back to page
```

**Restoring Profile:**
```
User clicks "Restore" on saved profile
  ↓
POST /current_tou_rate/restore/<id>
  ↓
Load SavedTOUProfile from database
  ↓
Parse tariff_json back to dict
  ↓
tesla_client.set_tariff_rate(site_id, tariff_data)
  ↓
Teslemetry/Fleet API: POST /api/1/energy_sites/{id}/time_of_use_settings
  ↓
Update last_restored_at timestamp
  ↓
Mark as is_current=True
  ↓
Redirect back to page
```

## Security Considerations

✅ **Authentication Required:** All routes require `@login_required`
✅ **User Isolation:** Queries filter by `user_id` to prevent access to other users' profiles
✅ **SQL Injection:** Using SQLAlchemy ORM prevents SQL injection
✅ **XSS Protection:** Flask's Jinja2 auto-escapes template variables

## Error Handling

**No Tesla Client:**
- Redirects to dashboard with message: "Please configure your Tesla API credentials first."

**No Site ID:**
- Redirects to dashboard with message: "Please configure your Tesla energy site ID first."

**No Tariff Data:**
- Displays warning alert explaining possible causes
- Continues to show saved profiles section

**API Errors:**
- Caught in try/except blocks
- Logged to Flask logs
- User-friendly flash messages displayed

## Testing Checklist

- [ ] Navigate to "Current TOU Rate" page
- [ ] Verify current tariff displays correctly
- [ ] Save a tariff profile with name and description
- [ ] Verify saved profile appears in table
- [ ] Restore a saved profile
- [ ] Verify "Current" badge moves to restored profile
- [ ] Delete a saved profile
- [ ] Check raw JSON endpoint: `/api/current_tou_rate/raw`
- [ ] Test with no tariff configured
- [ ] Test with Tesla API disconnected
- [ ] Test saving multiple profiles
- [ ] Verify database migration worked correctly

## Future Enhancements

Possible additions:

1. **Diff View:** Compare two saved profiles side-by-side
2. **Export/Import:** Download tariff as JSON file, upload from file
3. **Tariff Analysis:** Show graphs of rates throughout the day
4. **Auto-Save:** Automatically save tariff before Amber sync
5. **Version History:** Track changes to tariffs over time
6. **Share Profiles:** Export profile as shareable link/code
7. **Tariff Calculator:** Estimate monthly cost based on usage patterns

## Files Changed

```
app/models.py                               ✓ Added SavedTOUProfile model
app/api_clients.py                          ✓ Added get_current_tariff() to both clients
app/routes.py                               ✓ Added 5 new routes
app/templates/current_tou_rate.html         ✓ New template (created)
app/templates/base.html                     ✓ Added navigation link
migrations/versions/9d453fbea5d9_...py      ✓ New migration (applied)
```

## Known Issues

None currently identified.

## Support

If users encounter issues:
1. Check Flask logs for detailed error messages
2. Verify Tesla API credentials are configured
3. Verify site ID is correct
4. Test Teslemetry/Fleet API connection on API Status page
5. Check that Powerwall has a tariff configured

## Documentation

See also:
- `PROJECT_STRUCTURE_ANALYSIS.md` - Overall project structure
- `DEMAND_CHARGE_IMPLEMENTATION.md` - HA integration demand charges
- `README.md` - Main project documentation

---

**Implementation completed by Claude Code on November 8, 2024**
