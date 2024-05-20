from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Função para criar a conexão com o banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criação da tabela 'agenda' no banco de dados SQLite
def create_agenda_table():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, description TEXT NOT NULL)')
    conn.commit()
    conn.close()

# Criar a tabela de agenda ao iniciar o aplicativo
create_agenda_table()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agenda', methods=['GET', 'POST'])
def agenda():
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        description = request.form['description']

        # Formatar a data para DD/MM/YYYY
        date_str = f'{day}/{month}/{year}'
        date = datetime.strptime(date_str, '%d/%m/%Y')

        # Armazenar no SQLite
        conn = get_db_connection()
        conn.execute('INSERT INTO agenda (date, description) VALUES (?, ?)', (date, description))
        conn.commit()
        conn.close()

        return redirect(url_for('agenda'))

    # Obter os dados do SQLite e formatar a data para exibição
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM agenda ORDER BY date DESC')
    agenda_data = cursor.fetchall()

    # Formatando a data para exibição no formato DD/MM/YYYY
    for item in agenda_data:
        item['date'] = datetime.strptime(item['date'], '%Y-%m-%d').strftime('%d/%m/%Y')

    conn.close()

    return render_template('agenda.html', agenda_data=agenda_data)

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if request.method == 'POST':
        new_description = request.form['new_description']

        # Atualizar a descrição no SQLite
        conn = get_db_connection()
        conn.execute('UPDATE agenda SET description = ? WHERE id = ?', (new_description, entry_id))
        conn.commit()
        conn.close()

        return redirect(url_for('agenda'))

    # Obter os dados do SQLite para a entrada específica
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM agenda WHERE id = ?', (entry_id,))
    entry = cursor.fetchone()
    conn.close()

    return render_template('edit.html', entry=entry)

@app.route('/delete/<int:entry_id>')
def delete_entry(entry_id):
    # Excluir a entrada do SQLite
    conn = get_db_connection()
    conn.execute('DELETE FROM agenda WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('agenda'))

if __name__ == '__main__':
    app.run(debug=True)