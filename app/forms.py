# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
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
    submit = SubmitField('Save Environment Settings')

