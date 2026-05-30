#!/bin/sh
set -e

python manage.py collectstatic --noinput
echo "Applying database migrations..."
python manage.py migrate --noinput

exec "$@"
