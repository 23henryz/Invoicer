from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

class InvoiceForm(FlaskForm):
    Customer_name = SelectField('Customer Name', choices=[], validators=[DataRequired()])  
    Customer_email = StringField('Customer Email', validators=[DataRequired(), Email()])
    Item = SelectField('Item', choices=[], validators=[DataRequired()]) 
    Price = FloatField('Price', validators=[DataRequired()])
    submit = SubmitField('Submit Invoice')
