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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'message': 'Token is missing'}), 403

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 403

        return f(*args, **kwargs)

    return decorated  # Return the inner decorated function as a view function

@app.route("/api/login")
def login():
    auth = request.authorization

    if auth and auth.username == 'your_username' and auth.password == 'your_password':
        token = jwt.encode({'user': auth.username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({'token': token})

    return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.route('/api/company', methods=['POST'])
@token_required
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
@token_required
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
