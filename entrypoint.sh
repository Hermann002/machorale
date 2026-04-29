#!/bin/sh
set -e

python manage.py collectstatic --noinput
python manage.py makemigrations --noinput
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Running tests..."
pytest --create-db --ds=ma_chorale.settings --cov=ma_chorale --cov-report=xml --cov-report=html

if [ $? -ne 0 ]; then
    echo "Tests failed. Exiting."
    exit 1
fi

echo "✅ All tests passed, Starting application..."
exec "$@"
