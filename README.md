# Utility Mixin 🌀

This is a utility mixin that provides CRUD and JSON operations for your models.

It requires Flask-SQLAlchemy to be installed, as it makes use of the paginate method.

## Installation

The mixin is a single file, so you can just copy it into your project.

[__utility_mixin__.py](app%2Fmodels%2F__utility_mixin__.py)

## Setup of this project

 - Clone the repository 
 - install the dependencies

### Commands

Create the database
```bash
flask init
```

Reset the database
```bash
flask reset
```

Show all records
```bash
flask all
```

Show records using pagination
```bash
flask page
# or
flask page 2
# adding a number to the end will select the page, page 1 is default
```

Show records using pagination, return a JSON friendly dict
```bash
flask page-json
# or
flask page-json 2
# adding a number to the end will select the page, page 1 is default
```

Load fake records
```bash
flask load
# or
flask load 10
# adding a number to the end will select the number of records to load, 1 is default
```

Update a random record using the classmethod
```bash
flask update-cls
```

Update a random record using the instance method
```bash
flask update-inline
```

Delete a random record
```bash
flask delete
```

