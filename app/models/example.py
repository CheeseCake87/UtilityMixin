from datetime import datetime

from app.extensions import db
from .__mixins__ import UtilityMixin


class Example(db.Model, UtilityMixin):
    db = db

    example_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, nullable=False, default=datetime.now())
