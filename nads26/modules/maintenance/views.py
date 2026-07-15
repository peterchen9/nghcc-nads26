import mimetypes
import time
from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    MaintenanceCategoryForm,
    MaintenanceLocationForm,
    MaintenanceRecordForm,
    MaintenanceVendorForm,
    PublicMaintenanceReportForm,
)
from .models import (
    MaintenanceAttachment,
    MaintenanceCategory,
    MaintenanceLocation,
    MaintenanceRecord,
    MaintenanceVendor,
)


INCOMPLETE_STATUSES = (
    MaintenanceRecord.Status.PENDING,
    MaintenanceRecord.Status.IN_PROGRESS,
    MaintenanceRecord.Status.WAITING_QUOTE,
    MaintenanceRecord.Status.WAITING_CONSTRUCTION,
)

UPLOAD_FIELD_TYPES = (
    ('onsite_file', MaintenanceAttachment.Type.ONSITE),
    ('quote_file', MaintenanceAttachment.Type.QUOTE),
    ('receipt_file', MaintenanceAttachment.Type.RECEIPT),
)


def _save_uploads(record, form):
    for field_name, attachment_type in UPLOAD_FIELD_TYPES:
        uploaded = form.cleaned_data.get(field_name)
        if not uploaded:
            continue
        MaintenanceAttachment.objects.create(
            record=record,
            type=attachment_type,
            file=uploaded,
            original_name=Path(uploaded.name).name,
            mime_type=getattr(uploaded, 'content_type', '') or mimetypes.guess_type(uploaded.name)[0] or '',
        )


def _record_queryset():
    return MaintenanceRecord.objects.select_related('category', 'location', 'vendor', 'created_by').prefetch_related('attachments')


@login_required
def dashboard(request):
    today = timezone.localdate()
    records = MaintenanceRecord.objects.all()
    current_year = records.filter(maintenance_date__year=today.year)
    stats = {
        'total': records.count(),
        'month': records.filter(maintenance_date__year=today.year, maintenance_date__month=today.month).count(),
        'incomplete': records.filter(status__in=INCOMPLETE_STATUSES).count(),
        'year_cost': current_year.aggregate(
            total=Coalesce(Sum('cost'), Value(Decimal('0')), output_field=DecimalField(max_digits=12, decimal_places=2))
        )['total'],
    }
    recent = _record_queryset()[:8]
    return render(request, 'maintenance/dashboard.html', {'stats': stats, 'recent_records': recent})


@login_required
def record_list(request):
    records = _record_queryset()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    category_id = request.GET.get('category', '').strip()
    record_type = request.GET.get('type', '').strip()
    status = request.GET.get('status', '').strip()
    vendor_id = request.GET.get('vendor', '').strip()
    location_id = request.GET.get('location', '').strip()
    keyword = request.GET.get('keyword', '').strip()

    if start_date:
        records = records.filter(maintenance_date__gte=start_date)
    if end_date:
        records = records.filter(maintenance_date__lte=end_date)
    if category_id.isdigit():
        records = records.filter(category_id=int(category_id))
    if record_type in MaintenanceRecord.Type.values:
        records = records.filter(type=record_type)
    if status in MaintenanceRecord.Status.values:
        records = records.filter(status=status)
    if vendor_id.isdigit():
        records = records.filter(vendor_id=int(vendor_id))
    if location_id.isdigit():
        records = records.filter(location_id=int(location_id))
    if keyword:
        records = records.filter(
            Q(issue__icontains=keyword) | Q(result__icontains=keyword) |
            Q(notes__icontains=keyword) | Q(handler__icontains=keyword) |
            Q(vendor_representative__icontains=keyword)
        )

    paginator = Paginator(records, 30)
    page = paginator.get_page(request.GET.get('page'))
    context = {
        'page': page,
        'categories': MaintenanceCategory.objects.all(),
        'locations': MaintenanceLocation.objects.all(),
        'vendors': MaintenanceVendor.objects.all(),
        'type_choices': MaintenanceRecord.Type.choices,
        'status_choices': MaintenanceRecord.Status.choices,
        'filters': request.GET,
    }
    return render(request, 'maintenance/record_list.html', context)


def _record_form_view(request, instance=None):
    form = MaintenanceRecordForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            record = form.save(commit=False)
            if not record.created_by_id:
                record.created_by = request.user
            record.save()
            _save_uploads(record, form)
        messages.success(request, '維護紀錄已儲存。')
        return redirect('maintenance:record-detail', pk=record.pk)
    return render(request, 'maintenance/record_form.html', {'form': form, 'record': instance})


@login_required
def record_create(request):
    return _record_form_view(request)


@login_required
def record_update(request, pk):
    return _record_form_view(request, get_object_or_404(MaintenanceRecord, pk=pk))


@login_required
def record_detail(request, pk):
    record = get_object_or_404(_record_queryset(), pk=pk)
    return render(request, 'maintenance/record_detail.html', {'record': record})


@login_required
@require_POST
def record_delete(request, pk):
    record = get_object_or_404(MaintenanceRecord.objects.prefetch_related('attachments'), pk=pk)
    files = [attachment.file for attachment in record.attachments.all() if attachment.file]
    with transaction.atomic():
        record.delete()
    for stored_file in files:
        stored_file.delete(save=False)
    messages.success(request, '維護紀錄已刪除。')
    return redirect('maintenance:record-list')


@login_required
@require_POST
def attachment_delete(request, pk):
    attachment = get_object_or_404(MaintenanceAttachment, pk=pk)
    record_id = attachment.record_id
    stored_file = attachment.file
    attachment.delete()
    if stored_file:
        stored_file.delete(save=False)
    messages.success(request, '附件已刪除。')
    return redirect('maintenance:record-detail', pk=record_id)


@login_required
def vendor_list(request):
    editing = None
    edit_id = request.GET.get('edit', '')
    if edit_id.isdigit():
        editing = get_object_or_404(MaintenanceVendor, pk=int(edit_id))
    form = MaintenanceVendorForm(request.POST or None, instance=editing)
    if request.method == 'POST' and form.is_valid():
        vendor = form.save()
        messages.success(request, f'廠商「{vendor.name}」已儲存。')
        return redirect('maintenance:vendor-list')
    return render(request, 'maintenance/vendor_list.html', {
        'form': form, 'editing': editing, 'vendors': MaintenanceVendor.objects.all(),
    })


@login_required
def category_list(request):
    editing = None
    edit_id = request.GET.get('edit', '')
    if edit_id.isdigit():
        editing = get_object_or_404(MaintenanceCategory, pk=int(edit_id))
    form = MaintenanceCategoryForm(request.POST or None, instance=editing)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'分類「{item.name}」已儲存。')
        return redirect('maintenance:category-list')
    return render(request, 'maintenance/category_list.html', {
        'form': form, 'editing': editing, 'categories': MaintenanceCategory.objects.annotate(record_count=Count('records')),
    })


@login_required
def location_list(request):
    editing = None
    edit_id = request.GET.get('edit', '')
    if edit_id.isdigit():
        editing = get_object_or_404(MaintenanceLocation, pk=int(edit_id))
    form = MaintenanceLocationForm(request.POST or None, instance=editing)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'地點「{item.name}」已儲存。')
        return redirect('maintenance:location-list')
    return render(request, 'maintenance/location_list.html', {
        'form': form, 'editing': editing, 'locations': MaintenanceLocation.objects.annotate(record_count=Count('records')),
    })


@login_required
def statistics(request):
    records = MaintenanceRecord.objects.all()
    by_month = records.annotate(month=TruncMonth('maintenance_date')).values('month').annotate(
        count=Count('id'), cost=Coalesce(Sum('cost'), Value(Decimal('0')), output_field=DecimalField(max_digits=12, decimal_places=2)),
    ).order_by('-month')[:24]
    by_category = records.values('category__name').annotate(
        count=Count('id'), cost=Coalesce(Sum('cost'), Value(Decimal('0')), output_field=DecimalField(max_digits=12, decimal_places=2)),
    ).order_by('-cost', '-count')
    by_vendor = records.values('vendor__name').annotate(
        count=Count('id'), cost=Coalesce(Sum('cost'), Value(Decimal('0')), output_field=DecimalField(max_digits=12, decimal_places=2)),
    ).order_by('-cost', '-count')
    return render(request, 'maintenance/statistics.html', {
        'by_month': by_month, 'by_category': by_category, 'by_vendor': by_vendor,
    })


@login_required
def unfinished(request):
    records = _record_queryset().filter(status__in=INCOMPLETE_STATUSES)
    return render(request, 'maintenance/unfinished.html', {'records': records})


def public_report(request):
    initial = {'maintenance_date': timezone.localdate(), 'type': MaintenanceRecord.Type.GENERAL}
    form = PublicMaintenanceReportForm(request.POST or None, request.FILES or None, initial=initial)
    submitted = request.GET.get('submitted') == '1'
    if request.method == 'POST':
        last_submit = float(request.session.get('maintenance_public_submit_at', 0) or 0)
        if time.time() - last_submit < 20:
            return HttpResponseBadRequest('請稍候再送出新的回報。')
        if form.is_valid():
            with transaction.atomic():
                record = form.save(commit=False)
                record.status = MaintenanceRecord.Status.PENDING
                record.cost = Decimal('0')
                record.notes = '由公開維護回報連結送出'
                record.save()
                uploaded = form.cleaned_data.get('onsite_file')
                if uploaded:
                    MaintenanceAttachment.objects.create(
                        record=record,
                        type=MaintenanceAttachment.Type.ONSITE,
                        file=uploaded,
                        original_name=Path(uploaded.name).name,
                        mime_type=getattr(uploaded, 'content_type', '') or '',
                    )
            request.session['maintenance_public_submit_at'] = time.time()
            return redirect(f"{reverse('maintenance_public:report')}?submitted=1")
    return render(request, 'maintenance/public_report.html', {'form': form, 'submitted': submitted})
