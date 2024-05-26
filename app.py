from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import calendar
import locale
import os
from datetime import datetime, timedelta
from itertools import groupby

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')

app = Flask(__name__)
app.secret_key = b'\xf2B\x9c\x84\x91x\x0fq\xe7\xbd\x18\xe5\x1b\x13\x13P\x80so&\xc8\xd4\x1bi'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS agenda (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,  -- Alteração para DATE
                        description TEXT NOT NULL,
                        completed INTEGER DEFAULT 0,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (id))''')
        conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        conn.close()

class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return User(id=user['id'], username=user['username'], email=user['email'], password_hash=user['password_hash'])
    except Exception as e:
        print(f"Error loading user: {e}")
    finally:
        conn.close()
    return None

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
        
        conn = get_db_connection()
        try:
            cursor = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                login_user(User(id=user['id'], username=user['username'], email=user['email'], password_hash=user['password_hash']))
                return redirect(url_for('agenda'))
            else:
                flash('Invalid username or password')
        except Exception as e:
            print(f"Error logging in user: {e}")
        finally:
            conn.close()
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

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO agenda (date, description, user_id) VALUES (?, ?, ?)', (date, description, current_user.id))
            conn.commit()
        except Exception as e:
            print(f"Error inserting agenda entry: {e}")
        finally:
            conn.close()

    # Buscar anos únicos da base de dados
    years = []
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT DISTINCT strftime("%Y", date) as year FROM agenda WHERE user_id = ? ORDER BY year DESC', (current_user.id,))
        years_data = cursor.fetchall()
        years = [year[0] for year in years_data]  # Transforma a lista de tuplas em uma lista de anos únicos
    except Exception as e:
        print(f"Error fetching years: {e}")
    finally:
        conn.close()

    # Buscar eventos agrupados por data
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if selected_month and selected_year:
            query = 'SELECT id, date, description FROM agenda WHERE user_id = ? AND strftime("%m", date) = ? AND strftime("%Y", date) = ? ORDER BY date'
            cursor.execute(query, (current_user.id, selected_month, selected_year))
        elif selected_month:
            query = 'SELECT id, date, description FROM agenda WHERE user_id = ? AND strftime("%m", date) = ? ORDER BY date'
            cursor.execute(query, (current_user.id, selected_month))
        elif selected_year:
            query = 'SELECT id, date, description FROM agenda WHERE user_id = ? AND strftime("%Y", date) = ? ORDER BY date'
            cursor.execute(query, (current_user.id, selected_year))
        else:
            query = 'SELECT id, date, description FROM agenda WHERE user_id = ? ORDER BY date'
            cursor.execute(query, (current_user.id,))
        agenda_data = cursor.fetchall()
        for entry in agenda_data:
            entry_date = entry[1]
            if not isinstance(entry_date, str):
                entry_date = entry_date.strftime('%d-%m-%Y')
            if entry_date not in grouped_events:
                grouped_events[entry_date] = []
            grouped_events[entry_date].append({'id': entry[0], 'date': entry_date, 'description': entry[2]})
    except Exception as e:
        print(f"Error fetching agenda data: {e}")
        agenda_data = []
    finally:
        conn.close()

    months = []
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT DISTINCT strftime("%m", date) as month FROM agenda WHERE user_id = ? ORDER BY month', (current_user.id,))
        months_data = cursor.fetchall()
        for month_data in months_data:
            month_name = calendar.month_name[int(month_data[0])].capitalize()
            months.append({'month': month_data[0], 'month_name': month_name})
    except Exception as e:
        print(f"Error fetching months: {e}")
    finally:
        conn.close()

    return render_template('agenda.html', agenda_data=agenda_data, months=months, years=years, selected_month=selected_month, selected_year=selected_year, grouped_events=grouped_events)



def group_by_weeks(agenda_data):
    if not agenda_data:
        return []

    agenda_data.sort(key=lambda x: datetime.strptime(x['date'], '%d-%m-%Y'))
    grouped_data = []
    current_week = []
    start_of_week = datetime.strptime(agenda_data[0]['date'], '%d-%m-%Y')
    end_of_week = start_of_week + timedelta(days=6)

    for entry in agenda_data:
        entry_date = entry.get('date')
        if entry_date:
            if isinstance(entry_date, str):  # Garante que a data seja uma string para comparação
                entry_date = datetime.strptime(entry_date, '%d-%m-%Y')
            entry['date'] = entry_date.strftime('%Y-%m-%d')
            if entry_date > end_of_week:
                grouped_data.append({'week_start': start_of_week, 'week_end': end_of_week, 'entries': current_week})
                current_week = []
                start_of_week = entry_date - timedelta(days=entry_date.weekday())
                end_of_week = start_of_week + timedelta(days=6)
            current_week.append(entry)

    if current_week:
        grouped_data.append({'week_start': start_of_week, 'week_end': end_of_week, 'entries': current_week})

    return grouped_data

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if request.method == 'POST':
        new_description = request.form['new_description']
        
        conn = get_db_connection()
        try:
            conn.execute('UPDATE agenda SET description = ? WHERE id = ?', (new_description, event_id))
            conn.commit()
            flash('Evento editado com sucesso!')
            return redirect(url_for('agenda'))
        except Exception as e:
            print(f"Error editing event: {e}")
            flash('Erro ao editar o evento. Por favor, tente novamente.')
        finally:
            conn.close()
    return redirect(url_for('agenda'))  # Redirecionar para a página de agenda em caso de método GET

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    if current_user.username != 'teste':
        flash('Acesso negado.')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        users_cursor = conn.execute('SELECT id, username FROM users')
        users = users_cursor.fetchall()

        agenda_cursor = conn.execute('SELECT * FROM agenda')
        agenda = agenda_cursor.fetchall()
    except Exception as e:
        print(f"Error fetching admin data: {e}")
        users = []
        agenda = []
    finally:
        conn.close()

    return render_template('admin.html', users=users, agenda=agenda)

@app.route('/delete/<int:entry_id>')
@login_required
def delete_entry(entry_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM agenda WHERE id = ? AND user_id = ?', (entry_id, current_user.id))
        conn.commit()
    except Exception as e:
        print(f"Error deleting agenda entry: {e}")
    finally:
        conn.close()

    flash('Evento excluído com sucesso!')
    return redirect(url_for('agenda'))

@app.route('/mark_complete/<int:entry_id>', methods=['GET'])
@login_required
def mark_complete(entry_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE agenda SET completed = 1 WHERE id = ? AND user_id = ?', (entry_id, current_user.id))
        conn.commit()
        return jsonify({'message': 'Tarefa marcada como concluída.'})
    except Exception as e:
        print(f"Error marking task as complete: {e}")
        return jsonify({'message': 'Erro ao marcar a tarefa como concluída.'}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)