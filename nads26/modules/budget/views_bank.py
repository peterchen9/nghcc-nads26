from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import BankAccount, AccountBalance, TimeDeposit


@login_required
def bank_balances_dashboard(request):
    # Find all months that have balance data
    available_months_qs = AccountBalance.objects.order_by('-month').values_list('month', flat=True).distinct()
    available_months = []
    for m in available_months_qs:
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
    balances = AccountBalance.objects.filter(month=selected_date).select_related('account').order_by('account__order', 'account__id')

    # Prepare data for Chart 1: 各銀行帳戶結餘 (Latest balances)
    chart1_labels = []
    chart1_data = []
    total_bank_balance = Decimal('0')
    for b in balances:
        label = f"{b.account.category}"
        if b.account.bank:
            label += f" ({b.account.bank})"
        chart1_labels.append(label)
        chart1_data.append(float(b.balance))
        total_bank_balance += b.balance

    # Prepare data for Chart 2: 定期存單餘額 (Time deposits)
    time_deposits = TimeDeposit.objects.filter(is_active=True).order_by('order', 'id')
    # Group by category
    deposit_groups = {}
    total_deposit_balance = Decimal('0')
    for td in time_deposits:
        cat = td.category
        deposit_groups[cat] = deposit_groups.get(cat, Decimal('0')) + td.amount
        total_deposit_balance += td.amount

    chart2_labels = list(deposit_groups.keys())
    chart2_data = [float(amount) for amount in deposit_groups.values()]

    # Prepare data for Chart 3: 按月各帳戶餘額之趨勢 (Monthly trend)
    # Get total assets by month for the last 24 months with data, sorted chronologically
    monthly_trend_qs = AccountBalance.objects.values('month').annotate(total_balance=Sum('balance')).order_by('month')
    # Limit to past 36 records to avoid over-crowding, but show enough history
    monthly_trend_qs = list(monthly_trend_qs)[-36:]

    trend_labels = [item['month'].strftime('%Y-%m') for item in monthly_trend_qs]
    trend_data = [float(item['total_balance']) for item in monthly_trend_qs]

    # Category level trends for drill-down or multi-line comparison
    all_categories = list(BankAccount.objects.values_list('category', flat=True).distinct())
    cat_trends = {}
    for cat in all_categories:
        cat_trends[cat] = [0.0] * len(trend_labels)

    # Fetch monthly details for categories
    for i, t_label in enumerate(trend_labels):
        m_date = datetime.strptime(t_label, '%Y-%m').date()
        m_balances = AccountBalance.objects.filter(month=m_date).select_related('account')
        for b in m_balances:
            cat = b.account.category
            if cat in cat_trends:
                cat_trends[cat][i] += float(b.balance)

    context = {
        'available_months': available_months,
        'selected_month': selected_month_str,
        'balances': balances,
        'total_bank_balance': total_bank_balance,
        'total_deposit_balance': total_deposit_balance,
        'time_deposits': time_deposits,
        # Chart 1
        'chart1_labels': chart1_labels,
        'chart1_data': chart1_data,
        # Chart 2
        'chart2_labels': chart2_labels,
        'chart2_data': chart2_data,
        # Chart 3
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'cat_trends': cat_trends,
        'categories_list': all_categories,
    }
    return render(request, 'budget/bank_balances_dashboard.html', context)


@login_required
def manage_balances(request):
    selected_month_str = request.POST.get('month') or request.GET.get('month') or timezone.now().strftime('%Y-%m')
    try:
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()
    except ValueError:
        selected_month_str = timezone.now().strftime('%Y-%m')
        selected_date = datetime.strptime(selected_month_str, '%Y-%m').date()

    accounts = BankAccount.objects.filter(is_active=True).order_by('order', 'id')

    # Handle POST
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_balances':
            with transaction.atomic():
                for acc in accounts:
                    input_name = f"balance_{acc.id}"
                    val = request.POST.get(input_name)
                    if val is not None and val.strip() != '':
                        try:
                            balance_dec = Decimal(val.replace(',', '').strip())
                            AccountBalance.objects.update_or_create(
                                account=acc,
                                month=selected_date,
                                defaults={'balance': balance_dec}
                            )
                        except (InvalidOperation, ValueError):
                            pass
                    else:
                        # If left blank, delete the record for that month (or keep it None?)
                        AccountBalance.objects.filter(account=acc, month=selected_date).delete()
            return redirect(f'/finance/bank-balances/?month={selected_month_str}')

        elif action == 'add_account':
            category = request.POST.get('category', '').strip()
            bank = request.POST.get('bank', '').strip()
            account_no = request.POST.get('account_no', '').strip()
            if category:
                # Find max order to put it at the end
                max_order = BankAccount.objects.aggregate(max_order=Sum('order'))['max_order'] or 0
                BankAccount.objects.create(
                    category=category,
                    bank=bank,
                    account_no=account_no,
                    order=max_order + 1
                )
            return redirect(f'/finance/bank-balances/manage-balances/?month={selected_month_str}')

    # Fetch existing balances for this month
    existing_balances = {b.account_id: b.balance for b in AccountBalance.objects.filter(month=selected_date)}

    # Helper: fetch previous month's balances to use as placeholders/defaults
    import calendar
    prev_month_date = selected_date
    if selected_date.month == 1:
        prev_month_date = date(selected_date.year - 1, 12, 1)
    else:
        prev_month_date = date(selected_date.year, selected_date.month - 1, 1)
    prev_balances = {b.account_id: b.balance for b in AccountBalance.objects.filter(month=prev_month_date)}

    form_data = []
    for acc in accounts:
        curr_val = existing_balances.get(acc.id)
        prev_val = prev_balances.get(acc.id)
        form_data.append({
            'account': acc,
            'value': curr_val if curr_val is not None else '',
            'placeholder': prev_val if prev_val is not None else Decimal('0'),
        })

    context = {
        'selected_month': selected_month_str,
        'form_data': form_data,
    }
    return render(request, 'budget/manage_balances.html', context)


@login_required
def manage_deposits(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            category = request.POST.get('category', '').strip()
            duration = request.POST.get('duration', '').strip()
            period = request.POST.get('period', '').strip()
            deposit_type = request.POST.get('deposit_type', '').strip()
            deposit_no = request.POST.get('deposit_no', '').strip()

            rate_val = request.POST.get('interest_rate', '').strip()
            interest_rate = None
            if rate_val:
                try:
                    interest_rate = Decimal(rate_val)
                except (InvalidOperation, ValueError):
                    pass

            rate_type = request.POST.get('rate_type', '').strip()

            amount_val = request.POST.get('amount', '').strip()
            try:
                amount = Decimal(amount_val)
            except (InvalidOperation, ValueError):
                amount = Decimal('0')

            max_order = TimeDeposit.objects.filter(is_active=True).aggregate(max_order=Sum('order'))['max_order'] or 0
            TimeDeposit.objects.create(
                category=category,
                duration=duration,
                period=period,
                deposit_type=deposit_type,
                deposit_no=deposit_no,
                interest_rate=interest_rate,
                rate_type=rate_type,
                amount=amount,
                order=max_order + 1
            )

        elif action == 'update':
            dep_id = request.POST.get('deposit_id')
            deposit = get_object_or_404(TimeDeposit, pk=dep_id)
            deposit.category = request.POST.get('category', '').strip()
            deposit.duration = request.POST.get('duration', '').strip()
            deposit.period = request.POST.get('period', '').strip()
            deposit.deposit_type = request.POST.get('deposit_type', '').strip()
            deposit.deposit_no = request.POST.get('deposit_no', '').strip()

            rate_val = request.POST.get('interest_rate', '').strip()
            if rate_val:
                try:
                    deposit.interest_rate = Decimal(rate_val)
                except (InvalidOperation, ValueError):
                    deposit.interest_rate = None
            else:
                deposit.interest_rate = None

            deposit.rate_type = request.POST.get('rate_type', '').strip()

            amount_val = request.POST.get('amount', '').strip()
            try:
                deposit.amount = Decimal(amount_val)
            except (InvalidOperation, ValueError):
                pass

            deposit.save()

        elif action == 'delete':
            dep_id = request.POST.get('deposit_id')
            deposit = get_object_or_404(TimeDeposit, pk=dep_id)
            # Soft delete or hard delete, let's soft delete by setting active to False or just delete it
            deposit.delete()

        return redirect('/finance/bank-balances/manage-deposits/')

    deposits = TimeDeposit.objects.filter(is_active=True).order_by('order', 'id')
    categories = list(BankAccount.objects.values_list('category', flat=True).distinct())

    context = {
        'deposits': deposits,
        'categories': categories,
    }
    return render(request, 'budget/manage_deposits.html', context)
