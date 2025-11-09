# Utility Provider & Rate Plan Enhancement

## Summary

Added a dedicated, prominent section for configuring **Utility Provider** and **Rate Plan Name** settings in the Custom TOU Scheduler, ensuring clear alignment with Tesla's API requirements and how the information appears in the Tesla mobile app.

## What Was Changed

### 1. Enhanced Forms (`app/forms.py`)

Updated `CustomTOUScheduleForm` with:

**Field Order (now prominently placed first):**
1. **Utility Provider** (required)
   - Label: "Utility Provider"
   - Description: "Your electricity company (e.g., 'Origin Energy', 'AGL', 'Energy Australia')"
   - Maps to Tesla API `utility` field

2. **Rate Plan Name** (required)
   - Label: "Rate Plan Name"
   - Description: "Descriptive name for this rate plan (e.g., 'Single Rate + TOU', 'Residential Demand TOU')"
   - Maps to Tesla API `name` field

3. **Tariff Code** (optional)
   - Label: "Tariff Code (Optional)"
   - Description: "Official tariff code from your provider (e.g., 'EA205', 'DMO1', 'TOU-GS')"
   - Maps to Tesla API `code` field

All fields now include:
- Clear, descriptive labels
- Helper text with real Australian provider examples
- Validation where appropriate

### 2. New Templates

#### `create_schedule.html`
- **Dedicated Card Section** with primary styling for Utility Provider & Rate Plan
- **Live Preview** showing how the information will appear in Tesla app
- **JavaScript** for real-time preview updates as user types
- **Contextual Help** explaining what each field does
- **Visual Hierarchy** with the most important Tesla API fields prominently displayed
- **Example Values** in placeholders (e.g., "Origin Energy", "Single Rate + TOU")

#### `edit_schedule.html`
- **Prominent Card** at top with primary border styling
- **Large Form Controls** for key fields (utility and name)
- **Last Synced Badge** showing when the schedule was last uploaded to Tesla
- **Complete Season/Period Management** below the main settings
- **Visual Table** showing all configured time periods with color-coded rates

### 3. Updated Documentation

**CUSTOM_TOU_README.md** now includes:
- Dedicated section explaining Utility Provider & Rate Plan settings
- Clear mapping to Tesla API fields
- ASCII diagram showing how it appears in Tesla app
- Examples from popular Australian providers

## Tesla API Mapping

```python
# Form Fields → Tesla API
{
    "utility": form.utility.data,           # e.g., "Origin Energy"
    "name": form.name.data,                 # e.g., "Single Rate + TOU"
    "code": form.code.data or f"CUSTOM:{schedule.id}",  # e.g., "EA205"
    "currency": "AUD",
    "daily_charges": [{"name": "Supply Charge", "amount": form.daily_charge.data}],
    "monthly_charges": form.monthly_charge.data,
    ...
}
```

## User Experience Improvements

### Before
```
Simple form fields:
- Schedule Name: [         ]
- Utility/Provider: [         ]
- Code: [         ]
```

### After
```
┌─────────────────────────────────────────────────┐
│ 🏢 Utility Provider & Rate Plan                │  ← Primary card
├─────────────────────────────────────────────────┤
│ ℹ️ These settings appear in your Tesla app     │  ← Context
│                                                 │
│ Utility Provider* ────────────────────────────  │
│ [Origin Energy                            ]▼   │  ← Large controls
│ Your electricity company (e.g., "Origin Energy")│  ← Helper text
│                                                 │
│ Rate Plan Name* ──────────────────────────────  │
│ [Single Rate + TOU                        ]▼   │
│ Descriptive name for this rate plan...         │
│                                                 │
│ Tariff Code (Optional) ────────────────────────│
│ [EA205                                     ]   │
│ Official tariff code from your provider...      │
│                                                 │
│ Tesla App Display:                              │  ← Live preview
│ [Utility: Origin Energy] [Plan: Single Rate...]│
└─────────────────────────────────────────────────┘
```

## Tesla App Display

When synced to Tesla, users will see:

```
Tesla Mobile App
┌─────────────────────────────────────┐
│ ⚡ Energy Settings                  │
├─────────────────────────────────────┤
│ Current Rate Plan                   │
│                                     │
│ Origin Energy                       │ ← utility
│ Single Rate + TOU (EA205)           │ ← name (code)
│                                     │
│ Daily Charge: $1.18                 │
│                                     │
│ Time Periods:                       │
│ • Peak (14:00-20:00)    $0.35/kWh  │
│ • Shoulder (07:00-14:00) $0.25/kWh │
│ • Off-Peak (20:00-07:00) $0.15/kWh │
│ • Weekend (All Day)      $0.20/kWh │
└─────────────────────────────────────┘
```

## Common Australian Providers

Examples users can reference:

### Major Retailers
- **Origin Energy**
  - Plans: "Single Rate + TOU", "Demand TOU", "Solar Boost"
  - Codes: "EA205", "EA225", etc.

- **AGL**
  - Plans: "Residential TOU", "Solar Savers", "Value Saver"
  - Codes: Vary by state

- **Energy Australia**
  - Plans: "Total Plan Home", "Secure Saver", "No Fuss"
  - Codes: Varies

### Smaller Retailers
- **Amber Electric** (already handled by separate integration)
- **Powershop**
- **Sumo**
- **OVO Energy**

### Network-Based TOU
- **Ausgrid Area** - Often "Demand TOU" with capacity charges
- **Endeavour Energy** - TOU with demand windows
- **Essential Energy** - Regional NSW TOU plans

## Benefits

1. **Clarity** - Users immediately understand what information Tesla needs
2. **Accuracy** - Helper text and examples reduce data entry errors
3. **Confidence** - Live preview shows exactly how it will appear in Tesla app
4. **Compliance** - Ensures required Tesla API fields are always populated
5. **Professional** - Matches Tesla's terminology and user expectations

## Technical Implementation

### Form Validation
```python
# Required fields enforced at form level
utility = StringField('Utility Provider', validators=[DataRequired()])
name = StringField('Rate Plan Name', validators=[DataRequired()])

# Optional field with helpful description
code = StringField('Tariff Code (Optional)', validators=[Optional()])
```

### Live Preview (JavaScript)
```javascript
// Real-time updates as user types
utilityInput.addEventListener('input', function() {
    previewUtility.textContent = this.value || 'Your Provider';
});

nameInput.addEventListener('input', function() {
    previewPlan.textContent = this.value || 'Your Plan Name';
});
```

### Card Styling
```html
<div class="card mb-4 border-primary">
    <div class="card-header bg-primary text-white">
        <h5>🏢 Utility Provider & Rate Plan</h5>
    </div>
    <div class="card-body">
        <!-- Form fields with large controls -->
        {{ form.utility(class="form-control form-control-lg") }}
    </div>
</div>
```

## Testing

To verify the enhancement:

1. Navigate to `/custom-tou/create`
2. Observe the prominent "Utility Provider & Rate Plan" section
3. Type in the Utility field → watch live preview update
4. Type in the Rate Plan Name → watch preview update
5. Fill in all fields and create schedule
6. Edit the schedule → verify fields are pre-populated
7. Sync to Tesla → check Tesla app shows correct provider and plan name

## Files Modified

- ✅ `app/forms.py` - Enhanced `CustomTOUScheduleForm`
- ✅ `app/templates/custom_tou/create_schedule.html` - New template with dedicated section
- ✅ `app/templates/custom_tou/edit_schedule.html` - New template with prominent display
- ✅ `CUSTOM_TOU_README.md` - Added documentation for Utility Provider settings

## Screenshot Mockup

```
┌────────────────────────────────────────────────────────────────┐
│ Custom TOU Schedules > Create Schedule                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🏢 Utility Provider & Rate Plan                         [📝]  │ ← Primary
│  ───────────────────────────────────────────────────────────   │
│  ℹ️ These settings will appear in your Tesla app exactly as    │
│     entered. Choose names that match your electricity bill.    │
│                                                                 │
│  Utility Provider *                                             │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Origin Energy                                          │   │ ← Large input
│  └────────────────────────────────────────────────────────┘   │
│  Your electricity company (e.g., "Origin Energy", "AGL")       │
│                                                                 │
│  Rate Plan Name *                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Single Rate + TOU                                      │   │
│  └────────────────────────────────────────────────────────┘   │
│  Descriptive name for this rate plan                           │
│                                                                 │
│  Tariff Code (Optional)                                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ EA205                                                  │   │
│  └────────────────────────────────────────────────────────┘   │
│  Official tariff code from your provider                        │
│                                                                 │
│  📱 Tesla App Display:                                          │
│  ╔══════════════════════════════════════╗                      │
│  ║ Utility: Origin Energy               ║                      │
│  ║ Plan: Single Rate + TOU              ║  ← Live preview     │
│  ║ Code: EA205                          ║                      │
│  ╚══════════════════════════════════════╝                      │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  💵 Fixed Charges                                               │
│  ──────────────────────────────────────────────────────        │
│  Enter any fixed daily or monthly charges...                   │
│  ...                                                            │
└────────────────────────────────────────────────────────────────┘
```

## Future Enhancements

Potential additions:
- 🔍 Provider database/autocomplete for common Australian utilities
- 📋 Template selector (pre-fill based on known provider plans)
- ✅ Real-time validation against provider's published rate cards
- 🔗 Direct link to provider's tariff information
- 📊 Comparison with default market offer (DMO)
