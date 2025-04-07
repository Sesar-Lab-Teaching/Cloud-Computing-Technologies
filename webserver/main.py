
import os
from dotenv import load_dotenv

import socket
from flask import Flask
from flask_mysqldb import MySQL

load_dotenv()

app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))

mysql = MySQL(app)

local_hostname = socket.gethostname()

@app.route('/')
def get_data():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM accounts''')
    data = cur.fetchall()
    cur.close()

    html = '''
    <html>
        <head>
            <style>
            table, th, td {
                border: 1px solid black;
                border-collapse: collapse;
            }
            </style>
        </head>
        <body>
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
    html += f'''
            </table>
            <hr />
            <p>Hostname: {local_hostname}</p>
        </body>
    </html>'''
    return html
