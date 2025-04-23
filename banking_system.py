# main.py

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
import decimal

# .env faylidan konfiguratsiyani yuklash
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ma'lumotlar modellari
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    accounts = db.relationship('Account', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deposits = db.relationship('Deposit', backref='account', lazy=True)
    
    def deposit_money(self, amount):
        self.balance += decimal.Decimal(amount)
        db.session.commit()
    
    def withdraw_money(self, amount):
        if self.balance >= decimal.Decimal(amount):
            self.balance -= decimal.Decimal(amount)
            db.session.commit()
            return True
        return False

class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)  # Yillik foiz stavkasi
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    
    def calculate_interest(self):
        if not self.is_active:
            return 0
            
        # Joriy sana bilan omonat boshlanish sanasi orasidagi kunlar soni
        today = datetime.utcnow()
        if today > self.end_date:
            days = (self.end_date - self.start_date).days
        else:
            days = (today - self.start_date).days
            
        if days <= 0:
            return 0
            
        # Kunlik foiz hisobi
        daily_rate = float(self.interest_rate) / 365 / 100
        interest = float(self.amount) * daily_rate * days
        
        return round(interest, 2)
    
    def close_deposit(self):
        if self.is_active:
            interest = self.calculate_interest()
            self.is_active = False
            db.session.commit()
            return interest
        return 0

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit', 'withdrawal', 'interest'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routelar
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Bunday foydalanuvchi nomi mavjud.')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Bunday email mavjud.')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Ro\'yxatdan muvaffaqiyatli o\'tdingiz!')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Login yoki parol noto\'g\'ri!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', accounts=accounts)

@app.route('/account/create', methods=['GET', 'POST'])
@login_required
def create_account():
    if request.method == 'POST':
        import random
        account_number = f"ACC{random.randint(10000, 99999)}"
        
        account = Account(account_number=account_number, user_id=current_user.id)
        db.session.add(account)
        db.session.commit()
        
        flash('Yangi hisob yaratildi!')
        return redirect(url_for('dashboard'))
        
    return render_template('create_account.html')

@app.route('/account/<int:account_id>')
@login_required
def account_details(account_id):
    account = Account.query.get_or_404(account_id)
    
    if account.user_id != current_user.id and not current_user.is_admin:
        flash('Bu hisobga kirishga ruxsatingiz yo\'q!')
        return redirect(url_for('dashboard'))
        
    deposits = Deposit.query.filter_by(account_id=account_id).all()
    transactions = Transaction.query.filter_by(account_id=account_id).order_by(Transaction.timestamp.desc()).limit(10).all()
    
    return render_template('account_details.html', account=account, deposits=deposits, transactions=transactions)

@app.route('/account/<int:account_id>/deposit', methods=['GET', 'POST'])
@login_required
def deposit_money(account_id):
    account = Account.query.get_or_404(account_id)
    
    if account.user_id != current_user.id and not current_user.is_admin:
        flash('Bu hisobga kirishga ruxsatingiz yo\'q!')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        
        try:
            amount_decimal = decimal.Decimal(amount)
            if amount_decimal <= 0:
                flash('Miqdor musbat bo\'lishi kerak')
                return redirect(url_for('deposit_money', account_id=account_id))
                
            account.deposit_money(amount_decimal)
            
            transaction = Transaction(
                account_id=account_id,
                amount=amount_decimal,
                transaction_type='deposit',
                description='Hisobga pul qo\'shildi'
            )
            db.session.add(transaction)
            db.session.commit()
            
            flash(f'{amount} so\'m hisobingizga qo\'shildi!')
            return redirect(url_for('account_details', account_id=account_id))
            
        except decimal.InvalidOperation:
            flash('Noto\'g\'ri miqdor kiritildi')
            
    return render_template('deposit_money.html', account=account)

@app.route('/account/<int:account_id>/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw_money(account_id):
    account = Account.query.get_or_404(account_id)
    
    if account.user_id != current_user.id and not current_user.is_admin:
        flash('Bu hisobga kirishga ruxsatingiz yo\'q!')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        
        try:
            amount_decimal = decimal.Decimal(amount)
            if amount_decimal <= 0:
                flash('Miqdor musbat bo\'lishi kerak')
                return redirect(url_for('withdraw_money', account_id=account_id))
                
            if account.withdraw_money(amount_decimal):
                transaction = Transaction(
                    account_id=account_id,
                    amount=amount_decimal,
                    transaction_type='withdrawal',
                    description='Hisobdan pul yechib olindi'
                )
                db.session.add(transaction)
                db.session.commit()
                
                flash(f'{amount} so\'m hisobingizdan yechildi!')
            else:
                flash('Hisobda yetarli mablag\' mavjud emas!')
                
            return redirect(url_for('account_details', account_id=account_id))
            
        except decimal.InvalidOperation:
            flash('Noto\'g\'ri miqdor kiritildi')
            
    return render_template('withdraw_money.html', account=account)

@app.route('/account/<int:account_id>/create_deposit', methods=['GET', 'POST'])
@login_required
def create_deposit(account_id):
    account = Account.query.get_or_404(account_id)
    
    if account.user_id != current_user.id and not current_user.is_admin:
        flash('Bu hisobga kirishga ruxsatingiz yo\'q!')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        interest_rate = request.form.get('interest_rate')
        term_months = int(request.form.get('term_months'))
        
        try:
            amount_decimal = decimal.Decimal(amount)
            interest_decimal = decimal.Decimal(interest_rate)
            
            if amount_decimal <= 0 or interest_decimal <= 0:
                flash('Miqdor va foiz stavkasi musbat bo\'lishi kerak')
                return redirect(url_for('create_deposit', account_id=account_id))
                
            if account.balance < amount_decimal:
                flash('Hisobda yetarli mablag\' mavjud emas!')
                return redirect(url_for('create_deposit', account_id=account_id))
            
            # Hisobdan mablag'ni chiqarish
            account.withdraw_money(amount_decimal)
            
            # Omonatni yaratish
            end_date = datetime.utcnow() + timedelta(days=30 * term_months)
            deposit = Deposit(
                amount=amount_decimal,
                interest_rate=interest_decimal,
                end_date=end_date,
                account_id=account_id
            )
            
            db.session.add(deposit)
            
            transaction = Transaction(
                account_id=account_id,
                amount=amount_decimal,
                transaction_type='deposit_creation',
                description=f'Omonat yaratildi, muddat: {term_months} oy, foiz: {interest_rate}%'
            )
            db.session.add(transaction)
            db.session.commit()
            
            flash(f'Omonat muvaffaqiyatli yaratildi!')
            return redirect(url_for('account_details', account_id=account_id))
            
        except (decimal.InvalidOperation, ValueError):
            flash('Noto\'g\'ri ma\'lumotlar kiritildi')
            
    return render_template('create_deposit.html', account=account)

@app.route('/deposit/<int:deposit_id>/close', methods=['POST'])
@login_required
def close_deposit(deposit_id):
    deposit = Deposit.query.get_or_404(deposit_id)
    account = Account.query.get_or_404(deposit.account_id)
    
    if account.user_id != current_user.id and not current_user.is_admin:
        flash('Bu amaliyotni bajarishga ruxsatingiz yo\'q!')
        return redirect(url_for('dashboard'))
    
    interest = deposit.close_deposit()
    total_amount = float(deposit.amount) + interest
    
    # Asosiy summani va foizlarni hisobga qaytarish
    account.deposit_money(total_amount)
    
    transaction = Transaction(
        account_id=account.id,
        amount=total_amount,
        transaction_type='deposit_closure',
        description=f'Omonat yopildi, foiz daromadi: {interest}'
    )
    db.session.add(transaction)
    db.session.commit()
    
    flash(f'Omonat muvaffaqiyatli yopildi, hisobingizga {total_amount} so\'m qaytarildi (foiz: {interest} so\'m)')
    return redirect(url_for('account_details', account_id=account.id))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Adminlik huquqlari talab qilinadi')
        return redirect(url_for('dashboard'))
        
    users = User.query.all()
    accounts = Account.query.all()
    deposits = Deposit.query.all()
    
    return render_template('admin_dashboard.html', users=users, accounts=accounts, deposits=deposits)

@app.route('/admin/user/<int:user_id>')
@login_required
def admin_user_details(user_id):
    if not current_user.is_admin:
        flash('Adminlik huquqlari talab qilinadi')
        return redirect(url_for('dashboard'))
        
    user = User.query.get_or_404(user_id)
    return render_template('admin_user_details.html', user=user)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
