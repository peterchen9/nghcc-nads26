from decimal import Decimal, InvalidOperation
from io import BytesIO
import json
import re
import subprocess

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from openpyxl import Workbook, load_workbook

from .models import BudgetChangeLog, BudgetItem

FIELDS = [
    ('category', '分類'),
    ('budget_code', '2026預算代號'),
    ('ministry', '事工'),
    ('annual_goal', '年度目標'),
    ('strategy_plan', '策略&執行計畫'),
    ('activity_budget', '活動與預算'),
    ('lead_pastor', '主責牧者'),
    ('budget_2026', '2026預算'),
    ('accounting_subject', '會計科目'),
]
FORM_FIELDS = FIELDS[:8] + [('used_amount', '已使用金額')] + FIELDS[8:]

HEADER_ALIASES = {
    '分類': 'category',
    '2026預算代號': 'budget_code',
    '事工': 'ministry',
    '年度目標': 'annual_goal',
    '策略&執行計畫': 'strategy_plan',
    '策略＆執行計畫': 'strategy_plan',
    '活動與預算': 'activity_budget',
    '主責牧者': 'lead_pastor',
    '2026預算': 'budget_2026',
    '會計科目': 'accounting_subject',
    '已使用金額': 'used_amount',
    '使用金額': 'used_amount',
    '美美紀錄': 'used_amount',
}

TRACKED_FIELDS = [field for field, _label in FORM_FIELDS]


def _clean(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return value


def _decimal_or_none(value):
    value = _clean(value)
    if value == '':
        return None
    if isinstance(value, str):
        value = value.replace(',', '').replace('$', '').strip()
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _payload_from_post(post):
    payload = {}
    for field, _label in FORM_FIELDS:
        if field in ('budget_2026', 'used_amount'):
            payload[field] = _decimal_or_none(post.get(field))
        else:
            payload[field] = (post.get(field) or '').strip()
    return payload


def _snapshot(item):
    if item is None:
        return None
    data = {}
    for field in TRACKED_FIELDS:
        value = getattr(item, field)
        data[field] = str(value) if isinstance(value, Decimal) else value
    return data


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _client_mac(ip_address):
    if not ip_address:
        return ''
    commands = [
        ['ip', 'neigh', 'show', ip_address],
        ['arp', '-n', ip_address],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=2)
        except Exception:
            continue
        match = re.search(r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', result.stdout)
        if match:
            return match.group(1).lower()
    return ''


def _log_change(request, action, item=None, before=None, after=None):
    ip_address = _client_ip(request)
    user = request.user if request.user.is_authenticated else None
    BudgetChangeLog.objects.create(
        budget_item=item,
        action=action,
        before_data=before,
        after_data=after,
        changed_by=user,
        changed_by_code=getattr(user, 'username', '') if user else '',
        ip_address=ip_address or None,
        mac_address=_client_mac(ip_address),
    )


def _sheet_for_import(workbook):
    if '合併資料' in workbook.sheetnames:
        return workbook['合併資料']
    return workbook.active


def _header_map(sheet):
    mapping = {}
    for col in range(1, sheet.max_column + 1):
        header = _clean(sheet.cell(1, col).value)
        if header in HEADER_ALIASES:
            mapping[HEADER_ALIASES[header]] = col
    required = [field for field, _label in FIELDS]
    if all(field in mapping for field in required):
        return mapping

    # Prepared 2026 budget sheet: A=部門牧區, B-J=target fields, K=used amount.
    fallback = {field: index for (field, _label), index in zip(FIELDS, range(2, 11))}
    fallback['used_amount'] = 11
    return fallback


def import_budget_items(file_obj, request=None):
    workbook = load_workbook(file_obj, data_only=True)
    sheet = _sheet_for_import(workbook)
    mapping = _header_map(sheet)
    items = []
    for row_idx in range(2, sheet.max_row + 1):
        row_data = {}
        for field, _label in FORM_FIELDS:
            col = mapping.get(field)
            value = sheet.cell(row_idx, col).value if col else None
            row_data[field] = _decimal_or_none(value) if field in ('budget_2026', 'used_amount') else str(_clean(value) or '')
        if not any(row_data[field] not in ('', None) for field in TRACKED_FIELDS if field not in ('budget_2026', 'used_amount')) and row_data['budget_2026'] is None and row_data['used_amount'] is None:
            continue
        items.append(BudgetItem(**row_data))

    with transaction.atomic():
        before_count = BudgetItem.objects.count()
        BudgetItem.objects.all().delete()
        if items:
            BudgetItem.objects.bulk_create(items, batch_size=500)
        if request is not None:
            _log_change(request, 'import', None, {'count': before_count}, {'count': len(items)})
    return len(items)


@login_required
def budget_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            item = BudgetItem.objects.create(**_payload_from_post(request.POST))
            _log_change(request, 'create', item, None, _snapshot(item))
            return redirect('budget-list')
        if action == 'update':
            item = get_object_or_404(BudgetItem, pk=request.POST.get('item_id'))
            before = _snapshot(item)
            for field, value in _payload_from_post(request.POST).items():
                setattr(item, field, value)
            item.save()
            _log_change(request, 'update', item, before, _snapshot(item))
            return redirect(request.POST.get('next') or 'budget-list')
        if action == 'import' and request.FILES.get('file'):
            import_budget_items(request.FILES['file'], request)
            return redirect('budget-list')
        return redirect('budget-list')

    query = (request.GET.get('q') or '').strip()
    items = BudgetItem.objects.all()
    if query:
        items = items.filter(
            Q(budget_code__icontains=query) |
            Q(category__icontains=query) |
            Q(ministry__icontains=query) |
            Q(lead_pastor__icontains=query) |
            Q(accounting_subject__icontains=query)
        )
    items = items.order_by('id')
    page_obj = Paginator(items, 50).get_page(request.GET.get('page'))
    logs = BudgetChangeLog.objects.select_related('changed_by', 'budget_item').order_by('-created_at', '-id')[:200]
    return render(request, 'budget/budget_list.html', {
        'fields': FIELDS,
        'form_fields': FORM_FIELDS,
        'page_obj': page_obj,
        'query': query,
        'total_count': items.count(),
        'logs': logs,
    })


@login_required
def budget_edit(request, pk):
    item = get_object_or_404(BudgetItem, pk=pk)
    if request.method == 'POST':
        before = _snapshot(item)
        for field, value in _payload_from_post(request.POST).items():
            setattr(item, field, value)
        item.save()
        _log_change(request, 'update', item, before, _snapshot(item))
    return redirect('budget-list')


@login_required
def budget_delete(request, pk):
    item = get_object_or_404(BudgetItem, pk=pk)
    if request.method == 'POST':
        before = _snapshot(item)
        _log_change(request, 'delete', item, before, None)
        item.delete()
    return redirect('budget-list')


@login_required
def budget_export(request):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '預算表維護'
    sheet.append([label for _field, label in FORM_FIELDS] + ['使用比例', '餘額'])
    for item in BudgetItem.objects.order_by('id'):
        ratio = item.usage_ratio
        sheet.append([
            item.category,
            item.budget_code,
            item.ministry,
            item.annual_goal,
            item.strategy_plan,
            item.activity_budget,
            item.lead_pastor,
            float(item.budget_2026) if item.budget_2026 is not None else None,
            float(item.used_amount) if item.used_amount is not None else None,
            item.accounting_subject,
            float(ratio) / 100 if ratio is not None else None,
            float(item.balance),
        ])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="budget_items_2026.xlsx"'
    return response
