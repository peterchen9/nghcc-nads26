from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

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
