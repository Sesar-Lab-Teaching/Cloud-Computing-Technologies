import os
import mysql.connector

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DATABASE')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))

connection = mysql.connector.connect(
    host = MYSQL_HOST,
    database = MYSQL_DB,
    user = MYSQL_USER,
    password = MYSQL_PASSWORD,
    port = MYSQL_PORT)

def handler(event, context):
    print("Lambda 'retrieve accounts' is called")
    try:
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
        html += '</table></body></html>'

        return html
    finally:
        if connection.is_connected():
            cursor.close()