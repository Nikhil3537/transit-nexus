#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

if [ -n "$DJANGO_ADMIN_USERNAME" ] && [ -n "$DJANGO_ADMIN_PASSWORD" ]; then
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os

User = get_user_model()

username = os.environ['DJANGO_ADMIN_USERNAME']
password = os.environ['DJANGO_ADMIN_PASSWORD']

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
    }
)

if created:
    user.set_password(password)
    user.save()
    print('Admin user created successfully.')
else:
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.set_password(password)
    user.save()
    print('Admin user already existed; password updated.')
"
fi