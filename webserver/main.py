
import os
from dotenv import load_dotenv

import socket
from flask import Flask, jsonify, current_app
from flask_mysqldb import MySQL

load_dotenv()

app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))
if os.getenv('MYSQL_PASSWORD_FILE') is not None:
    with open(os.getenv('MYSQL_PASSWORD_FILE'), "r") as password_file:
        app.config['MYSQL_PASSWORD'] = password_file.read()
else:
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')

app.config['IS_SERVER_HEALTHY'] = True

mysql = MySQL(app)

local_hostname = socket.gethostname()


@app.route('/make-unhealthy', methods=['GET'])
def make_unhealthy():
    current_app.config['IS_SERVER_HEALTHY'] = False
    return 'Server is now unhealthy'


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'ok': current_app.config['IS_SERVER_HEALTHY']
    }), (200 if current_app.config['IS_SERVER_HEALTHY'] else 500)


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
