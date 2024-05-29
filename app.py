import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import calendar
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')

app = Flask(__name__)
app.secret_key = b'\xf2B\x9c\x84\x91x\x0fq\xe7\xbd\x18\xe5\x1b\x13\x13P\x80so&\xc8\xd4\x1bi'

# Configurações do banco de dados diretamente no código
database_url = 'postgres://ufs9evrb41pi2m:p6a1b5faa8d58943e6d3fd9f03b8aecfa58cf07c6ffeb8b1dc316f56ef8e8e230@ceqbglof0h8enj.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d2vu17d0p14l4e'

# Ajustar a URL se necessário
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"Database URL: {database_url}")  # Linha de debug

if not app.config['SQLALCHEMY_DATABASE_URI']:
    raise RuntimeError("DATABASE_URL não configurado corretamente")

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)

class Agenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
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

        new_user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        flash('Registered successfully. Please log in.')
        return redirect(url_for('login'))
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
    grouped_events = {}

    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']
        new_event = Agenda(date=date, description=description, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()

    years = [year[0] for year in db.session.query(db.func.strftime("%Y", Agenda.date)).distinct().filter_by(user_id=current_user.id).all()]
    months = [{'month': month[0], 'month_name': calendar.month_name[int(month[0])].capitalize()} for month in db.session.query(db.func.strftime("%m", Agenda.date)).distinct().filter_by(user_id=current_user.id).all()]

    query = Agenda.query.filter_by(user_id=current_user.id)
    if selected_month and selected_year:
        query = query.filter(db.func.strftime("%m", Agenda.date) == selected_month, db.func.strftime("%Y", Agenda.date) == selected_year)
    elif selected_month:
        query = query.filter(db.func.strftime("%m", Agenda.date) == selected_month)
    elif selected_year:
        query = query.filter(db.func.strftime("%Y", Agenda.date) == selected_year)
    agenda_data = query.order_by(Agenda.date).all()

    for entry in agenda_data:
        entry_date = entry.date.strftime('%d-%m-%Y')
        if entry_date not in grouped_events:
            grouped_events[entry_date] = []
        grouped_events[entry_date].append({'id': entry.id, 'date': entry_date, 'description': entry.description})

    return render_template('agenda.html', agenda_data=agenda_data, months=months, years=years, selected_month=selected_month, selected_year=selected_year, grouped_events=grouped_events)

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if request.method == 'POST':
        new_description = request.form['new_description']
        event = Agenda.query.get(event_id)
        if event and event.user_id == current_user.id:
            event.description = new_description
            db.session.commit()
            flash('Evento editado com sucesso!')
        else:
            flash('Erro ao editar o evento. Por favor, tente novamente.')
    return redirect(url_for('agenda'))

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    if current_user.username != 'teste':
        flash('Acesso negado.')
        return redirect(url_for('index'))

    users = User.query.all()
    agenda = Agenda.query.all()
    return render_template('admin.html', users=users, agenda=agenda)

@app.route('/delete/<int:entry_id>')
@login_required
def delete_entry(entry_id):
    event = Agenda.query.get(entry_id)
    if event and event.user_id == current_user.id:
        db.session.delete(event)
        db.session.commit()
        flash('Evento excluído com sucesso!')
    else:
        flash('Erro ao excluir o evento.')
    return redirect(url_for('agenda'))

@app.route('/mark_complete/<int:entry_id>', methods=['GET'])
@login_required
def mark_complete(entry_id):
    event = Agenda.query.get(entry_id)
    if event and event.user_id == current_user.id:
        event.completed = True
        db.session.commit()
        return jsonify({'message': 'Tarefa marcada como concluída.'})
    else:
        return jsonify({'message': 'Erro ao marcar a tarefa como concluída.'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)