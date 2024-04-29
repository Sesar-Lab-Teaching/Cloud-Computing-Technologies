
import os
import platform

from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)

with open(os.getenv('MYSQL_PASSWORD_FILE'), "r") as password_file:
    app.config['MYSQL_PASSWORD'] = password_file.read()

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))

mysql = MySQL(app)

@app.route('/')
def get_data():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM accounts''')
    data = cur.fetchall()
    cur.close()

    html = f'''
    <html>
        <head>
            <style>
            table, th, td {{
                border: 1px solid black;
                border-collapse: collapse;
            }}
            </style>
        </head>
        <body>
        <p>Hostname: {platform.node()}</p>
        <table>
            <tr>
                <th>Id</th>
                <th>Name</th>
                <th>Balance</th>
            </tr>
    '''
    
    for d in data:
       html += f'''
    <tr>
        <td>{d[0]}</td>
        <td>{d[1]}</td>
        <td>{d[2]}</td>
    </tr>
    '''
    html += '</table></body></html>'
    return html