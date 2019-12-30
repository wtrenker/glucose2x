from flask_wtf import FlaskForm
from wtforms import Form, TextAreaField, DecimalField, validators, StringField, SubmitField, IntegerField, SubmitField,\
    RadioField, SelectField, TextField, PasswordField

class DataEntryForm(FlaskForm):
    ddate = StringField('Date:', validators=[validators.DataRequired()])
    amreading = DecimalField('Morning:', validators=[validators.DataRequired()] )  #, places=1
    pmreading = DecimalField('Evening:')  #, validators=[validators.DataRequired()] )  #, places=1
    annotation = StringField('Annotation')
    submit = SubmitField("Record Data")

class DEholdEntryForm(FlaskForm):
    date = StringField('Date')
    heldValue = DecimalField("Held Value")

class HeldDatesForm(FlaskForm):
    helddateslist = SelectField('Held Dates')
    submit = SubmitField("Send")

class SelectReadingForm(FlaskForm):
    helddateslist = SelectField('Held Dates')
    submit = SubmitField("Select")

class EditReadingForm(FlaskForm):
    readingDate = StringField('Date')
    amreading = DecimalField("Morning")
    pmreading = DecimalField('Evening:')
    annotation = StringField('Annotation')
    submit = SubmitField("Update")

class SigninForm(FlaskForm):
    code = PasswordField('Code')
    submit = SubmitField('Continue')

class PickReadingForm(FlaskForm):
    date = StringField('Date')
    submit = SubmitField('Pick')
