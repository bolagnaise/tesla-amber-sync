# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DecimalField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, NumberRange
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class SettingsForm(FlaskForm):
    amber_token = StringField('Amber Electric API Token')
    tesla_site_id = StringField('Tesla Energy Site ID')
    teslemetry_api_key = StringField('Teslemetry API Key (get from teslemetry.com)')
    submit = SubmitField('Save Settings')


class EnvironmentForm(FlaskForm):
    """Form for updating environment variables (Tesla Developer credentials)"""
    tesla_client_id = StringField('Tesla Client ID')
    tesla_client_secret = StringField('Tesla Client Secret')
    tesla_redirect_uri = StringField('Tesla Redirect URI')
    app_domain = StringField('App Domain')
    tesla_region = SelectField('Tesla Fleet API Region', choices=[
        ('na', 'North America'),
        ('eu', 'Europe / Asia-Pacific (Australia)'),
        ('cn', 'China')
    ], default='na')
    submit = SubmitField('Save Environment Settings')


class DemandChargeForm(FlaskForm):
    """Form for configuring demand charge periods"""
    # Enable/disable demand charges
    enable_demand_charges = BooleanField('Enable Demand Charges')

    # Peak demand period
    peak_rate = DecimalField('Peak Rate ($/kW)', validators=[Optional(), NumberRange(min=0)], places=4, default=0)
    peak_start_hour = IntegerField('Peak Start Hour', validators=[Optional(), NumberRange(min=0, max=23)], default=14)
    peak_start_minute = IntegerField('Peak Start Minute', validators=[Optional(), NumberRange(min=0, max=59)], default=0)
    peak_end_hour = IntegerField('Peak End Hour', validators=[Optional(), NumberRange(min=0, max=23)], default=20)
    peak_end_minute = IntegerField('Peak End Minute', validators=[Optional(), NumberRange(min=0, max=59)], default=0)
    peak_days = SelectField('Peak Days', choices=[
        ('weekdays', 'Weekdays Only'),
        ('all', 'All Days'),
        ('weekends', 'Weekends Only')
    ], default='weekdays')

    # Off-peak demand period
    offpeak_rate = DecimalField('Off-Peak Rate ($/kW)', validators=[Optional(), NumberRange(min=0)], places=4, default=0)

    # Shoulder demand period (optional)
    shoulder_rate = DecimalField('Shoulder Rate ($/kW)', validators=[Optional(), NumberRange(min=0)], places=4, default=0)
    shoulder_start_hour = IntegerField('Shoulder Start Hour', validators=[Optional(), NumberRange(min=0, max=23)], default=7)
    shoulder_start_minute = IntegerField('Shoulder Start Minute', validators=[Optional(), NumberRange(min=0, max=59)], default=0)
    shoulder_end_hour = IntegerField('Shoulder End Hour', validators=[Optional(), NumberRange(min=0, max=23)], default=14)
    shoulder_end_minute = IntegerField('Shoulder End Minute', validators=[Optional(), NumberRange(min=0, max=59)], default=0)

    submit = SubmitField('Save Demand Charges')

