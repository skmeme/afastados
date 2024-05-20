from flask import Flask, render_template, request, redirect, url_for
import sqlite3

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

@app.route('/agenda', methods=['GET', 'POST'])
def agenda():
    if request.method == 'POST':
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        description = request.form['description']

        # Formatar a data
        date = f'{year}-{month.zfill(2)}-{day.zfill(2)}'

        # Armazenar no SQLite
        conn = get_db_connection()
        conn.execute('INSERT INTO agenda (date, description) VALUES (?, ?)', (date, description))
        conn.commit()
        conn.close()

    # Obter os dados do SQLite
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM agenda ORDER BY date DESC')
    agenda_data = cursor.fetchall()
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