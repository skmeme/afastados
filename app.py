from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g 
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import calendar

app = Flask(__name__)
app.secret_key = b'\xf2B\x9c\x84\x91x\x0fq\xe7\xbd\x18\xe5\x1b\x13\x13P\x80so&\xc8\xd4\x1bi'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Configurações do banco de dados diretamente no código
database_url = 'postgres://ufs9evrb41pi2m:p6a1b5faa8d58943e6d3fd9f03b8aecfa58cf07c6ffeb8b1dc316f56ef8e8e230@ceqbglof0h8enj.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d2vu17d0p14l4e'

# Ajustar a URL se necessário
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

db = SQLAlchemy(app)

def get_db_connection():
    return db

def create_tables():
    with app.app_context():
        db.create_all()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    agenda_items = db.relationship('Agenda', backref='user', lazy=True)

class Agenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)  # Alteração para DATE
    description = db.Column(db.Text, nullable=False)
    completed = db.Column(db.Boolean, default=False)  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)', (username, email, password_hash))
            conn.commit()
            flash('Registered successfully. Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error registering user: {e}")
            flash('An error occurred during registration. Please try again.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        
        if check_password_hash(current_user.password_hash, old_password):
            new_password_hash = generate_password_hash(new_password)
            
            conn = get_db_connection()
            try:
                conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, current_user.id))
                conn.commit()
                flash('Senha alterada com sucesso!')
            except Exception as e:
                print(f"Error changing password: {e}")
                flash('Erro ao alterar a senha. Por favor, tente novamente.')
            finally:
                conn.close()
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

create_tables()

@app.template_filter('nl2br')
def nl2br(value):
    return value.replace('\n', '<br>\n')

# Rota para deletar um evento da agenda
@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    entry = Agenda.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('agenda'))

# Rota para editar um evento da agenda
@app.route('/edit_event/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    # Obter o evento da agenda pelo ID
    event = Agenda.query.get_or_404(event_id)
    
    # Atualizar os detalhes do evento com base nos dados do formulário
    event.description = request.form['new_description']
    
    # Commit da transação
    db.session.commit()
    
    return redirect(url_for('agenda'))

from datetime import datetime
import calendar

@app.route('/agenda', methods=['GET', 'POST'])
@login_required
def agenda():
    # Obter os parâmetros de filtro da URL
    selected_month = request.args.get('month')
    selected_year = request.args.get('year')

    grouped_events = {}  # Inicializando grouped_events

    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']
        completed = request.form.get('completed') == 'on'  # Verifica se a checkbox foi marcada

        new_event = Agenda(date=date, description=description, completed=completed, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()

    # Buscar anos únicos da base de dados
    years_query = (
        db.session.query(func.date_part('year', Agenda.date).cast(db.Integer))
        .filter(Agenda.user_id == current_user.id)
        .distinct()
        .order_by(func.date_part('year', Agenda.date).cast(db.Integer).desc())
        .all()
    )
    years = [year[0] for year in years_query]

    # Buscar eventos agrupados por data
    agenda_data = []
    if selected_month and selected_year:
        agenda_data = Agenda.query.filter(func.date_part('month', Agenda.date) == selected_month, func.date_part('year', Agenda.date) == selected_year, Agenda.user_id == current_user.id).order_by(Agenda.date).all()
    elif selected_month:
        agenda_data = Agenda.query.filter(func.date_part('month', Agenda.date) == selected_month, Agenda.user_id == current_user.id).order_by(Agenda.date).all()
    elif selected_year:
        agenda_data = Agenda.query.filter(func.date_part('year', Agenda.date) == selected_year, Agenda.user_id == current_user.id).order_by(Agenda.date).all()
    else:
        agenda_data = Agenda.query.filter_by(user_id=current_user.id).order_by(Agenda.date).all()

    for entry in agenda_data:
        entry_date = entry.date.strftime('%d-%m-%Y')
        if entry_date not in grouped_events:
            grouped_events[entry_date] = []
        grouped_events[entry_date].append({'id': entry.id, 'date': entry_date, 'description': entry.description})

    months = [{'month': str(i), 'month_name': datetime.strptime(str(i), "%m").strftime("%B")} for i in range(1, 13)]

    return render_template('agenda.html', agenda_data=agenda_data, months=months, years=years, selected_month=selected_month, selected_year=selected_year, grouped_events=grouped_events)


@app.route('/mark_task_completed/<int:entry_id>', methods=['POST'])
@login_required
def mark_task_completed(entry_id):
    entry = Agenda.query.get(entry_id)
    if entry:
        entry.completed = True
        db.session.commit()
        flash('Tarefa concluída com sucesso!', 'success')
    return redirect(url_for('agenda'))


@app.context_processor
def inject_user():
    return dict(current_user=current_user)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
