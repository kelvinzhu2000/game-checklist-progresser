from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User, Game

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ChecklistForm(FlaskForm):
    title = StringField('Checklist Title', validators=[DataRequired(), Length(max=200)])
    game_name = StringField('Game Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    ai_prompt = TextAreaField('AI Generation Prompt (Optional)', 
                              description='Describe what items you want in this checklist, and AI will generate them for you.')
    is_public = BooleanField('Make Public', default=True)
    submit = SubmitField('Create Checklist')

class ChecklistItemForm(FlaskForm):
    title = StringField('Item Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    location = StringField('Location', validators=[Length(max=100)])
    category = StringField('Category', validators=[Length(max=100)])
    submit = SubmitField('Add Item')

class ChecklistEditForm(FlaskForm):
    title = StringField('Checklist Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    ai_prompt = TextAreaField('AI Generation Prompt (Optional)', 
                              description='Describe what new items you want to add to this checklist, and AI will generate them for you.')
    is_public = BooleanField('Make Public', default=True)
    submit = SubmitField('Update Checklist')

class GameForm(FlaskForm):
    name = StringField('Game Name', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Add Game')
    
    def validate_name(self, name):
        game = Game.query.filter_by(name=name.data).first()
        if game:
            raise ValidationError('This game already exists.')
