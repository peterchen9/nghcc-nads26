from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Fund, FundBalance, Fellowship, FellowshipBalance


@login_required
def fund_fellowship_dashboard(request):
    # Find all months that have balance data
    fund_months = list(FundBalance.objects.order_by('-month').values_list('month', flat=True).distinct())
    fellowship_months = list(FellowshipBalance.objects.order_by('-month').values_list('month', flat=True).distinct())
    all_months_set = set(fund_months + fellowship_months)
    all_months = sorted(list(all_months_set), reverse=True)

    available_months = []
    for m in all_months:
        m_str = m.strftime('%Y-%m')
        if m_str not in available_months:
            available_months.append(m_str)

    # Determine default/selected month
    latest_month = available_months[0] if available_months else timezone.now().strftime('%Y-%m')
    selected_month_str = request.GET.get('month', latest_month)

    try:
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()
    except ValueError:
        selected_month_str = latest_month
        selected_date = datetime.strptime(latest_month, '%Y-%m').date() if available_months else date.today().replace(day=1)

    # Get balances for the selected month
    fund_balances = FundBalance.objects.filter(month=selected_date).select_related('fund').order_by('fund__order', 'fund__id')
    fellowship_balances = FellowshipBalance.objects.filter(month=selected_date).select_related('fellowship').order_by('fellowship__order', 'fellowship__id')

    # Total balances
    total_fund_balance = sum(fb.balance for fb in fund_balances)
    total_fellowship_balance = sum(fb.balance for fb in fellowship_balances)

    # Prepare Fund Trend Chart Data (past 36 months)
    fund_trend_qs = list(FundBalance.objects.values('month').annotate(total_balance=Sum('balance')).order_by('month'))[-36:]
    fund_trend_labels = [item['month'].strftime('%Y-%m') for item in fund_trend_qs]
    fund_trend_total_data = [float(item['total_balance']) for item in fund_trend_qs]

    active_funds = list(Fund.objects.filter(is_active=True).order_by('order', 'id'))
    fund_cat_trends = {}
    for fund in active_funds:
        fund_cat_trends[fund.name] = [0.0] * len(fund_trend_labels)

    for i, t_label in enumerate(fund_trend_labels):
        m_date = datetime.strptime(t_label, '%Y-%m').date()
        m_balances = FundBalance.objects.filter(month=m_date).select_related('fund')
        for b in m_balances:
            name = b.fund.name
            if name in fund_cat_trends:
                fund_cat_trends[name][i] += float(b.balance)

    # Prepare Fellowship Trend Chart Data (past 36 months)
    fellowship_trend_qs = list(FellowshipBalance.objects.values('month').annotate(total_balance=Sum('balance')).order_by('month'))[-36:]
    fellowship_trend_labels = [item['month'].strftime('%Y-%m') for item in fellowship_trend_qs]
    fellowship_trend_total_data = [float(item['total_balance']) for item in fellowship_trend_qs]

    active_fellowships = list(Fellowship.objects.filter(is_active=True).order_by('order', 'id'))
    fellowship_cat_trends = {}
    for fs in active_fellowships:
        fellowship_cat_trends[fs.name] = [0.0] * len(fellowship_trend_labels)

    for i, t_label in enumerate(fellowship_trend_labels):
        m_date = datetime.strptime(t_label, '%Y-%m').date()
        m_balances = FellowshipBalance.objects.filter(month=m_date).select_related('fellowship')
        for b in m_balances:
            name = b.fellowship.name
            if name in fellowship_cat_trends:
                fellowship_cat_trends[name][i] += float(b.balance)

    context = {
        'available_months': available_months,
        'selected_month': selected_month_str,
        'fund_balances': fund_balances,
        'fellowship_balances': fellowship_balances,
        'total_fund_balance': total_fund_balance,
        'total_fellowship_balance': total_fellowship_balance,
        # Fund Trends
        'fund_trend_labels': fund_trend_labels,
        'fund_trend_total_data': fund_trend_total_data,
        'fund_cat_trends': fund_cat_trends,
        'funds_list': [f.name for f in active_funds],
        # Fellowship Trends
        'fellowship_trend_labels': fellowship_trend_labels,
        'fellowship_trend_total_data': fellowship_trend_total_data,
        'fellowship_cat_trends': fellowship_cat_trends,
        'fellowships_list': [f.name for f in active_fellowships],
    }
    return render(request, 'budget/fund_fellowship_dashboard.html', context)


@login_required
def manage_funds(request):
    selected_month_str = request.POST.get('month') or request.GET.get('month') or timezone.now().strftime('%Y-%m')
    try:
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()
    except ValueError:
        selected_month_str = timezone.now().strftime('%Y-%m')
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()

    funds = Fund.objects.filter(is_active=True).order_by('order', 'id')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_balances':
            with transaction.atomic():
                for fund in funds:
                    input_name = f"balance_{fund.id}"
                    val = request.POST.get(input_name)
                    if val is not None and val.strip() != '':
                        try:
                            balance_dec = Decimal(val.replace(',', '').strip())
                            FundBalance.objects.update_or_create(
                                fund=fund,
                                month=selected_date,
                                defaults={'balance': balance_dec}
                            )
                        except (InvalidOperation, ValueError):
                            pass
                    else:
                        FundBalance.objects.filter(fund=fund, month=selected_date).delete()
            return redirect(f'/finance/fund-fellowship-balances/?month={selected_month_str}')

        elif action == 'add_fund':
            name = request.POST.get('name', '').strip()
            note = request.POST.get('note', '').strip()
            if name:
                max_order = Fund.objects.aggregate(max_order=Sum('order'))['max_order'] or 0
                Fund.objects.create(
                    name=name,
                    note=note,
                    order=max_order + 1
                )
            return redirect(f'/finance/fund-fellowship-balances/manage-funds/?month={selected_month_str}')

        elif action == 'update_fund':
            fund_id = request.POST.get('fund_id')
            fund = get_object_or_404(Fund, pk=fund_id)
            name = request.POST.get('name', '').strip()
            note = request.POST.get('note', '').strip()
            if name:
                fund.name = name
                fund.note = note
                fund.save()
            return redirect(f'/finance/fund-fellowship-balances/manage-funds/?month={selected_month_str}')

        elif action == 'delete_fund':
            fund_id = request.POST.get('fund_id')
            fund = get_object_or_404(Fund, pk=fund_id)
            fund.delete()
            return redirect(f'/finance/fund-fellowship-balances/manage-funds/?month={selected_month_str}')

    # Fetch existing balances for this month
    existing_balances = {b.fund_id: b.balance for b in FundBalance.objects.filter(month=selected_date)}

    # Helper: fetch previous month's balances to use as placeholders/defaults
    if selected_date.month == 1:
        prev_month_date = date(selected_date.year - 1, 12, 1)
    else:
        prev_month_date = date(selected_date.year, selected_date.month - 1, 1)
    prev_balances = {b.fund_id: b.balance for b in FundBalance.objects.filter(month=prev_month_date)}

    form_data = []
    for fund in funds:
        curr_val = existing_balances.get(fund.id)
        prev_val = prev_balances.get(fund.id)
        form_data.append({
            'fund': fund,
            'value': curr_val if curr_val is not None else '',
            'placeholder': prev_val if prev_val is not None else Decimal('0'),
        })

    context = {
        'selected_month': selected_month_str,
        'form_data': form_data,
    }
    return render(request, 'budget/manage_funds.html', context)


@login_required
def manage_fellowships(request):
    selected_month_str = request.POST.get('month') or request.GET.get('month') or timezone.now().strftime('%Y-%m')
    try:
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()
    except ValueError:
        selected_month_str = timezone.now().strftime('%Y-%m')
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()

    fellowships = Fellowship.objects.filter(is_active=True).order_by('order', 'id')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_balances':
            with transaction.atomic():
                for fs in fellowships:
                    input_name = f"balance_{fs.id}"
                    val = request.POST.get(input_name)
                    if val is not None and val.strip() != '':
                        try:
                            balance_dec = Decimal(val.replace(',', '').strip())
                            FellowshipBalance.objects.update_or_create(
                                fellowship=fs,
                                month=selected_date,
                                defaults={'balance': balance_dec}
                            )
                        except (InvalidOperation, ValueError):
                            pass
                    else:
                        FellowshipBalance.objects.filter(fellowship=fs, month=selected_date).delete()
            return redirect(f'/finance/fund-fellowship-balances/?month={selected_month_str}')

        elif action == 'add_fellowship':
            name = request.POST.get('name', '').strip()
            note = request.POST.get('note', '').strip()
            if name:
                max_order = Fellowship.objects.aggregate(max_order=Sum('order'))['max_order'] or 0
                Fellowship.objects.create(
                    name=name,
                    note=note,
                    order=max_order + 1
                )
            return redirect(f'/finance/fund-fellowship-balances/manage-fellowships/?month={selected_month_str}')

        elif action == 'update_fellowship':
            fellowship_id = request.POST.get('fellowship_id')
            fellowship = get_object_or_404(Fellowship, pk=fellowship_id)
            name = request.POST.get('name', '').strip()
            note = request.POST.get('note', '').strip()
            if name:
                fellowship.name = name
                fellowship.note = note
                fellowship.save()
            return redirect(f'/finance/fund-fellowship-balances/manage-fellowships/?month={selected_month_str}')

        elif action == 'delete_fellowship':
            fellowship_id = request.POST.get('fellowship_id')
            fellowship = get_object_or_404(Fellowship, pk=fellowship_id)
            fellowship.delete()
            return redirect(f'/finance/fund-fellowship-balances/manage-fellowships/?month={selected_month_str}')

    # Fetch existing balances for this month
    existing_balances = {b.fellowship_id: b.balance for b in FellowshipBalance.objects.filter(month=selected_date)}

    # Helper: fetch previous month's balances to use as placeholders/defaults
    if selected_date.month == 1:
        prev_month_date = date(selected_date.year - 1, 12, 1)
    else:
        prev_month_date = date(selected_date.year, selected_date.month - 1, 1)
    prev_balances = {b.fellowship_id: b.balance for b in FellowshipBalance.objects.filter(month=prev_month_date)}

    form_data = []
    for fs in fellowships:
        curr_val = existing_balances.get(fs.id)
        prev_val = prev_balances.get(fs.id)
        form_data.append({
            'fellowship': fs,
            'value': curr_val if curr_val is not None else '',
            'placeholder': prev_val if prev_val is not None else Decimal('0'),
        })

    context = {
        'selected_month': selected_month_str,
        'form_data': form_data,
    }
    return render(request, 'budget/manage_fellowships.html', context)
