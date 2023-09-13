from flask import Flask, request, jsonify
import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

url = os.getenv("DATABASE_URL")
connection = conn = psycopg2.connect(
    "host='localhost' "
    "port='5432' "
    "dbname='cogip' "
    "user='postgres' "
    "password='Pianos123.'"
)

CREATE_COMPANY_TABLE = (
    "CREATE TABLE IF NOT EXISTS company ("
    "id SERIAL PRIMARY KEY,"
    "name VARCHAR(255) NOT NULL,"
    "country VARCHAR(255) NOT NULL,"
    "vat VARCHAR(255) NOT NULL,"
    "type VARCHAR(255) NOT NULL"
    ");"
)

INSERT_COMPANIES = (
    "INSERT INTO company "
    "(name, country, vat, type) "
    "VALUES (%s, %s, %s, %s) RETURNING id;"
)

CREATE_USER_TABLE = (
    "CREATE TABLE IF NOT EXISTS user ("
    "id SERIAL PRIMARY KEY,"
    "username VARCHAR(255) NOT NULL,"
    "password VARCHAR(255) NOT NULL,"
    "role VARCHAR(255) NOT NULL CHECK ("
    "role IN ('admin', 'accountant', 'intern')"
    ")"
    ");"
)   

INSERT_USERS = (
    "INSERT INTO user "
    "(username, password, role) "
    "VALUES (%s, %s, %s) RETURNING id;"
)

@app.route('/api/company', methods=['POST'])
def create_company():
    data = request.get_json()
    name = data["name"]
    country = data["country"]
    vat = data["vat"]
    type = data["type"]
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_COMPANY_TABLE)
            cursor.execute(INSERT_COMPANIES, (name, country, vat, type))
            company_id = cursor.fetchone()[0]
    return jsonify({"id": company_id, "message": f"Company {name} created"}), 201

@app.route('/api/user', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    role = data["role"]
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_USER_TABLE)
            cursor.execute(INSERT_USERS, (username, password, role))
            user_id = cursor.fetchone()[0]
    return jsonify({"id": user_id, "message": f"User {username} created"}), 201

if __name__ == '__main__':
    app.run(debug=True)
