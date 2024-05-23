from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import calendar
import locale
import os

app = Flask(__name__)
app.secret_key = b'\xf2B\x9c\x84\x91x\x0fq\xe7\xbd\x18\xe5\x1b\x13\x13P\x80so&\xc8\xd4\x1bi'  # Altere para uma chave secreta real

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configurar a localização para inglês (EUA)
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# Função para criar a conexão com o banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criação das tabelas 'users' e 'agenda' no banco de dados SQLite
def create_tables():
    conn = get_db_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            email TEXT,
                            password_hash TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS agenda (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT NOT NULL,
                            description TEXT NOT NULL,
                            completed INTEGER DEFAULT 0,  -- Adicionando a coluna "completed"
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
        
        # Verificar se a senha antiga está correta
        if check_password_hash(current_user.password_hash, old_password):
            # Gerar o hash da nova senha
            new_password_hash = generate_password_hash(new_password)
            
            # Atualizar a senha no banco de dados
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

# Criar as tabelas ao iniciar o aplicativo
create_tables()

@app.route('/agenda', methods=['GET', 'POST'])
@login_required
def agenda():
    selected_month = request.args.get('month')
    selected_year = request.args.get('year')

    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']

        # Formatar a data para yyyy-mm-dd
        year, month, day = date.split('-')
        formatted_date = f'{year}-{month}-{day}'

        # Armazenar no SQLite
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO agenda (date, description, user_id) VALUES (?, ?, ?)', (formatted_date, description, current_user.id))
            conn.commit()
        except Exception as e:
            print(f"Error inserting agenda entry: {e}")
        finally:
            conn.close()

    # Obter os dados do SQLite
    conn = get_db_connection()
    try:
        if selected_month and selected_year:
            cursor = conn.execute('SELECT * FROM agenda WHERE user_id = ? AND strftime("%m", date) = ? AND strftime("%Y", date) = ? ORDER BY date DESC', (current_user.id, selected_month, selected_year))
        elif selected_month:
            cursor = conn.execute('SELECT * FROM agenda WHERE user_id = ? AND strftime("%m", date) = ? ORDER BY date DESC', (current_user.id, selected_month))
        elif selected_year:
            cursor = conn.execute('SELECT * FROM agenda WHERE user_id = ? AND strftime("%Y", date) = ? ORDER BY date DESC', (current_user.id, selected_year))
        else:
            cursor = conn.execute('SELECT * FROM agenda WHERE user_id = ? ORDER BY date DESC', (current_user.id,))
        agenda_data = cursor.fetchall()

        # Converter as datas para o formato dd-mm-yyyy para exibição
        agenda_data = [dict(row) for row in agenda_data]
        for entry in agenda_data:
            year, month, day = entry['date'].split('-')
            entry['date'] = f'{day}-{month}-{year}'
    except Exception as e:
        print(f"Error fetching agenda data: {e}")
        agenda_data = []
    finally:
        conn.close()

    # Obter lista de meses e anos disponíveis
    months = []
    years = []
    try:
        conn = get_db_connection()  # Nova conexão
        cursor = conn.execute('SELECT DISTINCT strftime("%m", date) as month, strftime("%Y", date) as year FROM agenda WHERE user_id = ? ORDER BY year DESC, month DESC', (current_user.id,))
        months_data = cursor.fetchall()
        seen_months = set()
        for month_data in months_data:
            if month_data['month'] not in seen_months:
                month_name = calendar.month_name[int(month_data['month'])].capitalize()
                months.append({'month': month_data['month'], 'month_name': month_name})
                seen_months.add(month_data['month'])
            if month_data['year'] not in years:
                years.append(month_data['year'])
    except Exception as e:
        print(f"Error fetching months: {e}")
    finally:
        conn.close()

    return render_template('agenda.html', agenda_data=agenda_data, months=months, years=years, selected_month=selected_month, selected_year=selected_year)


@app.route('/admin', methods=['GET'])
@login_required
def admin():
    # Verificar se o usuário atual é um administrador
    if current_user.username != 'vigoradmin':
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

@app.route('/edit/<int:entry_id>', methods=['POST'])
@login_required
def edit_entry(entry_id):
    new_description = request.form['new_description']

    # Atualizar a descrição no SQLite
    conn = get_db_connection()
    try:
        conn.execute('UPDATE agenda SET description = ? WHERE id = ? AND user_id = ?', (new_description, entry_id, current_user.id))
        conn.commit()
    except Exception as e:
        print(f"Error updating agenda entry: {e}")
    finally:
        conn.close()

    flash('Evento atualizado com sucesso!')
    return redirect(url_for('agenda'))

@app.route('/delete/<int:entry_id>')
@login_required
def delete_entry(entry_id):
    # Excluir a entrada do SQLite
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

    return redirect(url_for('agenda'))

if __name__ == '__main__':
    app.run(debug=True)