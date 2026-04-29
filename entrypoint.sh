#!/bin/sh
set -e

python manage.py collectstatic --noinput
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Running tests..."
DJANGO_SETTINGS_MODULE=ma_chorale.settings.test pytest

if [ $? -ne 0 ]; then
    echo "Tests failed. Exiting."
    exit 1
fi

echo "✅ All tests passed, Starting application..."
exec "$@"
