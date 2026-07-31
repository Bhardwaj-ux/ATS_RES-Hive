#!/bin/bash
set -o errexit

echo "STEP 1: checking Django config"
python manage.py check

echo "STEP 2: generating any missing migrations"
python manage.py makemigrations --no-input

echo "STEP 3: reconciling migration history (one-time fix for jobs.0004)"
python manage.py migrate jobs 0004_job_priority_ctc_skills --fake || true

echo "STEP 4: running migrations"
python manage.py migrate --no-input

echo "STEP 5: building React frontend"
cd frontend
npm ci
npm run build
cd ..

echo "STEP 6: creating/updating admin user"
python manage.py bootstrap_admin

echo "STEP 7: collecting static files"
python manage.py collectstatic --no-input

echo "BUILD SCRIPT FINISHED"