from django.db.models import Prefetch
from .models import MenuItem

def menu_processor(request):
    if not request.user.is_authenticated:
        return {'side_menu': []}

    if request.user.is_superuser:
        menu_items = MenuItem.objects.filter(
            parent=None, is_active=True
        ).prefetch_related(
            Prefetch('children', queryset=MenuItem.objects.filter(is_active=True))
        )
        return {'side_menu': menu_items}

    try:
        profile = request.user.profile
        allowed_ids = set(profile.allowed_menu_items.filter(is_active=True).values_list('id', flat=True))
    except Exception:
        allowed_ids = set()

    # Prefetch only allowed children
    allowed_children_qs = MenuItem.objects.filter(id__in=allowed_ids, is_active=True)
    roots = MenuItem.objects.filter(parent=None, is_active=True).prefetch_related(
        Prefetch('children', queryset=allowed_children_qs)
    )

    filtered_menu = []
    for item in roots:
        # Check if the root menu has a route and is allowed, or if it has allowed children
        children_list = list(item.children.all())
        if (item.route and item.id in allowed_ids) or len(children_list) > 0:
            filtered_menu.append(item)

    return {'side_menu': filtered_menu}

