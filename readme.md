# Company Database Management App

This Python Flask application is designed to manage a simple company database. It offers various API endpoints for creating and retrieving information about companies, contacts, invoices, and users. Additionally, it provides user authentication and authorization through JSON Web Tokens (JWT) and session management.

## Getting Started

Before running the application, make sure you have the following prerequisites installed:

- Python 3.x
- PostgreSQL database
- `pip` (Python package manager)

### Installation

1. Clone the repository:

   
    git clone https://github.com/yourusername/company-database-app.git

Change to the project directory:
    
    cd company-database-app

Install the required Python packages using pip:



    pip install -r requirements.txt

Set up a PostgreSQL database and configure the connection details in a .env file. You can copy the .env.example file and customize it with your database details:



    cp .env.example .env

Modify the .env file to set your PostgreSQL database credentials and other configuration options.

Initialize the database schema by running the following command:



    python initialize_database.py

Start the Flask application:



    python app.py

The application should now be running locally at http://localhost:5000.
Usage
User Authentication

To use the API endpoints that require authentication and authorization, you need to obtain a JSON Web Token (JWT) by sending a POST request to /api/login with your username and password in the request body.



    curl -X POST -H "Content-Type: application/json" -d '{"username": "yourusername", "password": "yourpassword"}' http://localhost:5000/api/login

After successfully logging in, you will receive a JWT token in the response, which you should include in the Authorization header for subsequent requests.



    curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:5000/api/some-protected-endpoint

## API Endpoints
### Companies:

Create a new company (admin and accountant roles):



    POST /api/company

Get a list of all companies (admin, accountant, and intern roles):


    GET /api/companies

### Contacts:

Create a new contact (admin, accountant, and intern roles):



    POST /api/contact

Get a list of all contacts (admin, accountant, and intern roles):



    GET /api/contacts

### Invoices:

Create a new invoice (admin and accountant roles):



    POST /api/invoice

Get a list of all invoices (admin, accountant, and intern roles):



    GET /api/invoices

### Users :

Create a new user (admin role):



    POST /api/user

Get a list of all users (admin and accountant roles):

    

    GET /api/users

## Contributing

Contributions are welcome! If you find a bug or want to add new features, please open an issue or create a pull request.