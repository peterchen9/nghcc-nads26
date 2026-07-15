from .models import MenuItem


def normalize_route(route):
    route = (route or '').strip()
    if not route:
        return ''
    if not route.startswith('/'):
        route = f'/{route}'
    if not route.endswith('/'):
        route = f'{route}/'
    return route


def route_matches_path(route, path):
    normalized_route = normalize_route(route)
    normalized_path = normalize_route(path)
    if not normalized_route or not normalized_path:
        return False
    return normalized_path == normalized_route or normalized_path.startswith(normalized_route)


def active_routed_menu_items():
    return MenuItem.objects.filter(is_active=True).exclude(route='')


def find_menu_item_for_path(path):
    items = active_routed_menu_items().select_related('parent')
    for item in sorted(items, key=lambda item: len(normalize_route(item.route)), reverse=True):
        if route_matches_path(item.route, path):
            return item
    return None


def allowed_menu_ids_for_user(user):
    if not user.is_authenticated:
        return set()
    if user.is_superuser:
        return set(MenuItem.objects.filter(is_active=True).values_list('id', flat=True))
    try:
        return set(user.profile.allowed_menu_items.filter(is_active=True).values_list('id', flat=True))
    except Exception:
        return set()


def user_can_access_menu_item(user, menu_item):
    if not user.is_authenticated or not menu_item:
        return False
    if user.is_superuser:
        return True

    allowed_ids = allowed_menu_ids_for_user(user)
    if menu_item.id in allowed_ids:
        return True
    if menu_item.parent_id and menu_item.parent_id in allowed_ids:
        return True
    return False


def user_can_access_route(user, route):
    matched_item = find_menu_item_for_path(route)
    if not matched_item:
        return False
    return user_can_access_menu_item(user, matched_item)


def expand_menu_ids(menu_ids):
    clean_ids = []
    for raw_id in menu_ids or []:
        try:
            clean_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    selected_items = list(
        MenuItem.objects.filter(id__in=clean_ids, is_active=True).select_related('parent')
    )
    expanded_ids = {item.id for item in selected_items}

    selected_parent_ids = {item.id for item in selected_items if item.parent_id is None}
    if selected_parent_ids:
        expanded_ids.update(
            MenuItem.objects.filter(
                parent_id__in=selected_parent_ids,
                is_active=True,
            ).values_list('id', flat=True)
        )

    expanded_ids.update(item.parent_id for item in selected_items if item.parent_id)
    return expanded_ids
