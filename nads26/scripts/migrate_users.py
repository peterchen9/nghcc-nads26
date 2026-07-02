import os
import sys
import json
import django

# Add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from django.contrib.auth.models import User

migration_file = os.environ.get('USERS_MIGRATION_FILE', '').strip()
if not migration_file:
    raise RuntimeError('USERS_MIGRATION_FILE must point to a JSON file outside the repository.')

with open(migration_file, encoding='utf-8') as source:
    users = json.load(source)

if not isinstance(users, list):
    raise ValueError('The user migration JSON must contain a list of user objects.')

for u_data in users:
    if not all(key in u_data for key in ('username', 'password', 'is_superuser', 'is_staff')):
        raise ValueError('Each user entry must include username, password, is_superuser, and is_staff.')
    user, created = User.objects.get_or_create(username=u_data['username'])
    user.password = u_data['password']
    user.is_superuser = u_data['is_superuser']
    user.is_staff = u_data['is_staff']
    user.save()
    if created:
        print(f"Created user: {u_data['username']}")
    else:
        print(f"Updated user: {u_data['username']}")
