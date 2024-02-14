from flask import Flask

from app.extensions import imp, db


def create_app():
    app = Flask(__name__)
    imp.init_app(app)
    imp.import_models("models")
    db.init_app(app)

    @app.cli.command("init")
    def init_db():
        db.create_all()
        print("Database created.")

    @app.cli.command("reset")
    def init_db():
        db.drop_all()
        db.create_all()
        print("Database reset.")

    @app.cli.command("load")
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

        print(f"Database loaded. There are now {Example.um_count()} records.")

    return app


    @app.cli.command("delete-random")
        def delete_random_record():
            from app.models.example import Example
            import random

            count = Example.um_count()
            record = Example.um_read()

            Example.um_delete(random.choice(Example.query.all()).example_id)
            print(f"Random record deleted. There are now {Example.um_count()} records.")
