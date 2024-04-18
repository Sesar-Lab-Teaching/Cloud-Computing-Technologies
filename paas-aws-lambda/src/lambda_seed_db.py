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

    cursor = connection.cursor()
    try:
        for sql_command in sql_commands:
            cursor.execute(sql_command)
    finally:
        connection.commit()
        if connection.is_connected():
            cursor.close()