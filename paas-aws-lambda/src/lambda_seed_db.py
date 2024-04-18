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
    print("Lambda 'seed db' is called")
    try:
        sql_commands = [
            """CREATE TABLE IF NOT EXISTS accounts (
                id INT PRIMARY KEY,
                name VARCHAR(40),
                balance INT
            )""",
            """INSERT IGNORE INTO accounts
                (id, name, balance)
            VALUES
                (1, 'Mario', 100)""",
            """INSERT IGNORE INTO accounts
                (id, name, balance)
            VALUES
                (2, 'Luigi', 200)"""
        ]

        for sql_command in sql_commands:
            try:
                cursor = connection.cursor()
                cursor.execute(sql_command)
            finally:
                if connection.is_connected():
                    cursor.close()
    finally:
        if connection.is_connected():
            connection.close()