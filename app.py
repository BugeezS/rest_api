from functools import wraps

from flask_cors import CORS
from flask import Flask, request, jsonify, make_response, session, redirect, url_for
import os
import psycopg2
from dotenv import load_dotenv
import jwt
import datetime

from sqlalchemy.orm import Session

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app)

db_host = os.getenv('DATABASE_HOST')
db_port = os.getenv('DATABASE_PORT')
db_name = os.getenv('DATABASE_NAME')
db_user = os.getenv('DATABASE_USER')
db_password = os.getenv('DATABASE_PASSWORD')

connection = psycopg2.connect(
    f"host='{db_host}' "
    f"port='{db_port}' "
    f"dbname='{db_name}' "
    f"user='{db_user}' "
    f"password='{db_password}'"
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
    "CREATE TABLE IF NOT EXISTS users ("
    "id SERIAL PRIMARY KEY,"
    "username VARCHAR(255) NOT NULL,"
    "password VARCHAR(255) NOT NULL,"
    "role VARCHAR(255) NOT NULL CHECK ("
    "role IN ('admin', 'accountant', 'intern')"
    ")"
    ");"
)

INSERT_USERS = (
    "INSERT INTO users"
    "(username, password, role) "
    "VALUES (%s, %s, %s) RETURNING id;"
)
CREATE_CONTACT_TABLE = (
    "CREATE TABLE IF NOT EXISTS contact ("
    "id SERIAL PRIMARY KEY,"
    "firstname VARCHAR(255) NOT NULL,"
    "lastname VARCHAR(255) NOT NULL,"
    "phone VARCHAR(15) NOT NULL,"
    "email VARCHAR(255) NOT NULL,"
    "timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    "contact_company_id INTEGER REFERENCES company (id)"
    ");"
)

INSERT_CONTACTS = (
    "INSERT INTO contact "
    "(firstname, lastname, phone, email) "
    "VALUES (%s, %s, %s, %s) RETURNING id;"
)
CREATE_INVOICE_TABLE = (
    "CREATE TABLE IF NOT EXISTS invoice ("
    "id SERIAL PRIMARY KEY,"
    "timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    "invoice_company_id INTEGER REFERENCES company (id),"
    "invoice_contact_id INTEGER REFERENCES contact (id)"
    ");"
)
INSERT_INVOICES = (
    "INSERT INTO invoice "
    "(number) "
    "VALUES (%s) RETURNING id;"
)

JWT_EXPIRATION_DELTA = datetime.timedelta(minutes=30)


def authenticate_user(username, password):
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT username, role FROM users WHERE username = %s AND password = %s",
                               (username, password))
                user = cursor.fetchone()
                if user:
                    return user
                else:
                    return None
    except psycopg2.Error as e:
        return None


def token_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')

            if not token:
                token = request.args.get('token')

            if not token:
                return jsonify({'message': 'Token is missing'}), 403

            try:
                if token.startswith('Bearer '):
                    token = token.split(' ')[1]

                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = data.get('username')

                user_role = get_user_role(username)

                if user_role in allowed_roles:
                    return f(*args, **kwargs)
                else:
                    return jsonify({'message': 'Access forbidden for this role'}), 403

            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Token has expired'}), 403
            except jwt.InvalidTokenError:
                return jsonify({'message': 'Token is invalid'}), 403

        return decorated

    return decorator

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_role(username):
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
                user_role = cursor.fetchone()
                if user_role:
                    return user_role[0]
                else:
                    return None
    except psycopg2.Error as e:
        return None


@app.route("/api/login", methods=['POST'])
def login():
    data = request.get_json()
    auth_username = data.get('username')
    auth_password = data.get('password')
    user = authenticate_user(auth_username, auth_password)

    if user:
        username, _ = user
        token_payload = {'username': username, 'exp': datetime.datetime.utcnow() + JWT_EXPIRATION_DELTA}
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        session['token'] = token
        return jsonify({'token': token}), 200

    return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.route('/api/company', methods=['POST'])
@token_required(['admin', 'accountant'])
@login_required
def create_company():
    data = request.get_json()
    name = data["name"]
    country = data["country"]
    vat = data["vat"]
    type = data["type"]
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_COMPANY_TABLE)
                cursor.execute(INSERT_COMPANIES, (name, country, vat, type))
                company_id = cursor.fetchone()[0]
        return jsonify({"id": company_id, "message": f"Company {name} created"}), 201
    except psycopg2.Error as e:
        return jsonify({"message": "Failed to create company"}), 500


@app.route('/api/companies', methods=['GET'])
@token_required(['admin', 'accountant', 'intern'])
@login_required
def get_companies():
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name, country, vat, type FROM company")
                companies = cursor.fetchall()
                company_list = []
                for company in companies:
                    company_dict = {
                        'id': company[0],
                        'name': company[1],
                        'country': company[2],
                        'vat': company[3],
                        'type': company[4]
                    }
                    company_list.append(company_dict)

                return jsonify({'companies': company_list}), 200
    except psycopg2.Error as e:
        return jsonify({'message': 'Failed to retrieve companies'}), 500

@app.route('/api/contact', methods=['POST'])
@token_required(['admin', 'accountant', 'intern'])
def create_contact():
    data = request.get_json()
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    phone = data.get('phone')
    email = data.get('email')
    contact_company_id = data.get('contact_company_id')

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO contact (firstname, lastname, phone, email, contact_company_id) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                               (firstname, lastname, phone, email, contact_company_id))
                contact_id = cursor.fetchone()[0]
        return jsonify({"id": contact_id, "message": f"Contact {firstname} {lastname} created"}), 201
    except psycopg2.Error as e:
        return jsonify({"message": "Failed to create contact"}), 500

@app.route('/api/contacts', methods=['GET'])
@token_required(['admin', 'accountant', 'intern'])
def get_contacts():
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, firstname, lastname, phone, email, timestamp, contact_company_id FROM contact")
                contacts = cursor.fetchall()
                contact_list = []
                for contact in contacts:
                    contact_dict = {
                        'id': contact[0],
                        'firstname': contact[1],
                        'lastname': contact[2],
                        'phone': contact[3],
                        'email': contact[4],
                        'timestamp': contact[5],
                        'contact_company_id': contact[6]
                    }
                    contact_list.append(contact_dict)

                return jsonify({'contacts': contact_list}), 200
    except psycopg2.Error as e:
        return jsonify({'message': 'Failed to retrieve contacts'}), 500
@app.route('/api/invoice', methods=['POST'])
@token_required(['admin', 'accountant'])
def create_invoice():
    data = request.get_json()
    invoice_company_id = data.get('invoice_company_id')
    invoice_contact_id = data.get('invoice_contact_id')

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO invoice (invoice_company_id, invoice_contact_id) VALUES (%s, %s) RETURNING id;",
                               (invoice_company_id, invoice_contact_id))
                invoice_id = cursor.fetchone()[0]
        return jsonify({"id": invoice_id, "message": "Invoice created"}), 201
    except psycopg2.Error as e:
        return jsonify({"message": "Failed to create invoice"}), 500

@app.route('/api/invoices', methods=['GET'])
@token_required(['admin', 'accountant', 'intern'])
def get_invoices():
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, timestamp, invoice_company_id, invoice_contact_id FROM invoice")
                invoices = cursor.fetchall()
                invoice_list = []
                for invoice in invoices:
                    invoice_dict = {
                        'id': invoice[0],
                        'timestamp': invoice[1],
                        'invoice_company_id': invoice[2],
                        'invoice_contact_id': invoice[3]
                    }
                    invoice_list.append(invoice_dict)

                return jsonify({'invoices': invoice_list}), 200
    except psycopg2.Error as e:
        return jsonify({'message': 'Failed to retrieve invoices'}), 500

@app.route('/api/user', methods=['POST'])
@token_required(['admin'])
def create_user():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    role = data["role"]
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_USER_TABLE)
                cursor.execute(INSERT_USERS, (username, password, role))
                user_id = cursor.fetchone()[0]
        return jsonify({"id": user_id, "message": f"User {username} created"}), 201
    except psycopg2.Error as e:
        return jsonify({"message": "Failed to create user"}), 500


@app.route('/api/users', methods=['GET'])
@token_required(['admin', 'accountant'])
def get_users():
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, username, role FROM users")
                users = cursor.fetchall()
                user_list = []
                for user in users:
                    user_dict = {
                        'id': user[0],
                        'username': user[1],
                        'role': user[2]
                    }
                    user_list.append(user_dict)

                return jsonify({'users': user_list}), 200
    except psycopg2.Error as e:
        return jsonify({'message': 'Failed to retrieve users'}), 500


if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        connection.close()
