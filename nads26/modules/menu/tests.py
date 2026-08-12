from django.contrib.auth.models import User
from django.test import RequestFactory, SimpleTestCase, TestCase

from modules.menu.context_processors import menu_processor
from modules.menu.models import MenuItem
from modules.menu.permissions import (
    expand_menu_ids,
    user_can_access_menu_item,
)


class MenuPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='worker', password='test')
        self.parent = MenuItem.objects.create(title='同工', order=1)
        self.allowed_child = MenuItem.objects.create(
            title='休假表',
            route='/staff/leaves/',
            parent=self.parent,
            order=1,
        )
        self.denied_child = MenuItem.objects.create(
            title='出勤狀態',
            route='/eureka/attendance/',
            parent=self.parent,
            order=2,
        )

    def test_child_permission_does_not_include_parent_or_sibling(self):
        expanded_ids = expand_menu_ids([self.allowed_child.id])

        self.assertEqual(expanded_ids, {self.allowed_child.id})

    def test_parent_permission_expands_to_all_children_when_explicitly_selected(self):
        expanded_ids = expand_menu_ids([self.parent.id])

        self.assertEqual(
            expanded_ids,
            {self.parent.id, self.allowed_child.id, self.denied_child.id},
        )

    def test_parent_record_alone_does_not_grant_child_route(self):
        self.user.profile.allowed_menu_items.set([self.parent])

        self.assertFalse(
            user_can_access_menu_item(self.user, self.allowed_child)
        )

    def test_menu_only_renders_explicitly_allowed_child(self):
        self.user.profile.allowed_menu_items.set([self.allowed_child])
        request = RequestFactory().get('/')
        request.user = self.user

        side_menu = menu_processor(request)['side_menu']

        self.assertEqual([item.id for item in side_menu], [self.parent.id])
        self.assertEqual(
            [item.id for item in side_menu[0].children.all()],
            [self.allowed_child.id],
        )


from django.core.management import call_command
from modules.accounts.models import UserProfile, SystemSetting
from modules.eureka.models import StaffInfo
from rest_framework.test import APIRequestFactory
from modules.accounts.views import identity_permissions_detail
import json
import runpy
from pathlib import Path

class IncrementalPermissionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='worker', password='test')
        self.profile = self.user.profile
        
        # Create standard menu items
        self.standard_items = []
        from modules.menu.permissions import STANDARD_USER_MENU_ROUTES
        for i, route in enumerate(STANDARD_USER_MENU_ROUTES):
            item = MenuItem.objects.create(
                title=f'Standard Item {i}',
                route=route,
                order=i,
                is_active=True
            )
            self.standard_items.append(item)
            
        # Create a custom menu item not in the standard list
        self.custom_item = MenuItem.objects.create(
            title='Custom Item',
            route='/custom/route/',
            order=100,
            is_active=True
        )

    def test_apply_standard_menu_permissions_adds_items_without_removing_custom_ones(self):
        # 1. Grant custom permission to user
        self.profile.allowed_menu_items.set([self.custom_item])
        
        # 2. Run management command
        call_command('apply_standard_menu_permissions')
        
        # 3. Verify standard permissions were added
        allowed_ids = set(self.profile.allowed_menu_items.values_list('id', flat=True))
        for item in self.standard_items:
            self.assertIn(item.id, allowed_ids)
            
        # 4. Verify custom permission was NOT removed
        self.assertIn(self.custom_item.id, allowed_ids)

    def test_identity_permissions_update_does_not_wipe_custom_permissions(self):
        # Create StaffInfo linking user to identity 'P1'
        staff_info = StaffInfo.objects.create(
            staff_id=999,
            name='Test Staff',
            identity_code='P1',
            user=self.user,
            is_active=True
        )
        
        # Grant custom permission
        self.profile.allowed_menu_items.set([self.custom_item])
        
        # Update identity permissions via API POST (initial POST)
        factory = APIRequestFactory()
        req = factory.post(
            '/users/identity-permissions/P1/',
            json.dumps({'menu_ids': [self.standard_items[0].id]}),
            content_type='application/json'
        )
        self.user.is_superuser = True
        self.user.save()
        req.user = self.user
        
        resp = identity_permissions_detail(req, 'P1')
        self.assertEqual(resp.status_code, 200)
        
        # Verify user has both custom item and standard item 0
        allowed_ids = set(self.profile.allowed_menu_items.values_list('id', flat=True))
        self.assertIn(self.custom_item.id, allowed_ids)
        self.assertIn(self.standard_items[0].id, allowed_ids)
        
        # Update identity permissions again (adding standard item 1, removing 0)
        req2 = factory.post(
            '/users/identity-permissions/P1/',
            json.dumps({'menu_ids': [self.standard_items[1].id]}),
            content_type='application/json'
        )
        req2.user = self.user
        resp2 = identity_permissions_detail(req2, 'P1')
        self.assertEqual(resp2.status_code, 200)
        
        # Verify standard item 0 is removed, standard item 1 is added, custom item is STILL present
        allowed_ids_updated = set(self.profile.allowed_menu_items.values_list('id', flat=True))
        self.assertIn(self.custom_item.id, allowed_ids_updated)
        self.assertNotIn(self.standard_items[0].id, allowed_ids_updated)
        self.assertIn(self.standard_items[1].id, allowed_ids_updated)


class MenuSyncSafetyTests(TestCase):
    def test_init_menu_preserves_ids_permissions_and_custom_items(self):
        user = User.objects.create_user(username='menu-sync-worker', password='test')
        existing = MenuItem.objects.create(
            title='舊休假表名稱',
            route='/staff/leaves/',
            order=99,
        )
        custom = MenuItem.objects.create(
            title='自訂選單',
            route='/custom/preserved/',
            order=999,
        )
        user.profile.allowed_menu_items.set([existing, custom])
        original_id = existing.id

        script_path = Path(__file__).resolve().parents[2] / 'scripts' / 'init_menu.py'
        runpy.run_path(str(script_path), run_name='__main__')
        runpy.run_path(str(script_path), run_name='__main__')

        existing.refresh_from_db()
        allowed_ids = set(
            user.profile.allowed_menu_items.values_list('id', flat=True)
        )
        self.assertEqual(existing.id, original_id)
        self.assertEqual(existing.title, '休假表')
        self.assertIn(original_id, allowed_ids)
        self.assertIn(custom.id, allowed_ids)
        self.assertTrue(MenuItem.objects.filter(id=custom.id).exists())


class BaseTemplateScrollRestorationTests(SimpleTestCase):
    def test_base_template_preserves_scroll_after_confirmed_actions(self):
        template_path = Path(__file__).resolve().parents[2] / 'templates' / 'base.html'
        source = template_path.read_text(encoding='utf-8')

        for marker in [
            'PAGE_SCROLL_PENDING_KEY',
            'preparePageScrollRestore',
            'restorePageScroll',
            "document.addEventListener('submit'",
            'window.confirm = function',
            "window.addEventListener('pagehide'",
            'scrollableContentElements',
        ]:
            self.assertIn(marker, source)
