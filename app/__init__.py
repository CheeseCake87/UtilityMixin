import random
from pprint import pprint

import click
from faker import Faker
from flask import Flask

from app.extensions import imp, db
from app.models.example import Example


def create_app():
    app = Flask(__name__)
    imp.init_app(app)
    imp.import_models("models")
    db.init_app(app)

    @app.cli.command("init")
    def init():
        db.create_all()
        print("Database created.")

    @app.cli.command("reset")
    def reset():
        db.drop_all()
        db.create_all()
        print("Database reset.")

    @app.cli.command("all")
    def show_all_records():
        results = Example.um_read()

        print(f"Database has {Example.um_count()} records.")
        print("Results:")
        print(results)

    @app.cli.command("page")
    @click.argument("page", type=int, default=1)
    def show_paged_records(page):
        results = Example.um_read(
            paginate=True,
            paginate_page=page,
            paginate_per_page=5,
            paginate_error_out=False,
        )

        if page > results.pages:
            print(f"Page {page} does not exist.")
            return

        print(f"Database has {Example.um_count()} records.")
        print(f"Page {page} of {results.pages}")
        print(f"Has previous: {results.has_prev}")
        print(f"Has next: {results.has_next}")
        print("Results:")
        print(results.items)

    @app.cli.command("load")
    @click.argument("amount", type=int, default=1)
    def load(amount):
        if amount < 1:
            print("Amount must be greater than 0.")
            return

        if amount > 1:
            fake = Faker()

            fr = []

            for _ in range(amount):
                fr.append(
                    {
                        "name": fake.name(),
                        "description": fake.text(),
                    }
                )

            if amount < 11:
                results = Example.um_create_batch(fr, return_records=True)

                print(f"Database loaded. There are now {Example.um_count()} records.")
                print("Results:")
                print(results)
                return

            Example.um_create_batch(fr)
            print(f"Database loaded. There are now {Example.um_count()} records.")
            print("Printing skipped due to amount being greater than 10.")

        else:
            fake = Faker()

            result = Example.um_create({
                "name": fake.name(),
                "description": fake.text(),
            }, return_record=True)

            print(f"Database loaded. There are now {Example.um_count()} records.")
            print("Result:")
            print(result)

    @app.cli.command("delete")
    def delete_random_record():
        all_records = Example.um_read()

        random_record = random.choice(all_records)

        print(f"Deleting random record: {random_record}")
        Example.um_delete(random_record.example_id)

        print(f"Random record deleted. There are now {Example.um_count()} records.")
        print("Deleted record:")
        print(random_record)

    @app.cli.command("update-inline")
    def update_random_record_inline():
        all_records = Example.um_read()

        random_record = random.choice(all_records)

        print(f"Updating random record: {random_record}")
        print(f"Original record name: {random_record.name}")
        print("---")
        print(f"Class method update attr name to 'Updated Name'")
        random_record.um_update_inline({"name": "Updated Name"})
        print("-")
        cls_query_update = Example.um_read(random_record.example_id, one_or_none=True)
        print(f"Updated record name (new query): {cls_query_update.name}")
        print("---")

        print(f"Random record updated.")

    @app.cli.command("update-cls")
    def update_random_record_cls():
        all_records = Example.um_read()

        random_record = random.choice(all_records)

        print(f"Updating random record: {random_record}")
        print(f"Original record name: {random_record.name}")
        print("---")
        print(f"Class method update attr name to 'Updated Name'")
        Example.um_update(
            {"example_id": random_record.example_id, "name": "Updated Name"}
        )
        print("-")
        cls_query_update = Example.um_read(random_record.example_id, one_or_none=True)
        print(f"Updated record name (new query): {cls_query_update.name}")
        print("---")

        print(f"Random record updated.")

    @app.cli.command("page-json")
    @click.argument("page", type=int, default=1)
    def show_paged_records_in_json(page):
        results = Example.um_read(
            paginate=True,
            paginate_page=page,
            paginate_per_page=2,
            paginate_error_out=False,
            as_json=True,
            json_remove_return_key=True,
        )

        pprint(results)

    return app
