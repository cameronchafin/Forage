from flask import Flask, render_template, request, flash, redirect
import datetime
import requests
import base64
import os
from werkzeug.utils import secure_filename


API_URL = "https://mushroom.kindwise.com/api/v1/identification"
API_KEY = "lLPXIjX93GaPI6BgVBVgFjmgSFCJp3K6B6rcXKNgvWkFgUmhXE"
API_URL_WITH_DETAILS = f"{API_URL}?details=common_names,url,description,edibility,image"

app = Flask(__name__)
app.secret_key = "secret_key"
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

            return render_template('result.html', year=year, suggestions=suggestions)

    return render_template('identify.html', year=year)


@app.route("/result")
def result():
    return render_template('result.html', year=year)


if __name__ == "__main__":
    app.run(debug=True)
