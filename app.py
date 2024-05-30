from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
from models import db, User, Entry

app = Flask(__name__)
app.secret_key = b'\xf2B\x9c\x84\x91x\x0fq\xe7\xbd\x18\xe5\x1b\x13\x13P\x80so&\xc8\xd4\x1bi'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configurações do banco de dados
database_url = 'postgres://ufs9evrb41pi2m:p6a1b5faa8d58943e6d3fd9f03b8aecfa58cf07c6ffeb8b1dc316f56ef8e8e230@ceqbglof0h8enj.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d2vu17d0p14l4e'

if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
            flash('An error occurred during registration. Please try again.')
    
    return render_template('register.html')

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
    
    return render_template('change_password.html')

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
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agenda', methods=['GET', 'POST'])
@login_required
def agenda():
    selected_month = request.args.get('month')
    selected_year = request.args.get('year')

    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']
        completed = request.form.get('completed') == 'on'
        new_event = Entry(date=date, description=description, completed=completed, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()

    years_query = (
        db.session.query(func.date_part('year', Entry.date).cast(db.Integer))
        .filter(Entry.user_id == current_user.id)
        .distinct()
        .order_by(func.date_part('year', Entry.date).cast(db.Integer).desc())
        .all()
    )
    years = [year[0] for year in years_query]

    events_query = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.date).all()

    grouped_events = {}
    for entry in events_query:
        date_key = entry.date.strftime('%Y-%m-%d')
        if date_key not in grouped_events:
            grouped_events[date_key] = []
        grouped_events[date_key].append(entry)

    return render_template('agenda.html', grouped_events=grouped_events, years=years)

@app.route('/mark_task_completed/<int:entry_id>', methods=['POST'])
@login_required
def mark_task_completed(entry_id):
    entry = Entry.query.get(entry_id)
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
    event = db.session.get(Entry, event_id)
    if event and event.user_id == current_user.id:
        event.description = request.form['new_description']
        db.session.commit()
    return redirect(url_for('agenda'))


@app.route('/admin')
@login_required  # Certifique-se de que esta rota exige autenticação
def admin():
    if not current_user.admin:
        return redirect(url_for('index'))
    
    # Obtenha todos os usuários e entradas do banco de dados
    users = User.query.all()
    entries = Entry.query.all()

    # Renderize a página admin.html e passe os dados para ela
    return render_template('admin.html', users=users, entries=entries)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
