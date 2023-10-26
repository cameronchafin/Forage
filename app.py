from flask import Flask, render_template, request, flash, redirect
from werkzeug.utils import secure_filename
import datetime
import requests
import os

API_URL = "https://mushroom.kindwise.com/api/v1/identification"
API_KEY = "lLPXIjX93GaPI6BgVBVgFjmgSFCJp3K6B6rcXKNgvWkFgUmhXE"

app = Flask(__name__)
year = datetime.date.today().year

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = "uploads"


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
    if request.method == "POST":
        # Check if an image was uploaded
        if 'image' not in request.files:
            flash('No image part')
            return redirect(request.url)
        file = request.files['image']

        # Check if the image is valid
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)

            # Call your API function
            result = identify_mushroom_with_api(image_path)

            # Depending on your results page design, you might directly render the results page here
            return render_template('result.html', result=result)

            # Or you might want to redirect to a separate results page with some session data
            # session['result'] = result
            # return redirect(url_for('results'))

    # If it's a GET request or if there's any other condition you've not met, render the identify page.
    return render_template('identify.html', year=year)


@app.route("/result")
def result():
    return render_template('result.html', year=year)


def identify_mushroom_with_api(image_path):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Api-Key": API_KEY,
        "Content-Type": "multipart/form-data"
    }

    # Additional params
    params = {
        "details": "common_names,url,description,edibility,image",
        "language": "en",
        "async": "false"  # We want to wait for the response
    }

    with open(image_path, 'rb') as image_file:
        files = {'image': image_file}
        response = requests.post(API_URL + "/identification", headers=headers, files=files, params=params)

    print(response.status_code)
    print(response.text)

    # Assuming the API returns data in JSON format
    try:
        data = response.json()
        return data
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return None


if __name__ == "__main__":
    app.run(debug=True)
