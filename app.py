from flask import Flask, render_template, request, flash, redirect, url_for, session
import datetime
import requests
import base64
import os
from werkzeug.utils import secure_filename
from models import db, IdentifiedMushroom


API_URL = "https://mushroom.kindwise.com/api/v1/identification"
API_KEY = "lLPXIjX93GaPI6BgVBVgFjmgSFCJp3K6B6rcXKNgvWkFgUmhXE"
API_URL_WITH_DETAILS = f"{API_URL}?details=common_names,url,description,edibility,image"

app = Flask(__name__)
app.secret_key = "secret_key"
year = datetime.date.today().year

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = "uploads"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///collections.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html', year=year)


@app.route("/about")
def about():
    return render_template('about.html', year=year)


@app.route("/contact")
def contact():
    return render_template('contact.html', year=year)


@app.route("/identify", methods=["GET", "POST"])
def identify():
    if 'username' not in session:
        flash('You need to be logged in to access this page.')
        return redirect(url_for('login'))

    if request.method == "POST":

        if 'file' not in request.files:
            flash('No file part')
            print("File not found in request")
            return redirect(request.url)
        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with open(filepath, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode("ascii")

            print("Preparing to make the API call...")

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

            suggestions = response.get("result", {}).get("classification", {}).get("suggestions", [])

            # Check if user is logged in before saving
            if 'username' in session:
                save_identified_mushrooms(suggestions, session['username'])

            return render_template('result.html', year=year, suggestions=suggestions)

    return render_template('identify.html', year=year)


def save_identified_mushrooms(suggestions, username):
    for suggestion in suggestions:

        common_names_list = suggestion.get('details', {}).get('common_names', [])
        if not isinstance(common_names_list, list):
            common_names_list = [common_names_list] if common_names_list else []
        common_names = ', '.join([name for name in common_names_list if isinstance(name, str)])

        new_mushroom = IdentifiedMushroom(
            username=username,
            scientific_name=suggestion.get('name', 'Unknown'),
            probability=suggestion.get('probability', 0),
            common_names=common_names,
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
    if 'username' not in session:
        flash('You need to be logged in to access this page.')
        return redirect(url_for('login'))

    return render_template('result.html', year=year)


@app.route('/my_collection')
def my_collection():
    if 'username' not in session:
        flash('You need to be logged in to access this page.')
        return redirect(url_for('login'))

    user_mushrooms = IdentifiedMushroom.query.filter_by(username=session['username']).all()
    return render_template('my_collection.html', mushrooms=user_mushrooms)


@app.route('/remove_mushroom/<int:mushroom_id>', methods=['POST'])
def remove_mushroom(mushroom_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    mushroom = IdentifiedMushroom.query.get(mushroom_id)
    if mushroom and mushroom.username == session['username']:
        db.session.delete(mushroom)
        db.session.commit()
        flash('Mushroom removed from your collection.')

    return redirect(url_for('my_collection'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        response = requests.post('http://localhost:5001/register', json={'username': username, 'email': email, 'password': password})
        if response.status_code == 201:
            return redirect(url_for('login'))
        else:
            error_message = response.json().get('message', 'An error occurred during registration.')
            flash(error_message)
            return render_template('register.html')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post('http://localhost:5001/login', json={'username': username, 'password': password})

        if response.status_code == 200:
            session['token'] = response.json()['token']
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('token', None)
    session.pop('username', None)  # Clear the username or identifier
    return redirect(url_for('index'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

