from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import MonthlyOffering, AnnualOffering


@login_required
def offering_dashboard(request):
    # Fetch monthly offerings (oldest first for charts, newest first for table)
    monthly_qs = MonthlyOffering.objects.order_by('month')
    monthly_offerings_newest = MonthlyOffering.objects.order_by('-month')

    # Prepare Monthly Trend Chart Data (past 36 months)
    monthly_trend_qs = list(monthly_qs)[-36:]
    monthly_labels = [m.month.strftime('%Y-%m') for m in monthly_trend_qs]
    
    # Categories list and mappings
    categories = [
        ('sunday', '主日奉獻'),
        ('pledge', '月定奉獻'),
        ('thanksgiving', '感恩奉獻'),
        ('building', '建築奉獻'),
        ('planting', '植堂奉獻'),
        ('designated', '指定奉獻'),
        ('mission', '宣教&大陸奉獻'),
        ('galilee', '加利利基金'),
        ('timothy', '提摩太基金'),
        ('kingdom', '國度基金'),
        ('venue', '場地費收入'),
    ]

    monthly_categories_data = {key: [] for key, _ in categories}
    monthly_totals = []
    
    for m in monthly_trend_qs:
        monthly_totals.append(float(m.total))
        for key, _ in categories:
            val = getattr(m, key) or Decimal('0.0')
            monthly_categories_data[key].append(float(val))

    # Prepare Annual Trend Chart Data (all historical years)
    annual_qs = AnnualOffering.objects.order_by('year')
    annual_labels = [a.year for a in annual_qs]
    annual_totals = [float(a.total) for a in annual_qs]
    
    # Prepare Annual Pledge People Trend
    annual_people_labels = []
    annual_people_data = []
    for a in annual_qs:
        if a.pledge_people_count is not None:
            annual_people_labels.append(a.year)
            annual_people_data.append(a.pledge_people_count)

    context = {
        'monthly_offerings': monthly_offerings_newest,
        'monthly_labels': monthly_labels,
        'monthly_totals': monthly_totals,
        'monthly_categories_data': monthly_categories_data,
        'categories': categories,
        
        'annual_labels': annual_labels,
        'annual_totals': annual_totals,
        
        'annual_people_labels': annual_people_labels,
        'annual_people_data': annual_people_data,
    }
    return render(request, 'budget/offering_dashboard.html', context)


@login_required
def get_monthly_offering_data(request):
    month_str = request.GET.get('month', '')
    if not month_str:
        return JsonResponse({'status': 'error', 'message': 'Month is required'}, status=400)
    
    try:
        dt = datetime.strptime(month_str, '%Y-%m').date()
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid month format'}, status=400)
        
    offering = MonthlyOffering.objects.filter(month=dt).first()
    if offering:
        data = {
            'pledge_people_count': offering.pledge_people_count or '',
            'sunday': float(offering.sunday),
            'pledge': float(offering.pledge),
            'thanksgiving': float(offering.thanksgiving),
            'building': float(offering.building),
            'planting': float(offering.planting),
            'designated': float(offering.designated),
            'mission': float(offering.mission),
            'galilee': float(offering.galilee),
            'timothy': float(offering.timothy),
            'kingdom': float(offering.kingdom),
            'venue': float(offering.venue),
            'total': float(offering.total),
        }
        return JsonResponse({'status': 'success', 'data': data})
    else:
        return JsonResponse({'status': 'not_found', 'data': {}})


@login_required
def save_monthly_offering(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    month_str = request.POST.get('month', '')
    if not month_str:
        return redirect('/finance/offering-statistics/?error=month_required')

    try:
        selected_date = datetime.strptime(month_str, '%Y-%m').date()
    except ValueError:
        return redirect('/finance/offering-statistics/?error=invalid_month_format')

    people_count_raw = request.POST.get('pledge_people_count')
    people_count = None
    if people_count_raw is not None and people_count_raw.strip() != '':
        try:
            people_count = int(people_count_raw)
        except ValueError:
            pass

    fields = [
        'sunday', 'pledge', 'thanksgiving', 'building', 'planting',
        'designated', 'mission', 'galilee', 'timothy', 'kingdom', 'venue'
    ]
    
    defaults = {'pledge_people_count': people_count}
    for f in fields:
        val = request.POST.get(f)
        if val is not None and val.strip() != '':
            try:
                dec_val = Decimal(val.replace(',', '').strip())
                defaults[f] = dec_val
            except (InvalidOperation, ValueError):
                defaults[f] = Decimal('0.0')
        else:
            defaults[f] = Decimal('0.0')

    with transaction.atomic():
        MonthlyOffering.objects.update_or_create(
            month=selected_date,
            defaults=defaults
        )

    return redirect('/finance/offering-statistics/?success=1')
