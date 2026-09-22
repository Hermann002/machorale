#!/bin/sh
set -e

echo "Django settings: ${DJANGO_SETTINGS_MODULE}"

python manage.py collectstatic --noinput

echo "Applying database migrations..."

python manage.py migrate --noinput

python manage.py compilemessages

exec "$@"
