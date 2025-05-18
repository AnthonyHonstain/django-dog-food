




## Setup of Environment

* Initialize mamba environment `mamba create -n django-dog-food -c conda-forge  python=3.13`
* `mamba activate django-dog-food`
* `pip install poetry`
* `poetry install --no-root`
* `python manage.py migrate`
* `python manage.py createsuperuser`
* `python manage.py runserver 8002`
    *  Alternatively can run with gunicorn `gunicorn --bind 0.0.0.0:8002 dogfood.wsgi -w 1`
* `python manage.py test`
* `mypy .`
* `black .`

---

### Building the docker image

```shell
docker build -t django-dog-food .

docker run -it --rm -p 8002:8002 django-dog-food 
```

What it looks like when the docker container starts
```shell
❯ docker run -it --rm -p 8002:8002 django-dog-food 

Skipping virtualenv creation, as specified in config file.
[2025-05-18 20:19:39 +0000] [1] [INFO] Starting gunicorn 23.0.0
[2025-05-18 20:19:39 +0000] [1] [INFO] Listening at: http://0.0.0.0:8002 (1)
[2025-05-18 20:19:39 +0000] [1] [INFO] Using worker: sync
[2025-05-18 20:19:39 +0000] [12] [INFO] Booting worker with pid: 12
[2025-05-18 20:19:39 +0000] [13] [INFO] Booting worker with pid: 13
[2025-05-18 20:19:39 +0000] [14] [INFO] Booting worker with pid: 14
[2025-05-18 20:19:39 +0000] [15] [INFO] Booting worker with pid: 15
```

### How I created the service

Get poetry bootstrapped

```shell
pip install poetry

poetry new django-dog-food
# Remove src and test that were generated
poetry add django
poetry add django-stubs
poetry add psycopg2-binary
poetry add pytest
poetry add pytest-django
poetry add black
poetry add mypy
poetry add gunicorn


django-admin startproject dogfood
# Clean up the directory structure to keep things flat
```

You need to get mypy setup, add initial mypy.ini
```
[mypy]
# Global mypy settings (if any)
plugins =
    mypy_django_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = "finance_service.settings"
```

Setup a .gitignore file

Get the Django app going

```shell
python manage.py startapp foodtracker

❯ tree
.
├── db.sqlite3
├── django-dog-food.iml
├── dogfood
│   ├── asgi.py
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── foodtracker
│   ├── admin.py
│   ├── apps.py
│   ├── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── manage.py
├── mypy.ini
├── poetry.lock
├── pyproject.toml
└── README.md
```

NOTE - we still haven't dealt with the database (notice the sqlite3 file)
