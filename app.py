from functools import wraps
from flask import Flask, request, jsonify, make_response
import os
import psycopg2
from dotenv import load_dotenv
import jwt
import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

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

JWT_EXPIRATION_DELTA = datetime.timedelta(minutes=30)
def authenticate_user(username, password):
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT username, role FROM users WHERE username = %s AND password = %s", (username, password))
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
                # Check if the token is provided as a query parameter
                token = request.args.get('token')

            if not token:
                return jsonify({'message': 'Token is missing'}), 403

            try:
                if token.startswith('Bearer '):
                    token = token.split(' ')[1]

                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = data.get('username')

                # Fetch the user's role from the database
                user_role = get_user_role(username)

                # Check if the user's role is allowed
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
        # Handle the database error appropriately, e.g., log the error or return an error response.
        return None




@app.route("/api/login", methods=['POST'])  # Changed to POST method to accept JSON data
def login():
    data = request.get_json()
    auth_username = data.get('username')
    auth_password = data.get('password')
    user = authenticate_user(auth_username, auth_password)

    if user:
        username, _ = user
        token_payload = {'username': username, 'exp': datetime.datetime.utcnow() + JWT_EXPIRATION_DELTA}
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token}), 200

    return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.route('/api/company', methods=['POST'])
@token_required(['admin'])
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


if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        # Close the database connection when the application exits
        connection.close()