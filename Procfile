release: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py backfill_interest_deposits --year 2025
web: gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --log-file -
