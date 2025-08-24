release: python manage.py collectstatic --noinput && python manage.py migrate
web: gunicorn core.wsgi.application --log-file -
