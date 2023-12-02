from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class IdentifiedMushroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))  # Storing the username from the session
    scientific_name = db.Column(db.String(255), nullable=False)
    probability = db.Column(db.Float)
    common_names = db.Column(db.String(255))
    edibility = db.Column(db.String(100))
    description = db.Column(db.Text)
    representative_image_url = db.Column(db.String(255))
    more_info_url = db.Column(db.String(255))
    date_saved = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<IdentifiedMushroom {}>'.format(self.scientific_name)
