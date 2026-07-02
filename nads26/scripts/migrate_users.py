import os
import sys
import django

# Add the project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from django.contrib.auth.models import User

users = [
    {
        'id': 1,
        'username': 'admin',
        'password': 'pbkdf2_sha256$1000000$94wkYpllaVrZ7Sinbwyesi$DCkb0uBMSuhqE7w2hcfIqbCzqMPa53dNRe6uOTh0hyY=',
        'is_superuser': True,
        'is_staff': True,
        'date_joined': '2026-02-12 15:26:41.567609',
    },
    {
        'id': 2,
        'username': 'user',
        'password': 'pbkdf2_sha256$1000000$VqWWEQ8gKp4rmTfLWvBJRk$jGGg08/11CpN7Hxk52p4j6/MVGUl90moAHu040p8LTA=',
        'is_superuser': False,
        'is_staff': True,
        'date_joined': '2026-02-15 00:11:41.082049',
    },
    {
        'id': 3,
        'username': 'peter',
        'password': 'pbkdf2_sha256$1000000$JFslvOQ8YXpa1gRexPjh7Y$78W4b3cIzxyK3cRet3DvF0ADatGLuaBS1M/BRLIOBBo=',
        'is_superuser': False,
        'is_staff': True,
        'date_joined': '2026-02-15 00:11:52.401801',
    },
]

for u_data in users:
    user, created = User.objects.get_or_create(username=u_data['username'])
    user.password = u_data['password']
    user.is_superuser = u_data['is_superuser']
    user.is_staff = u_data['is_staff']
    user.save()
    if created:
        print(f"Created user: {u_data['username']}")
    else:
        print(f"Updated user: {u_data['username']}")
