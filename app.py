from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
from models import db, User, Entry
from sqlalchemy.orm import Session
import calendar
from config import Config
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

database_url = os.getenv('DATABASE_URL')

if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    raise ValueError("DATABASE_URL não foi encontrado no .env")

db.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        
        if existing_user:
            flash('Esse usuário ou e-mail já está cadastrado. Por favor escolha outro.')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password_hash=password_hash)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Cadastro realizado com sucesso.')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error registering user: {e}")
            db.session.rollback()
            flash('Ocorreu um erro ao tentar cadastrar-se. Tente novamente.')


    ano_atual = datetime.now().year

    return render_template('register.html', current_year=ano_atual)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        
        if check_password_hash(current_user.password_hash, old_password):
            new_password_hash = generate_password_hash(new_password)
            current_user.password_hash = new_password_hash
            db.session.commit()
            flash('Senha alterada com sucesso!')
        else:
            flash('Senha antiga incorreta.')
    
    ano_atual = datetime.now().year

    return render_template('change_password.html', current_year=ano_atual)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('agenda'))
        else:
            flash('Invalid username or password')

    

    ano_atual = datetime.now().year
    return render_template('login.html', current_year=ano_atual)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():

    ano_atual = datetime.now().year

    return render_template('index.html', current_year=ano_atual)


@app.route('/agenda', methods=['GET', 'POST'])
@login_required
def agenda():
    
    selected_month = request.args.get('month')
    selected_year = request.args.get('year')
    selected_day = request.args.get('day')
    page = request.args.get('page', 1, type=int)  

   
    per_page = 25

    grouped_events = {}  

    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']

        try:
            new_event = Entry(date=date, description=description, user_id=current_user.id)
            db.session.add(new_event)
            db.session.commit()
        except Exception as e:
            print(f"Error inserting agenda entry: {e}")
            db.session.rollback()

   
    years = []
    try:
        years_query = (
            db.session.query(func.date_part('year', Entry.date).cast(db.Integer))
            .filter(Entry.user_id == current_user.id)
            .distinct()
            .order_by(func.date_part('year', Entry.date).cast(db.Integer).desc())
            .all()
        )
        years = [year[0] for year in years_query]
    except Exception as e:
        print(f"Error fetching years: {e}")

    
    try:
        events_query = Entry.query.filter(Entry.user_id == current_user.id)
        
        if not selected_month and not selected_year and not selected_day:
            events_query = events_query.filter(Entry.completed == False)
        if selected_month:
            events_query = events_query.filter(func.date_part('month', Entry.date) == int(selected_month))
        if selected_year:
            events_query = events_query.filter(func.date_part('year', Entry.date) == int(selected_year))
        if selected_day:
            events_query = events_query.filter(func.date_part('day', Entry.date) == int(selected_day))
        events_query = events_query.order_by(Entry.date).paginate(page=page, per_page=per_page)

        for entry in events_query.items:  
            entry_date = entry.date.strftime('%Y-%m-%d')
            if entry_date not in grouped_events:
                grouped_events[entry_date] = []
            grouped_events[entry_date].append({'id': entry.id, 'date': entry_date, 'description': entry.description, 'completed': entry.completed})
    except Exception as e:
        print(f"Error fetching agenda data: {e}")

    months = []
    for month in range(1, 13):
        month_name = calendar.month_name[month].capitalize()
        months.append({'month': str(month).zfill(2), 'month_name': month_name})

        current_year = datetime.now().year

    return render_template('agenda.html', months=months, years=years, selected_month=selected_month, selected_year=selected_year, selected_day=selected_day, grouped_events=grouped_events, events_query=events_query, current_year=current_year)



@app.route('/mark_task_completed/<int:entry_id>', methods=['POST'])
@login_required
def mark_task_completed(entry_id):
    entry = db.session.get(Entry, entry_id)
    if entry and entry.user_id == current_user.id:
        entry.completed = True  
        db.session.commit()
    return redirect(url_for('agenda'))

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = Entry.query.get(entry_id)
    if entry and entry.user_id == current_user.id:
        db.session.delete(entry)
        db.session.commit()
    return redirect(url_for('agenda'))

@app.route('/edit_event/<int:event_id>', methods=['POST'])
@login_required
def edit_event(event_id):
    print("Received request to edit event:", request.form)
    event = Entry.query.get(event_id)
    if event and event.user_id == current_user.id:
        event.description = request.form.get('new_description')
        event.completed = 'completed' in request.form
        db.session.commit()
        return redirect(url_for('agenda', page=request.args.get('page', 1)))
    return 'Event not found', 404


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'delete_user' in request.form:
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
        elif 'delete_entry' in request.form:
            entry_id = request.form['entry_id']
            entry = Entry.query.get(entry_id)
            if entry:
                db.session.delete(entry)
                db.session.commit()

    users = User.query.all()
    entries = Entry.query.all()
    return render_template('admin.html', users=users, entries=entries)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
