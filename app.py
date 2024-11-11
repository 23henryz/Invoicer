from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime
from config import Config
from models import db, User, Invoice
from forms import InvoiceForm
import json
from quickbook_service import auth_client, refresh_access_token, create_invoice
from quickbook_util import get_customers, get_items

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

refresh_access_token()
customers = get_customers()
items = get_items()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    if current_user.is_anonymous:
        return redirect(url_for('login'))
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('admin_invoices'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_invoices'))
            return redirect(url_for('dashboard')) 
        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = InvoiceForm()

    global customers, items
    if not customers:
        customers = get_customers()
    if not items:
        items = get_items()
    if customers is not None:
        form.Customer_name.choices = [(customer['Id'], customer['DisplayName']) for customer in customers]
        form.Item.choices = [(item['Id'], item['Name']) for item in items]

    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(desc(Invoice.submit_time)).all()
    # if current_user.role == 'user':
    #     invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(desc(Invoice.submit_time)).all()
    # else:
    #     invoices = Invoice.query.order_by(desc(Invoice.submit_time)).all()

    if request.method == 'POST' and form.validate_on_submit():
        new_invoice = Invoice(
            customer_id=form.Customer_name.data,
            customer_name=dict(form.Customer_name.choices).get(form.Customer_name.data),
            customer_email=form.Customer_email.data,
            item_id=form.Item.data,
            item=dict(form.Item.choices).get(form.Item.data),
            price=form.Price.data,
            user_id=current_user.id,
            submit_time=datetime.utcnow()
        )
        db.session.add(new_invoice)
        db.session.commit()
        flash('Invoice submitted successfully!')
        return redirect(url_for('dashboard'))



    return render_template('dashboard.html', invoices=invoices, form=form)


@app.route('/user_management')
@login_required
def user_management():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('user_management.html', users=users)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully!')
    return redirect(url_for('user_management'))


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        user.username = username
        if password: 
            user.password = password
        user.role = role

        db.session.commit()
        flash(f'User {user.username} updated successfully!')
        return redirect(url_for('user_management'))

    return render_template('edit_user.html', user=user)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully!')
        return redirect(url_for('user_management'))

    return render_template('add_user.html')


@app.route('/admin/invoices', methods=['GET', 'POST'])
@login_required
def admin_invoices():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))


    if 'send_single' in request.form:
        invoice_id = request.form.get('send_single')
        invoice = Invoice.query.get(invoice_id)
        if invoice and invoice.status == 'pending':

            create_invoice(invoice.price, invoice.item_id, invoice.customer_email, invoice.customer_id)
            invoice.status = 'sent'
            invoice.send_time = datetime.utcnow()
            db.session.commit()
            print("Send ", invoice)
            flash(f'Invoice {invoice_id} sent successfully!')
        return redirect(url_for('admin_invoices'))

    if 'reject_single' in request.form:
        invoice_id = request.form.get('reject_single')
        invoice = Invoice.query.get(invoice_id)
        if invoice and invoice.status == 'pending':

            invoice.status = 'rejected'
            db.session.commit()
            print("Reject ", invoice)
            flash(f'Invoice {invoice_id} rejected!')
        return redirect(url_for('admin_invoices'))


    if request.method == 'POST' and 'selected_invoices' in request.form:
        selected_invoice_ids = request.form.getlist('selected_invoices')
        for invoice_id in selected_invoice_ids:
            invoice = Invoice.query.get(invoice_id)
            if invoice and invoice.status == 'pending':

                invoice.status = 'sent'
                invoice.send_time = datetime.utcnow()
        db.session.commit()
        flash(f'{len(selected_invoice_ids)} invoice(s) sent successfully!')
        return redirect(url_for('admin_invoices'))

    invoices = Invoice.query.options(db.joinedload(Invoice.owner)).order_by(desc(Invoice.submit_time)).all()
    return render_template('admin_invoices.html', invoices=invoices)

@app.route('/cancel_invoice/<int:invoice_id>', methods=['POST'])
@login_required
def cancel_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if invoice and invoice.status == 'pending':
        invoice.status = 'cancelled'
        db.session.commit()
        flash('Invoice has been cancelled.', 'success')
    else:
        flash('Invoice could not be cancelled.', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/callback')
def callback():
    auth_code = request.args.get('code')
    realm_id = request.args.get('realmId')  

    if not auth_code:
        return "did not receive auth code", 400

    try:
        auth_client.get_bearer_token(auth_code)

        tokens = {
            'access_token': auth_client.access_token,
            'refresh_token': auth_client.refresh_token,
            'realm_id': realm_id 
        }

        with open('tokens.json', 'w') as token_file:
            json.dump(tokens, token_file)

        return f"Successful authentification is！Company ID（realm_id）is: {realm_id}"

    except Exception as e:
        return f"In successful authentification: {e}", 400

    return "Successful authentification，access token acquired."


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password='admin_password', role='admin')
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True,host='0.0.0.0', port=5000)
