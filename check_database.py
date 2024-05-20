import sqlite3

def check_users_table():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("PRAGMA table_info(users);")
    columns = cursor.fetchall()
    print(columns)
    conn.close()

check_users_table()