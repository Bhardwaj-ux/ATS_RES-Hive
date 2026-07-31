#!/bin/bash
set -o errexit

echo "STEP 1: checking Django config"
python manage.py check

echo "STEP 2: generating any missing migrations"
python manage.py makemigrations --no-input

echo "STEP 3: running migrations"
python manage.py migrate --no-input

echo "STEP 4: building React frontend"
cd frontend
npm ci
npm run build
cd ..

echo "STEP 5: creating/updating admin user"
python manage.py bootstrap_admin

echo "STEP 6: collecting static files"
python manage.py collectstatic --no-input

echo "BUILD SCRIPT FINISHED"