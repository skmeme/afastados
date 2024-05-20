from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Altere para uma chave secreta real

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Função para criar a conexão com o banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criação das tabelas 'users' e 'agenda' no banco de dados SQLite
def create_tables():
    conn = get_db_connection()
    try:
        conn.execute('DROP TABLE IF EXISTS users')  # Adicionando para recriar a tabela
        conn.execute('DROP TABLE IF EXISTS agenda')  # Adicionando para recriar a tabela
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            password_hash TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS agenda (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT NOT NULL,
                            description TEXT NOT NULL,
                            user_id INTEGER,
                            FOREIGN KEY (user_id) REFERENCES users (id))''')
        conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        conn.close()

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return User(id=user['id'], username=user['username'], password_hash=user['password_hash'])
    except Exception as e:
        print(f"Error loading user: {e}")
    finally:
        conn.close()
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            conn.commit()
            flash('Registered successfully. Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error registering user: {e}")
            flash('An error occurred during registration. Please try again.')
        finally:
            conn.close()
    return render_template('register.html')

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
                login_user(User(id=user['id'], username=user['username'], password_hash=user['password_hash']))
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
    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']

        # Converter a data de dd-mm-yyyy para yyyy-mm-dd
        day, month, year = date.split('-')
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

    return render_template('agenda.html', agenda_data=agenda_data)

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    if request.method == 'POST':
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

        return redirect(url_for('agenda'))

    # Obter os dados do SQLite para a entrada específica
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM agenda WHERE id = ? AND user_id = ?', (entry_id, current_user.id))
        entry = cursor.fetchone()
    except Exception as e:
        print(f"Error fetching agenda entry: {e}")
        entry = None
    finally:
        conn.close()

    return render_template('edit.html', entry=entry)

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

    return redirect(url_for('agenda'))

if __name__ == '__main__':
    app.run(debug=True)