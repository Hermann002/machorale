#!/bin/sh
set -e

python manage.py collectstatic --noinput
python manage.py makemigrations --noinput
echo "Applying database migrations..."
python manage.py migrate --noinput

pytest

if [ $? -ne 0 ]; then
    echo "Tests failed. Exiting."
    exit 1
fi

echo "Starting application..."
exec "$@"
