from flask import Flask, render_template
import datetime

app = Flask(__name__)
year = datetime.date.today().year


@app.route('/')
def index():
    return render_template('index.html', year=year)


@app.route("/about")
def about():
    return render_template('about.html', year=year)


@app.route("/contact")
def contact():
    return render_template('about.html', year=year)


@app.route("/identify")
def identify():
    return render_template('about.html', year=year)


if __name__ == "__main__":
    app.run(debug=True)
