from flask import Flask, render_template, request, flash, redirect, url_for, session
import datetime
import requests
import base64
import os
from werkzeug.utils import secure_filename
from models import db, IdentifiedMushroom
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# API configuration
API_URL = os.getenv('API_URL', 'default_api_url')
API_KEY = os.getenv('API_KEY', 'default_api_key')
API_URL_WITH_DETAILS = f"{API_URL}?details=common_names,url,description,edibility,image"

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
year = datetime.date.today().year

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///collections.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """
    Render the home page of the application.
    """
    return render_template('index.html', year=year)


@app.route("/about")
def about():
    """
    Render the 'About' page of the application.
    """
    return render_template('about.html', year=year)


@app.route("/contact")
def contact():
    """
    Render the 'Contact' page of the application.
    """
    return render_template('contact.html', year=year)


@app.route("/identify", methods=["GET", "POST"])
def identify():
    """
    Handle the identification of mushrooms through uploaded images. This endpoint
    supports both GET and POST requests. For POST requests, it processes the uploaded
    image for mushroom identification. The feature is accessible only to logged-in users.
    """
    # Check if the user is logged in, redirect to login page if not
    if 'username' not in session:
        flash('You need to be logged in to access this page.')
        return redirect(url_for('login'))

    # Handle file upload on POST request
    if request.method == "POST":
        # Check if the request contains the file part
        if 'file' not in request.files:
            flash('No file part')
            print("File not found in request")
            return redirect(request.url)

        file = request.files['file']

        # Ensure a file is selected
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        # Save the file if it is present and has a valid extension
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            #  Convert the image file to a base64 string
            with open(filepath, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode("ascii")

            print("Preparing to make the API call...")

            # Make API request with base64 image data
            response = requests.post(
                API_URL_WITH_DETAILS,
                json={
                    "images": [img_base64],
                    "similar_images": True,
                },
                headers={
                    "Content-Type": "application/json",
                    "Api-Key": API_KEY,
                }
            ).json()

            # Extract suggestions from API response
            suggestions = response.get("result", {}).get("classification", {}).get("suggestions", [])

            # Save identified mushrooms if user is logged in
            if 'username' in session:
                save_identified_mushrooms(suggestions, session['username'])

            return render_template('result.html', year=year, suggestions=suggestions)

    return render_template('identify.html', year=year)


def save_identified_mushrooms(suggestions, username):
    """
    Saves identified mushrooms to the database. Each suggestion in the `suggestions` list
    is processed and saved as an entry linked to the user's `username`.

    Parameters:
    - suggestions (list): List of mushroom identification results from the API.
    - username (str): Username of the user who performed the identification.

    Each mushroom entry includes details such as scientific name, common names, edibility,
    and links to more information, which are extracted from the suggestion data structure.
    """
    for suggestion in suggestions:
        # Attempt to retrieve and format the list of common names, if available
        common_names_list = suggestion.get('details', {}).get('common_names', [])
        if not isinstance(common_names_list, list):
            # Ensure common_names_list is always a list for consistent processing
            common_names_list = [common_names_list] if common_names_list else []
        # Join list elements into a single string separated by commas
        common_names = ', '.join([name for name in common_names_list if isinstance(name, str)])

        # Create a new IdentifiedMushroom object with all relevant data extracted from the suggestion
        new_mushroom = IdentifiedMushroom(
            username=username,  # Link the mushroom to the user
            scientific_name=suggestion.get('name', 'Unknown'),
            probability=suggestion.get('probability', 0),
            common_names=common_names,  # Formatted string of common names
            edibility=suggestion.get('details', {}).get('edibility', 'Unknown'),
            description=suggestion.get('details', {}).get('description', {}).get('value', ''),
            representative_image_url=suggestion.get('similar_images', [{}])[0].get('url', ''),
            more_info_url=suggestion.get('details', {}).get('description', {}).get('citation', ''),
            date_saved=datetime.date.today()
        )

        db.session.add(new_mushroom)
    db.session.commit()


@app.route("/result")
def result():
    """
    Displays the results page where identified mushrooms and their details are shown.
    This page is only accessible to logged-in users.
    """
    # Check if the user is logged in, redirect to login page if not
    if 'username' not in session:
        flash('You need to be logged in to access this page.')
        return redirect(url_for('login'))

    return render_template('result.html', year=year)


@app.route('/my_collection')
def my_collection():
    """
    Displays the user's personal collection of identified mushrooms.
    This page is only accessible to logged-in users.
    """
    # Check if the user is logged in, redirect to login page if not
    if 'username' not in session:
        flash('You need to be logged in to access this page.')
        return redirect(url_for('login'))

    # Retrieve all mushrooms identified by the logged-in user
    user_mushrooms = IdentifiedMushroom.query.filter_by(username=session['username']).all()

    # Render the my_collection template, passing the user's mushrooms for display
    return render_template('my_collection.html', mushrooms=user_mushrooms)


@app.route('/remove_mushroom/<int:mushroom_id>', methods=['POST'])
def remove_mushroom(mushroom_id):
    """
    Removes a specified mushroom from the user's collection.
    This endpoint is only accessible to the logged-in user who owns the mushroom.

    Parameters:
    - mushroom_id (int): The database ID of the mushroom to be removed.
    """
    # Check if the user is logged in, redirect to login page if not
    if 'username' not in session:
        return redirect(url_for('login'))

    # Retrieve the mushroom by its ID
    mushroom = IdentifiedMushroom.query.get(mushroom_id)
    # Check if the mushroom exists and belongs to the logged-in user
    if mushroom and mushroom.username == session['username']:
        db.session.delete(mushroom)
        db.session.commit()
        flash('Mushroom removed from your collection.')

    return redirect(url_for('my_collection'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Manages user registration. Accepts user details and communicates with the authentication
    microservice to register the user. Redirects to the login page upon successful registration.
    """
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Send a POST request to the authentication microservice to register the user
        response = requests.post('http://localhost:5001/register', json={'username': username, 'email': email, 'password': password})

        # Check if the registration was successful (HTTP 201)
        if response.status_code == 201:
            return redirect(url_for('login'))
        else:
            error_message = response.json().get('message', 'An error occurred during registration.')
            flash(error_message)
            return render_template('register.html')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login. Validates user credentials against the authentication microservice
    and creates a session for the user upon successful login.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Send a POST request to the authentication microservice to validate the user's credentials
        response = requests.post('http://localhost:5001/login', json={'username': username, 'password': password})

        # Check if the login was successful (HTTP 200)
        if response.status_code == 200:
            # Store the authentication token and username in the session
            session['token'] = response.json()['token']
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Handles user logout by clearing the session and redirecting the user to the index page.
    """
    # Remove token and username from session
    session.pop('token', None)
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

