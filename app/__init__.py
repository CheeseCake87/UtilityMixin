from flask import Flask

from app.extensions import imp, db


def create_app():
    app = Flask(__name__)
    imp.init_app(app)
    imp.import_models("models")
    db.init_app(app)

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Database created.")

    @app.cli.command("reset-db")
    def init_db():
        db.drop_all()
        db.create_all()
        print("Database reset.")

    @app.cli.command("load-db")
    def load_db():
        from app.models.example import Example
        from faker import Faker

        fake = Faker()

        fr = []

        for _ in range(500):
            fr.append(
                {
                    "name": fake.name(),
                    "description": fake.text(),
                }
            )

        Example.um_create_batch(fr)

        print("Database loaded.")

    return app
