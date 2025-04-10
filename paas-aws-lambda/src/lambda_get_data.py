import os
import socket
import mysql.connector
from mysql.connector import errorcode

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DATABASE')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))

def handler(event, context):
    print(f"Lambda {context.function_name} is called")

    local_hostname = socket.gethostname()

    try:
        connection = mysql.connector.connect(
            host = MYSQL_HOST,
            database = MYSQL_DB,
            user = MYSQL_USER,
            password = MYSQL_PASSWORD,
            port = MYSQL_PORT)
        
        query = "SELECT id, name, balance FROM accounts"

        cursor = connection.cursor()
        cursor.execute(query)

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
                        </tr>'''
            
        for (id, name, balance) in cursor:
            html += f'''
                        <tr>
                            <td>{id}</td>
                            <td>{name}</td>
                            <td>{balance}</td>
                        </tr>'''
        html += f'''
                    </table>
                    <hr />
                    <p>Hostname: {local_hostname}</p>
                </body>
            </html>'''
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("User credentials are wrong")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:
        if connection.is_connected():
            cursor.close()
        connection.close()
        return html