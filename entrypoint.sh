#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Collect static files (optional; uncomment if needed)
# echo "Collecting static files..."
# python manage.py collectstatic --noinput

# Start Gunicorn server
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 stud_test.wsgi:application
