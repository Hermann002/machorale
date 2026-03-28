#!/bin/sh
set -e

python manage.py collectstatic --noinput
python manage.py makemigrations --noinput
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting application..."
exec "$@"
