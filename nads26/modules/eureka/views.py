import os
import re
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, HttpResponse
from django.conf import settings
from django.db.models import Q, Max, Count
from django.contrib import messages
from openpyxl import Workbook
from .models import Member, PastoralOverseer, PastoralSection, PastoralGroup

# 照片目錄路徑
PHOTO_FOLDER = os.path.join(settings.MEDIA_ROOT, 'eureka', 'photo')

VARIANT_MAP = {'峰': '峰峯', '峯': '峰峯', '群': '群羣', '羣': '群羣'}


def get_search_results(request):
    """處理搜尋邏輯，支援 7 個搜尋條件 (AND / OR / NOT)"""
    query = Member.objects.all()
    # 支援的欄位
    fields = ['name', 'name2', 'mobile1', 'car_number', 'section', 'address', 'note']
    and_filters, or_filters, not_filters = [], [], []

    has_active_filter = False

    for f in fields:
        val = request.GET.get(f'val_{f}', '').strip()
        logic = request.GET.get(f'l_{f}', 'A')

        if val:
            has_active_filter = True
            condition = None
            
            if f == 'name' or f == 'name2':
                # 相似字擴展搜尋
                char_conds = []
                for char in val:
                    variants = VARIANT_MAP.get(char, char)
                    char_q = Q()
                    for v in variants:
                        char_q |= Q(name__contains=v)
                    char_conds.append(char_q)
                
                if char_conds:
                    condition = char_conds[0]
                    for cond in char_conds[1:]:
                        condition &= cond
            elif f == 'mobile1':
                clean_val = re.sub(r'\D', '', val)
                if clean_val:
                    condition = Q(mobile1__contains=clean_val)
            elif f == 'car_number':
                condition = Q(car_number__icontains=val)
            elif f == 'section':
                if val not in ('全部分區', '全分區', '全部', ''):
                    condition = Q(section__icontains=val)
            else:
                condition = Q(**{f"{f}__contains": val})

            if condition is not None:
                if logic == 'A':
                    and_filters.append(condition)
                elif logic == 'O':
                    or_filters.append(condition)
                elif logic == 'X':
                    not_filters.append(condition)

    if not has_active_filter:
        return None

    c_and = Q()
    if and_filters:
        c_and = and_filters[0]
        for cond in and_filters[1:]:
            c_and &= cond

    c_or = Q()
    if or_filters:
        c_or = or_filters[0]
        for cond in or_filters[1:]:
            c_or |= cond

    combined_filter = Q()
    if and_filters and or_filters:
        combined_filter = c_and | c_or
    elif and_filters:
        combined_filter = c_and
    elif or_filters:
        combined_filter = c_or

    if not_filters:
        c_not = not_filters[0]
        for cond in not_filters[1:]:
            c_not |= cond
        if combined_filter:
            combined_filter &= ~c_not
        else:
            combined_filter = ~c_not

    if combined_filter:
        query = query.filter(combined_filter)
    else:
        query = Member.objects.none()
    
    # 限制最多回傳 100 筆，並回傳同家族成員的資訊以優化搜尋卡片效能
    return query.order_by('church_id')[:100]


@login_required
def serve_photo(request, filename):
    """安全提供人員照片，若檔案不存在則回傳 404"""
    safe_filename = os.path.basename(filename)
    photo_path = os.path.join(PHOTO_FOLDER, safe_filename)
    if os.path.exists(photo_path):
        return FileResponse(open(photo_path, 'rb'), content_type='image/jpeg')
    raise Http404("照片不存在")


@login_required
def eureka_view(request):
    """找人搜尋主頁"""
    results = get_search_results(request)
    
    # 獲取所有不為空的牧區，供下拉選單選擇
    sections = Member.objects.exclude(section='').values_list('section', flat=True).distinct().order_by('section')
    
    if results is not None:
        # 對於搜尋結果，我們可以直接獲取每個會員的家族成員，供卡片顯示
        for m in results:
            if m.family_id:
                m.family_list = Member.objects.filter(family_id=m.family_id).exclude(church_id=m.church_id)
            else:
                m.family_list = []
                
            # 解析卡片顯示出席率 (例如: "55 57 88 88 73 100")
            if m.percent_year:
                m.att_percent_display = m.percent_year.replace('-', ' ')
            else:
                m.att_percent_display = "無紀錄"
            
    return render(request, 'eureka/eureka.html', {
        'results': results,
        'sections': sections,
        'query_params': request.GET,
    })


@login_required
def melos_view(request, church_id):
    """人員資料編輯/詳情"""
    member = get_object_or_404(Member, church_id=church_id)
    if request.method == 'POST':
        member.name = request.POST.get('name', '').strip()
        member.mobile1 = request.POST.get('mobile1', '').strip()
        member.email1 = request.POST.get('email1', '').strip()
        member.address = request.POST.get('address', '').strip()
        member.note = request.POST.get('note', '').strip()
        member.section = request.POST.get('section', '').strip()
        member.family1 = request.POST.get('family1', '').strip()
        fid = request.POST.get('family_id', '').strip()
        member.family_id = int(fid) if fid else None
        member.save()
        
        # 重新導向回搜尋結果，帶上之前的 query parameters
        get_params = request.GET.urlencode()
        redirect_url = '/eureka/'
        if get_params:
            redirect_url += f'?{get_params}'
        return redirect(redirect_url)

    # 取得同家族成員
    family = []
    if member.family_id:
        family = Member.objects.filter(family_id=member.family_id).exclude(church_id=member.church_id)

    # 處理舊的出席紀錄換行符號（保留相容性）
    att_records = member.att_str.replace('$', '\n') if member.att_str else "無紀錄"

    # 首次打卡日期 fallback：若欄位為空則動態查詢本機的 checkin_records
    first_checkin = member.first_daka
    if not first_checkin:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT MIN(timestamp) FROM checkin_records WHERE church_id = %s", [member.church_id])
            row = cursor.fetchone()
            if row and row[0]:
                first_checkin = row[0].strftime('%Y-%m-%d')
            else:
                first_checkin = "-"

    # 解析年度出席率以供圖表使用 (55-57-88-88-73-100 -> 2021~2026 年)
    yearly_attendance = []
    if member.percent_year:
        rates = member.percent_year.split('-')
        years = [2021, 2022, 2023, 2024, 2025, 2026]
        for y, r in zip(years, rates):
            try:
                yearly_attendance.append({
                    'year': y,
                    'rate': int(r),
                })
            except ValueError:
                pass

    results = get_search_results(request)
    sections = Member.objects.exclude(section='').values_list('section', flat=True).distinct().order_by('section')
    
    if results is not None:
        for m_item in results:
            if m_item.family_id:
                m_item.family_list = Member.objects.filter(family_id=m_item.family_id).exclude(church_id=m_item.church_id)
            else:
                m_item.family_list = []
                
            if m_item.percent_year:
                m_item.att_percent_display = m_item.percent_year.replace('-', ' ')
            else:
                m_item.att_percent_display = "無紀錄"

    return render(request, 'eureka/eureka.html', {
        'results': results,
        'sections': sections,
        'query_params': request.GET,
        'show_modal': True,
        'm': member,
        'family': family,
        'att_records': att_records,
        'first_checkin': first_checkin,
        'yearly_attendance': yearly_attendance,
        'query_params_url': request.GET.urlencode(),
    })


@login_required
def neos_view(request):
    """新增人員"""
    if request.method == 'POST':
        church_id = request.POST.get('church_id')
        name = request.POST.get('name', '').strip()
        mobile1 = request.POST.get('mobile1', '').strip()
        email1 = request.POST.get('email1', '').strip()
        address = request.POST.get('address', '').strip()
        section = request.POST.get('section', '').strip()
        fid = request.POST.get('family_id', '').strip()
        family_id = int(fid) if fid else None

        new_m = Member.objects.create(
            church_id=church_id,
            name=name,
            mobile1=mobile1,
            email1=email1,
            address=address,
            section=section,
            family_id=family_id
        )
        return redirect('/eureka/')
    return render(request, 'eureka/neos.html')


@login_required
def pastoral_view(request):
    """牧區小組檢視"""
    # 統計數據
    total_members = Member.objects.count()
    sections_count = Member.objects.exclude(section='').values('section').distinct().count()
    groups_count = Member.objects.exclude(family1='').values('family1').distinct().count()
    
    # 區牧結構與資料庫動態資訊
    pastoral_structure = []
    overseers = PastoralOverseer.objects.all().order_by('id')
    for o in overseers:
        sections_list = []
        for s in o.sections.all().order_by('id'):
            sections_list.append({
                'id': s.id,
                'name': s.name,
                'leader1': s.leader,
                'leader2': s.counselor,
                'date': '',
                'status': '',
                'groups': [g.name for g in s.groups.all().order_by('id')]
            })
        pastoral_structure.append({
            'id': o.id,
            'overseer': o.name,
            'sections': sections_list,
            'section_count': len(sections_list),
            'group_count': sum(len(s['groups']) for s in sections_list)
        })
    
    # 1. 預先載入所有家族成員的對照表 (僅執行 1 次 DB 查詢)
    family_map = {}
    family_members_qs = Member.objects.exclude(family_id__isnull=True).only('church_id', 'name', 'family_id')
    for m in family_members_qs:
        if m.family_id not in family_map:
            family_map[m.family_id] = []
        family_map[m.family_id].append({'church_id': m.church_id, 'name': m.name})
        
    # 2. 獲取所有相關牧區的成員 (僅執行 1 次 DB 查詢)
    active_sections = []
    for cat in pastoral_structure:
        for sec in cat['sections']:
            active_sections.append(sec['name'])
            
    all_members = Member.objects.filter(section__in=active_sections).order_by('name')
    
    # 3. 在記憶體中進行分組與資料處理，避免 N+1 查詢
    members_by_section = {}
    for m in all_members:
        sec_name = m.section
        if sec_name not in members_by_section:
            members_by_section[sec_name] = []
        members_by_section[sec_name].append(m)
        
        # 填充家族成員資訊 (記憶體查詢)
        if m.family_id and m.family_id in family_map:
            m.family_list = [f for f in family_map[m.family_id] if f['church_id'] != m.church_id]
        else:
            m.family_list = []
            
        if m.percent_year:
            m.att_percent_display = m.percent_year.replace('-', ' ')
        else:
            m.att_percent_display = "無紀錄"
            
    # 獲取所有小組的資料庫屬性
    all_groups_dict = {g.name: g for g in PastoralGroup.objects.all()}
            
    # 4. 組裝結構資料
    for category in pastoral_structure:
        cat_member_count = 0
        cat_group_count = 0
        cat_section_count = len(category['sections'])
        
        for sec in category['sections']:
            sec_name = sec['name']
            sec_members = members_by_section.get(sec_name, [])
            sec['member_count'] = len(sec_members)
            cat_member_count += sec['member_count']
            
            # 分組 (小組)
            groups_dict = {g: [] for g in sec.get('groups', [])}
            for m in sec_members:
                g_name = m.family1
                if not g_name:
                    continue
                if g_name not in groups_dict:
                    groups_dict[g_name] = []
                groups_dict[g_name].append(m)
                
            sec['group_count'] = len(groups_dict)
            cat_group_count += sec['group_count']
            
            # 排序小組名稱
            sorted_groups = sorted(groups_dict.keys())
            sec['groups_data'] = []
            for g_name in sorted_groups:
                g_obj = all_groups_dict.get(g_name)
                sec['groups_data'].append({
                    'id': g_obj.id if g_obj else None,
                    'name': g_name,
                    'member_count': len(groups_dict[g_name]),
                    'members': groups_dict[g_name],
                    'meeting_time': g_obj.meeting_time if g_obj else '',
                    'location': g_obj.location if g_obj else '',
                    'target': g_obj.target if g_obj else '',
                    'topic': g_obj.topic if g_obj else '',
                    'photo_url': g_obj.photo.url if g_obj and g_obj.photo else ''
                })
                
        category['member_count'] = cat_member_count
        category['group_count'] = cat_group_count
        category['section_count'] = cat_section_count
        
    return render(request, 'eureka/pastoral.html', {
        'total_members': total_members,
        'sections_count': sections_count,
        'groups_count': groups_count,
        'pastoral_structure': pastoral_structure,
        'all_overseers': PastoralOverseer.objects.all().order_by('id')
    })


from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse

@login_required
@csrf_protect
def edit_overseer_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    overseer = get_object_or_404(PastoralOverseer, pk=pk)
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'message': '名字不能為空'}, status=400)
    
    overseer.name = name
    overseer.save()
    return JsonResponse({'success': True, 'message': '區牧修改成功'})


@login_required
@csrf_protect
def add_section_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    name = request.POST.get('name', '').strip()
    overseer_id = request.POST.get('overseer', '').strip()
    counselor = request.POST.get('counselor', '').strip()
    leader = request.POST.get('leader', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': '牧區名稱不能為空'}, status=400)
    if not overseer_id:
        return JsonResponse({'success': False, 'message': '請選擇區牧'}, status=400)
        
    try:
        overseer = PastoralOverseer.objects.get(pk=int(overseer_id))
    except (ValueError, PastoralOverseer.DoesNotExist):
        return JsonResponse({'success': False, 'message': '無效的區牧'}, status=400)
        
    if PastoralSection.objects.filter(name=name).exists():
        return JsonResponse({'success': False, 'message': '該牧區名稱已存在'}, status=400)
        
    section = PastoralSection.objects.create(
        name=name,
        overseer=overseer,
        counselor=counselor,
        leader=leader
    )
    
    return JsonResponse({'success': True, 'message': '牧區新增成功', 'id': section.id})


@login_required
@csrf_protect
def edit_section_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    section = get_object_or_404(PastoralSection, pk=pk)
    name = request.POST.get('name', '').strip()
    overseer_id = request.POST.get('overseer', '').strip()
    counselor = request.POST.get('counselor', '').strip()
    leader = request.POST.get('leader', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': '牧區名稱不能為空'}, status=400)
        
    old_name = section.name
    
    section.name = name
    if overseer_id:
        section.overseer_id = int(overseer_id)
    section.counselor = counselor
    section.leader = leader
    section.save()
    
    # Keep member section assignments in sync
    if old_name != name:
        Member.objects.filter(section=old_name).update(section=name)
        
    return JsonResponse({'success': True, 'message': '牧區修改成功'})


@login_required
@csrf_protect
def edit_group_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
        
    group = get_object_or_404(PastoralGroup, pk=pk)
    name = request.POST.get('name', '').strip()
    meeting_time = request.POST.get('meeting_time', '').strip()
    location = request.POST.get('location', '').strip()
    target = request.POST.get('target', '').strip()
    topic = request.POST.get('topic', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': '小組名稱不能為空'}, status=400)
        
    old_name = group.name
    
    group.name = name
    group.meeting_time = meeting_time
    group.location = location
    group.target = target
    group.topic = topic
    
    if 'photo' in request.FILES:
        photo_file = request.FILES['photo']
        group.photo = photo_file
        
    group.save()
    
    # Keep member group assignments in sync
    if old_name != name:
        Member.objects.filter(family1=old_name).update(family1=name)
        
    return JsonResponse({'success': True, 'message': '小組修改成功'})


@login_required
@csrf_protect
def add_group_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
        
    name = request.POST.get('name', '').strip()
    section_id = request.POST.get('section', '').strip()
    meeting_time = request.POST.get('meeting_time', '').strip()
    location = request.POST.get('location', '').strip()
    target = request.POST.get('target', '').strip()
    topic = request.POST.get('topic', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': '小組名稱不能為空'}, status=400)
    if not section_id:
        return JsonResponse({'success': False, 'message': '請選擇所屬牧區'}, status=400)
        
    try:
        section = PastoralSection.objects.get(pk=int(section_id))
    except (ValueError, PastoralSection.DoesNotExist):
        return JsonResponse({'success': False, 'message': '無效的牧區'}, status=400)
        
    if PastoralGroup.objects.filter(name=name).exists():
        return JsonResponse({'success': False, 'message': '該小組名稱已存在'}, status=400)
        
    photo_file = None
    if 'photo' in request.FILES:
        photo_file = request.FILES['photo']
        
    group = PastoralGroup.objects.create(
        name=name,
        section=section,
        meeting_time=meeting_time,
        location=location,
        target=target,
        topic=topic,
        photo=photo_file
    )
    
    return JsonResponse({'success': True, 'message': '小組新增成功', 'id': group.id})


@login_required
def group_members_api(request, pk):
    group = get_object_or_404(PastoralGroup, pk=pk)
    members = Member.objects.filter(family1=group.name).order_by('name').values('church_id', 'name')
    return JsonResponse({'success': True, 'members': list(members)})


@login_required
@csrf_protect
def add_group_member_api(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
        
    group = get_object_or_404(PastoralGroup, pk=pk)
    church_id = request.POST.get('church_id', '').strip()
    if not church_id:
        return JsonResponse({'success': False, 'message': 'Church ID cannot be empty'}, status=400)
        
    member = get_object_or_404(Member, church_id=int(church_id))
    
    member.family1 = group.name
    member.section = group.section.name
    member.save()
    
    return JsonResponse({'success': True, 'message': f'成功新增 {member.name} 到 {group.name}'})


@login_required
@csrf_protect
def remove_group_member_api(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
        
    group = get_object_or_404(PastoralGroup, pk=pk)
    church_id = request.POST.get('church_id', '').strip()
    if not church_id:
        return JsonResponse({'success': False, 'message': 'Church ID cannot be empty'}, status=400)
        
    member = get_object_or_404(Member, church_id=int(church_id))
    
    if member.family1 != group.name:
        return JsonResponse({'success': False, 'message': 'Member is not in this group'}, status=400)
        
    member.section = "未加入牧區"
    member.family1 = "未加入小組"
    member.save()
    
    return JsonResponse({'success': True, 'message': f'已將 {member.name} 移出小組，並歸入未加入牧區/未加入小組'})


@login_required
def unassigned_members_api(request):
    query = request.GET.get('q', '').strip()
    unassigned = Member.objects.filter(family1="未加入小組")
    if query:
        unassigned = unassigned.filter(name__icontains=query)
    
    results = unassigned.order_by('name')[:50].values('church_id', 'name')
    return JsonResponse({'success': True, 'members': list(results)})


@login_required
def add_view(request):
    """新朋友登記"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip().replace(" ", "")
        if not name:
            messages.error(request, '姓名為必填欄位')
            return redirect('eureka:add')
            
        max_id = Member.objects.aggregate(Max('church_id'))['church_id__max']
        new_church_id = (max_id or 0) + 1
        
        gender_val = request.POST.get('gender', '')
        gender = 'M' if gender_val == 'male' else ('F' if gender_val == 'female' else '')
        
        marriage_val = request.POST.get('marriage', '')
        marriage = 'm' if marriage_val == 'yes' else ('s' if marriage_val == 'no' else '')
        
        baptized_val = request.POST.get('baptized', '')
        baptized = 'y' if baptized_val == 'yes' else ('n' if baptized_val == 'no' else '')
        
        b_year = request.POST.get('b_year', '')
        b_month = request.POST.get('b_month', '')
        b_day = request.POST.get('b_day', '')
        birthday = None
        if b_year.isdigit() and b_month.isdigit() and b_day.isdigit():
            try:
                birthday = datetime.date(int(b_year) + 1911, int(b_month), int(b_day))
            except ValueError:
                pass
                
        emer_name = request.POST.get('emer_contact_name', '').strip()
        emer_phone = request.POST.get('emer_contact_phone', '').strip()
        emer_relation = request.POST.get('emer_contact_relation', '').strip()
        
        note = request.POST.get('note', '').strip()
        if emer_name or emer_phone or emer_relation:
            relation_map = {'dad': '爸爸', 'mom': '媽媽'}
            rel = relation_map.get(emer_relation, emer_relation)
            note += f"\n[緊急聯絡人: {emer_name} ({rel}) {emer_phone}]".strip()
            
        visitor_notes = []
        if request.POST.get('checkbox1') == 'on':
            visitor_notes.append('我不是基督徒，願進一步了解基督教')
        if request.POST.get('checkbox2') == 'on':
            visitor_notes.append('我尚未受洗，願參加慕道班明白真理')
        if request.POST.get('checkbox3') == 'on':
            visitor_notes.append('我是基督徒，因臨時需要而參加貴堂之聚會')
        if request.POST.get('checkbox4') == 'on':
            visitor_notes.append('我是基督徒，我目前還沒有固定參加哪一個教會')
        if request.POST.get('checkbox5') == 'on':
            visitor_notes.append('我是基督徒，今後可能經常參加貴堂之聚會')
            
        if visitor_notes:
            note += " (訪客資訊: " + "，".join(visitor_notes) + ")"
            
        def parse_roc_date(date_str):
            if not date_str:
                return datetime.date.today()
            try:
                parts = date_str.split('-')
                if len(parts) == 3:
                    return datetime.date(int(parts[0]) + 1911, int(parts[1]), int(parts[2]))
            except Exception:
                pass
            return datetime.date.today()
            
        join_date = parse_roc_date(request.POST.get('joindate', ''))
        dataindate = parse_roc_date(request.POST.get('dataindate', ''))
        
        new_m = Member.objects.create(
            church_id=new_church_id,
            name=name,
            gender=gender,
            marriage=marriage,
            birthday=birthday,
            phone_h=request.POST.get('home_phone', '').strip(),
            phone_o=request.POST.get('office_phone', '').strip(),
            mobile1=request.POST.get('mobile_phone', '').strip(),
            address=request.POST.get('home_address', '').strip(),
            email1=request.POST.get('e_mail', '').strip(),
            baptized=baptized,
            section='新朋友牧區',
            family1='新朋友',
            note=note,
            join_date=join_date,
            dataindate=dataindate,
            car_number=request.POST.get('reserved2', '').strip().upper(),
            line_id=request.POST.get('reserved3', '').strip(),
            presence=0
        )
        
        photo_file = request.FILES.get('photo')
        if photo_file:
            photo_dir = os.path.join(settings.MEDIA_ROOT, 'eureka', 'photo')
            os.makedirs(photo_dir, exist_ok=True)
            photo_path = os.path.join(photo_dir, f"{new_church_id}.jpg")
            with open(photo_path, 'wb+') as destination:
                for chunk in photo_file.chunks():
                    destination.write(chunk)
                    
        messages.success(request, f"成功新增新朋友: {name} (ID: {new_church_id})")
        return redirect('eureka:add')
        
    today = datetime.date.today()
    roc_today = f"{today.year - 1911}-{today.month}-{today.day}"
    return render(request, 'eureka/add.html', {'dataindate': roc_today})


@login_required
def download_add_view(request):
    """下載新朋友資料的 Excel 檔"""
    if request.method != 'POST':
        return redirect('eureka:add')
        
    date_str = request.POST.get('date', '').strip()
    if not date_str:
        messages.error(request, '請輸入日期')
        return redirect('eureka:add')
        
    try:
        query_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, '不正確的日期格式，請使用西元格式如 2013-11-10')
        return redirect('eureka:add')
        
    members = Member.objects.filter(section='新朋友牧區', family1='新朋友', dataindate=query_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "新朋友資料"
    
    headers = ["填卡日期", "姓名", "性別", "出生年日", "手機", "Email", "電話(H)", "電話(O)", "住址", "車號", "附註"]
    ws.append(headers)
    
    for m in members:
        b_str = ""
        if m.birthday:
            b_str = f"{m.birthday.year - 1911}.{m.birthday.month:02d}.{m.birthday.day:02d}"
            
        gender_display = '男' if m.gender == 'M' else ('女' if m.gender == 'F' else '')
        dataindate_str = m.dataindate.strftime('%Y-%m-%d') if m.dataindate else ''
        
        ws.append([
            dataindate_str,
            m.name,
            gender_display,
            b_str,
            m.mobile1,
            m.email1,
            m.phone_h,
            m.phone_o,
            m.address,
            m.car_number,
            m.note
        ])
        
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = f'attachment; filename=new_friends_{date_str}.xlsx'
    wb.save(response)
    return response


@login_required
def modify_view(request):
    """搜名單與管理介面"""
    results = get_search_results(request)
    key_word = request.GET.get('key_word', '').strip()
    
    if results is None:
        if key_word:
            results = Member.objects.filter(
                Q(name__contains=key_word) |
                Q(mobile1__contains=key_word) |
                Q(address__contains=key_word) |
                Q(note__contains=key_word) |
                Q(section__contains=key_word) |
                Q(family1__contains=key_word) |
                Q(car_number__contains=key_word) |
                Q(line_id__contains=key_word)
            ).order_by('church_id')[:100]
        else:
            results = []
            
    sections = Member.objects.exclude(section='').values_list('section', flat=True).distinct().order_by('section')
    
    return render(request, 'eureka/modify.html', {
        'people_list': results,
        'key_word': key_word,
        'result_count': len(results) if results else 0,
        'sections': sections,
        'query_params': request.GET,
    })


@login_required
def duplicates_view(request):
    """搜尋重複姓名"""
    duplicate_names = Member.objects.values('name').annotate(name_count=Count('name')).filter(name_count__gt=1)
    names = [item['name'] for item in duplicate_names]
    people_list = Member.objects.filter(name__in=names).order_by('name')
    sections = Member.objects.exclude(section='').values_list('section', flat=True).distinct().order_by('section')
    
    return render(request, 'eureka/modify.html', {
        'people_list': people_list,
        'key_word': '重複姓名',
        'result_count': len(people_list),
        'sections': sections,
        'query_params': request.GET,
    })


@login_required
def delete_view(request, church_id):
    """刪除成員"""
    member = get_object_or_404(Member, church_id=church_id)
    name = member.name
    
    photo_path = os.path.join(settings.MEDIA_ROOT, 'eureka', 'photo', f"{church_id}.jpg")
    if os.path.exists(photo_path):
        try:
            os.remove(photo_path)
        except Exception:
            pass
            
    member.delete()
    messages.success(request, f"成功刪除成員: {name} (ID: {church_id})")
    return redirect('eureka:modify')


@login_required
def download_all_view(request):
    """下載全部名單 Excel 檔"""
    members = Member.objects.all().order_by('church_id')
    
    wb = Workbook()
    ws = wb.active
    
    export_format = request.GET.get('format', '').strip()
    if export_format == 'simple':
        ws.title = "會員資料"
        headers = ["church_id", "name", "section", "family1"]
        ws.append(headers)
        
        for m in members:
            ws.append([
                m.church_id,
                m.name,
                m.section,
                m.family1
            ])
        filename = 'members_export_simple.xlsx'
    else:
        ws.title = "北門聖教會通訊錄"
        headers = ["姓名", "Email", "手機號碼", "室內電話", "住址", "牧區", "小組", "生日"]
        ws.append(headers)
        
        for m in members:
            birthday_str = m.birthday.strftime('%Y-%m-%d') if m.birthday else ''
            ws.append([
                m.name,
                m.email1,
                m.mobile1,
                m.phone_h,
                m.address,
                m.section,
                m.family1,
                birthday_str
            ])
        filename = 'church_address_book.xlsx'
        
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


from django.utils import timezone
from .models import StaffAttendance, StaffInfo, StaffShift
from django.core.management import call_command

@login_required
def attendance_view(request):
    """員工出勤狀態視圖"""
    # 支援手動同步
    if request.GET.get('sync') == 'true':
        try:
            call_command('sync_staff_attendance')
            messages.success(request, "已成功從考勤機擷取最新打卡資料！")
        except Exception as e:
            messages.error(request, f"從考勤機擷取資料失敗: {e}")
        return redirect('eureka:attendance')

    # 取得日期參數，預設為今日
    date_str = request.GET.get('date', '').strip()
    tz = timezone.get_current_timezone()
    now_local = datetime.datetime.now(tz)
    
    if date_str:
        try:
            selected_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.warning(request, "不正確的日期格式，已自動載入今天資料。")
            selected_date = now_local.date()
    else:
        selected_date = now_local.date()

    # 查詢所選日期的打卡記錄
    start_dt = timezone.make_aware(datetime.datetime.combine(selected_date, datetime.time.min), tz)
    end_dt = timezone.make_aware(datetime.datetime.combine(selected_date, datetime.time.max), tz)

    records = StaffAttendance.objects.filter(timestamp__range=(start_dt, end_dt)).order_by('timestamp')

    # 按員工編號分組
    from collections import OrderedDict
    grouped = OrderedDict()
    
    for r in records:
        emp_no = r.employee_no
        if emp_no not in grouped:
            grouped[emp_no] = {
                'employee_no': emp_no,
                'name': r.name,
                'card_no': r.card_no,
                'logs': [],
            }
        grouped[emp_no]['logs'].append(r)

    # 彙整每位員工的上下班時間
    attendance_list = []
    earliest_time = None
    latest_time = None

    for emp_no, info in grouped.items():
        logs = info['logs']
        first_in = logs[0].timestamp
        last_out = logs[-1].timestamp if len(logs) > 0 else first_in
        
        # 統計最晚與最早
        if earliest_time is None or first_in < earliest_time:
            earliest_time = first_in
        if latest_time is None or last_out > latest_time:
            latest_time = last_out

        info['first_in'] = first_in
        info['last_out'] = last_out
        info['count'] = len(logs)
        attendance_list.append(info)

    # 總體出勤統計卡
    stats = {
        'total_present': len(attendance_list),
        'earliest_clockin': earliest_time.strftime('%H:%M:%S') if earliest_time else '--:--:--',
        'latest_clockin': latest_time.strftime('%H:%M:%S') if latest_time else '--:--:--',
    }

    # 近30天出勤統計計算
    import json
    start_date = selected_date - datetime.timedelta(days=29)
    start_dt_30 = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min), tz)
    
    records_30 = StaffAttendance.objects.filter(timestamp__range=(start_dt_30, end_dt)).order_by('timestamp')

    # 按姓名與日期將打卡記錄分組，抓取每天最早的打卡時間 (只計 11:00 以前的打卡紀錄)
    earliest_records = {}
    for r in records_30:
        local_ts = r.timestamp.astimezone(tz)
        if local_ts.time() <= datetime.time(11, 0, 0):
            r_date = local_ts.date()
            key = (r.name, r_date)
            if key not in earliest_records:
                earliest_records[key] = local_ts

    # 取得所有在職同工，並只篩選身份為 P1, P2, W1, W2 的人，並 preload 班表關係以加速
    active_staff = StaffInfo.objects.select_related('shift').filter(
        is_active=True, 
        identity_code__in=['P1', 'P2', 'W1', 'W2']
    ).order_by('staff_id')
    
    # 取得 30 天內所有請假紀錄
    from django.db import connection
    leaves_map = {}
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT staff_name, staff_user, leave_date, day_part
            FROM staff_leave_entry
            WHERE leave_date >= %s AND leave_date <= %s
        ''', [start_date, selected_date])
        for row in cursor.fetchall():
            s_name, s_user, l_date, d_part = row
            leaves_map[(s_name, l_date, d_part)] = True
            if s_user:
                leaves_map[(s_user, l_date, d_part)] = True

    date_list = [start_date + datetime.timedelta(days=i) for i in range(30)]

    stats_30_days = []
    for staff in active_staff:
        ontime_count = 0
        late_count = 0
        nodata_count = 0
        
        daily_details = []
        for d in date_list:
            key = (staff.name, d)
            weekday_str = "週" + "一二三四五六日"[d.weekday()]
            
            # 檢查當天上午是否請假
            has_am_leave = leaves_map.get((staff.name, d, 'am')) or (staff.user and leaves_map.get((staff.user.username, d, 'am')))
            
            # 從班表判定是否為工作日及上班時間
            shift = staff.shift
            shift_start_time = None
            is_scheduled_workday = True
            
            if shift:
                day_attrs = ['mon_start', 'tue_start', 'wed_start', 'thu_start', 'fri_start', 'sat_start', 'sun_start']
                shift_start_time = getattr(shift, day_attrs[d.weekday()])
                if shift_start_time is None:
                    is_scheduled_workday = False
            else:
                # 預設排班規則：週日及週一至六皆為 08:30 (P1/P2 週五為 10:00)
                is_scheduled_workday = True
                if staff.identity_code in ['P1', 'P2'] and d.weekday() == 4:
                    shift_start_time = datetime.time(10, 0, 0)
                else:
                    shift_start_time = datetime.time(8, 30, 0)
            
            if key in earliest_records:
                local_ts = earliest_records[key]
                time_str = local_ts.strftime('%H:%M:%S')
                limit_time = shift_start_time or datetime.time(8, 30, 0)
                
                if local_ts.time() <= limit_time:
                    ontime_count += 1
                    status = '準時'
                    status_class = 'badge-success'
                else:
                    late_count += 1
                    status = '遲到'
                    status_class = 'badge-warning'
            else:
                time_str = '--:--:--'
                # 無打卡紀錄時，若是上午請假或班表休假日則為「休假」，否則為「未打卡」
                if has_am_leave or not is_scheduled_workday:
                    status = '休假'
                    status_class = 'badge-secondary'
                else:
                    nodata_count += 1
                    status = '未打卡'
                    status_class = 'badge-danger'
                
            daily_details.append({
                'date': d.strftime('%Y-%m-%d'),
                'weekday': weekday_str,
                'time': time_str,
                'status': status,
                'status_class': status_class,
            })
                
        stats_30_days.append({
            'employee_no': staff.employee_no or '--',
            'name': staff.name,
            'ontime_count': ontime_count,
            'late_count': late_count,
            'nodata_count': nodata_count,
            'daily_details_json': json.dumps(daily_details),
        })

    return render(request, 'eureka/attendance.html', {
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'attendance_list': attendance_list,
        'stats': stats,
        'raw_records': records,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'stats_30_days': stats_30_days,
    })


import calendar
from .models import StaffLeave, DailyDutyNote

@login_required
def vacation_view(request):
    """同工休假表視圖"""
    # 取得年月參數，預設為本月
    tz = timezone.get_current_timezone()
    now_local = datetime.datetime.now(tz)
    
    year_str = request.GET.get('year', '').strip()
    month_str = request.GET.get('month', '').strip()
    
    try:
        year = int(year_str) if year_str else now_local.year
        month = int(month_str) if month_str else now_local.month
        if not (1 <= month <= 12):
            raise ValueError()
    except ValueError:
        year = now_local.year
        month = now_local.month

    # 取得所有可用年份供選單選擇
    try:
        years_dates = StaffLeave.objects.dates('date', 'year')
        available_years = sorted(list(set(d.year for d in years_dates)), reverse=True)
    except Exception:
        available_years = []
    
    if not available_years:
        available_years = [2024, 2025, 2026]

    months = range(1, 13)

    # 取得本年/本月有休假記錄的同工名單 (若本年無記錄，則抓全部)
    staff_names = list(
        StaffLeave.objects.filter(date__year=year)
        .values_list('staff_name', flat=True)
        .distinct()
        .order_by('staff_name')
    )
    if not staff_names:
        staff_names = list(
            StaffLeave.objects.values_list('staff_name', flat=True)
            .distinct()
            .order_by('staff_name')
        )

    # 取得本月天數與每日詳情
    num_days = calendar.monthrange(year, month)[1]
    days_list = []
    
    # 預先查出本月所有休假與備註以提升效能
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, num_days)
    
    leaves_qs = StaffLeave.objects.filter(date__range=(start_date, end_date))
    notes_qs = DailyDutyNote.objects.filter(date__range=(start_date, end_date))
    
    leaves_by_date = {}
    for lv in leaves_qs:
        dt = lv.date
        if dt not in leaves_by_date:
            leaves_by_date[dt] = {}
        if lv.staff_name not in leaves_by_date[dt]:
            leaves_by_date[dt][lv.staff_name] = {'AM': '', 'PM': ''}
        leaves_by_date[dt][lv.staff_name][lv.time_slot] = lv.leave_type

    notes_by_date = {n.date: n.note for n in notes_qs}

    # 計算統計數據
    stats_by_staff = {
        name: {'休': 0.0, '特': 0.0, '補': 0.0, '公': 0.0, '其他': 0.0, '總計': 0.0}
        for name in staff_names
    }

    # 統計本月休假天數
    for lv in leaves_qs:
        name = lv.staff_name
        if name not in stats_by_staff:
            stats_by_staff[name] = {'休': 0.0, '特': 0.0, '補': 0.0, '公': 0.0, '其他': 0.0, '總計': 0.0}
            
        ltype = lv.leave_type.strip()
        if not ltype:
            continue
            
        if '休' in ltype and '特' not in ltype and '補' not in ltype and '公' not in ltype:
            key = '休'
        elif '特' in ltype:
            key = '特'
        elif '補' in ltype:
            key = '補'
        elif '公' in ltype:
            key = '公'
        else:
            key = '其他'
            
        stats_by_staff[name][key] += 0.5
        stats_by_staff[name]['總計'] += 0.5

    # 建立每日資料列表
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    for d in range(1, num_days + 1):
        curr_date = datetime.date(year, month, d)
        wday_name = weekday_names[curr_date.weekday()]
        is_weekend = curr_date.weekday() in (5, 6) # Sat or Sun
        note_text = notes_by_date.get(curr_date, "")
        
        day_leaves = []
        date_leaves = leaves_by_date.get(curr_date, {})
        for name in staff_names:
            day_leaves.append(date_leaves.get(name, {'AM': '', 'PM': ''}))

        days_list.append({
            'day': f"{d:02d}",
            'date': curr_date,
            'weekday_name': wday_name,
            'is_weekend': is_weekend,
            'note': note_text,
            'leaves': day_leaves,
        })

    # 將統計資訊轉成列表排序，依總休假天數倒序，若一樣則依姓名排序
    sorted_stats = []
    for name, st in stats_by_staff.items():
        sorted_stats.append({
            'name': name,
            'data': st
        })
    sorted_stats.sort(key=lambda x: (-x['data']['總計'], x['name']))

    return render(request, 'eureka/vacation.html', {
        'selected_year': year,
        'selected_month': month,
        'available_years': available_years,
        'months': months,
        'staff_names': staff_names,
        'days_list': days_list,
        'stats': sorted_stats,
    })


@login_required
def sync_vacation_view(request):
    """管理員手動觸發 Google Sheets 休假資料同步"""
    if not request.user.is_superuser:
        messages.error(request, "只有管理員可以同步休假資料。")
        return redirect('eureka:vacation')
        
    try:
        from django.core.management import call_command
        call_command('import_leave_records')
        messages.success(request, "已成功從 Google Sheets 擷取最新休假資料！")
    except Exception as e:
        messages.error(request, f"從 Google Sheets 擷取資料失敗: {e}")
        
    return redirect('eureka:vacation')


from .models import StaffInfo

@login_required
def staff_list_view(request):
    """同工基本資料與特休額度列表視圖"""
    can_view_staff = request.user.is_superuser or request.user.has_perm('eureka.view_staffinfo')
    can_add_staff = request.user.is_superuser or request.user.has_perm('eureka.add_staffinfo')
    can_edit_staff = request.user.is_superuser or request.user.has_perm('eureka.change_staffinfo')
    can_delete_staff = request.user.is_superuser or request.user.has_perm('eureka.delete_staffinfo')
    if not can_view_staff:
        messages.error(request, "只有管理員可以存取同工資料。")
        return redirect('home')

    query = request.GET.get('q', '').strip()
    staff_list = StaffInfo.objects.select_related('user', 'shift').all()

    if query:
        staff_list = staff_list.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(identity_code__icontains=query) |
            Q(employee_no__icontains=query) |
            Q(mobile__icontains=query) |
            Q(seat__icontains=query) |
            Q(locker_no__icontains=query) |
            Q(bank_branch__icontains=query) |
            Q(bank_account__icontains=query) |
            Q(user__username__icontains=query)
        )

    users = User.objects.filter(is_active=True).order_by('username')
    shifts = StaffShift.objects.all().order_by('shift_code')

    return render(request, 'eureka/staff_list.html', {
        'staff_list': staff_list,
        'query': query,
        'users': users,
        'shifts': shifts,
        'can_add_staff': can_add_staff,
        'can_edit_staff': can_edit_staff,
        'can_delete_staff': can_delete_staff,
    })


@login_required
def add_staff_view(request):
    """Create a staff record from the staff administration page."""
    if not (request.user.is_superuser or request.user.has_perm('eureka.add_staffinfo')):
        messages.error(request, "您沒有新增同工資料的權限。")
        return redirect('eureka:staff-list')

    if request.method != 'POST':
        return redirect('eureka:staff-list')

    try:
        staff_id = int(request.POST.get('staff_id', '').strip())
        if staff_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "同工編號必須是大於零的整數。")
        return redirect('eureka:staff-list')

    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, "姓名為必填欄位。")
        return redirect('eureka:staff-list')
    if StaffInfo.objects.filter(pk=staff_id).exists():
        messages.error(request, f"同工編號 {staff_id} 已存在。")
        return redirect('eureka:staff-list')

    try:
        user_id = request.POST.get('user_id', '').strip()
        shift_id = request.POST.get('shift_id', '').strip()
        onboard_date = request.POST.get('onboard_date', '').strip() or None
        try:
            annual_leave_quota = float(request.POST.get('annual_leave_quota', '0') or 0)
        except ValueError:
            annual_leave_quota = 0.0

        staff = StaffInfo.objects.create(
            staff_id=staff_id,
            name=name,
            identity_code=request.POST.get('identity_code', '').strip(),
            employee_no=request.POST.get('employee_no', '').strip(),
            mobile=request.POST.get('mobile', '').strip(),
            seat=request.POST.get('seat', '').strip(),
            locker_no=request.POST.get('locker_no', '').strip(),
            bank_branch=request.POST.get('bank_branch', '').strip(),
            bank_account=request.POST.get('bank_account', '').strip(),
            user_id=int(user_id) if user_id else None,
            shift_id=int(shift_id) if shift_id else None,
            annual_leave_quota=max(annual_leave_quota, 0.0),
            onboard_date=onboard_date,
            is_active=request.POST.get('is_active', 'true') == 'true',
            email=request.POST.get('email', '').strip(),
            cc_email=request.POST.get('cc_email', '').strip(),
        )
        messages.success(request, f"已新增同工：{staff.name}。")
    except Exception:
        messages.error(request, "新增同工資料失敗，請檢查帳號、班表及欄位格式。")

    return redirect('eureka:staff-list')


@login_required
def edit_staff_view(request, staff_id):
    """編輯同工資料"""
    if not (request.user.is_superuser or request.user.has_perm('eureka.change_staffinfo')):
        messages.error(request, "只有管理員可以修改同工資料。")
        return redirect('home')

    if request.method == 'POST':
        staff = get_object_or_404(StaffInfo, pk=staff_id)
        try:
            staff.name = request.POST.get('name', '').strip()
            staff.identity_code = request.POST.get('identity_code', '').strip()
            staff.email = request.POST.get('email', '').strip()
            staff.cc_email = request.POST.get('cc_email', '').strip()
            
            onboard_date_str = request.POST.get('onboard_date', '').strip()
            if onboard_date_str:
                staff.onboard_date = onboard_date_str
            else:
                staff.onboard_date = None
                
            staff.employee_no = request.POST.get('employee_no', '').strip()
            staff.mobile = request.POST.get('mobile', '').strip()
            staff.seat = request.POST.get('seat', '').strip()
            staff.locker_no = request.POST.get('locker_no', '').strip()
            staff.bank_branch = request.POST.get('bank_branch', '').strip()
            staff.bank_account = request.POST.get('bank_account', '').strip()
            user_id = request.POST.get('user_id', '').strip()
            staff.user_id = int(user_id) if user_id else None
            shift_id = request.POST.get('shift_id', '').strip()
            staff.shift_id = int(shift_id) if shift_id else None
            
            try:
                staff.annual_leave_quota = float(request.POST.get('annual_leave_quota', '0') or 0.0)
            except ValueError:
                staff.annual_leave_quota = 0.0
                
            staff.is_active = request.POST.get('is_active') == 'true'
            
            staff.save()
            messages.success(request, f"已成功更新同工 {staff.name} 的資料。")
        except Exception as e:
            messages.error(request, f"更新同工資料失敗: {e}")
            
    return redirect('eureka:staff-list')


@login_required
def delete_staff_view(request, staff_id):
    """刪除同工資料"""
    if not (request.user.is_superuser or request.user.has_perm('eureka.delete_staffinfo')):
        messages.error(request, "只有管理員可以刪除同工資料。")
        return redirect('eureka:staff-list')

    staff = get_object_or_404(StaffInfo, pk=staff_id)
    name = staff.name
    try:
        staff.delete()
        messages.success(request, f"已成功刪除同工 {name} 的資料。")
    except Exception as e:
        messages.error(request, f"刪除同工資料失敗: {e}")

    return redirect('eureka:staff-list')


@login_required
def seat_map_view(request):
    """辦公室座位配置圖視圖"""
    from .models import SeatMap, StaffInfo
    import json
    
    # Get or create default seat map
    seat_map, created = SeatMap.objects.get_or_create(
        name="預設座位圖",
        defaults={"layout_data": {"width": 1000, "height": 700, "elements": []}}
    )
    
    # Default layout if empty
    if not isinstance(seat_map.layout_data, dict) or not seat_map.layout_data:
        seat_map.layout_data = {"width": 1000, "height": 700, "elements": []}
        
    # Pre-populate mockup office layout if new/empty
    if created or not seat_map.layout_data.get("elements"):
        elements = []
        for i in range(1, 9):
            row = (i - 1) // 4
            col = (i - 1) % 4
            x = 150 + col * 200
            y = 150 + row * 220
            
            # Desk Element
            elements.append({
                "id": f"desk-{i}",
                "type": "desk",
                "x": x,
                "y": y,
                "w": 120,
                "h": 60,
                "label": f"辦公桌 {i}"
            })
            # Seat Element
            elements.append({
                "id": f"seat-{i}",
                "type": "seat",
                "x": x + 40,
                "y": y + 80,
                "w": 40,
                "h": 40,
                "seat_no": f"S{i:02d}",
                "staff_id": "",
                "staff_name": ""
            })
        
        # Room boundaries and facilities
        elements.append({
            "id": "door-1",
            "type": "door",
            "x": 50,
            "y": 50,
            "w": 80,
            "h": 10,
            "label": "辦公室大門"
        })
        elements.append({
            "id": "printer-1",
            "type": "printer",
            "x": 900,
            "y": 80,
            "w": 50,
            "h": 50,
            "label": "多功能事務機"
        })
        
        seat_map.layout_data["elements"] = elements
        seat_map.save()
        
    coworkers = StaffInfo.objects.filter(is_active=True).order_by('name')
    coworker_list = [
        {"staff_id": c.staff_id, "name": c.name, "employee_no": c.employee_no, "seat": c.seat}
        for c in coworkers
    ]
    
    return render(request, 'eureka/seats.html', {
        'seat_map': seat_map,
        'layout_json': json.dumps(seat_map.layout_data),
        'coworkers_json': json.dumps(coworker_list),
        'coworkers': coworkers,
        'is_admin': request.user.is_superuser,
    })


@login_required
def save_seat_map_view(request):
    """儲存辦公室座位配置圖"""
    from django.http import JsonResponse
    
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "只有管理員可以儲存座位配置圖。"}, status=403)
        
    if request.method == 'POST':
        import json
        from .models import SeatMap, StaffInfo
        from django.db import transaction
        
        try:
            data = json.loads(request.body.decode('utf-8'))
            layout_data = data.get('layout_data')
            
            if not layout_data or not isinstance(layout_data, dict):
                return JsonResponse({"success": False, "error": "無效的配置資料。"}, status=400)
                
            seat_map = SeatMap.objects.filter(name="預設座位圖").first()
            if not seat_map:
                seat_map = SeatMap.objects.create(name="預設座位圖")
                
            seat_map.layout_data = layout_data
            seat_map.save()
            
            # Sync assigned seats to StaffInfo.seat
            elements = layout_data.get('elements', [])
            assigned_staff_seats = {}
            for elem in elements:
                if elem.get('type') == 'seat':
                    s_id = elem.get('staff_id')
                    seat_no = elem.get('seat_no', '')
                    if s_id and str(s_id).isdigit():
                        assigned_staff_seats[int(s_id)] = seat_no
            
            with transaction.atomic():
                for coworker in StaffInfo.objects.all():
                    new_seat = assigned_staff_seats.get(coworker.staff_id, "")
                    if coworker.seat != new_seat:
                        coworker.seat = new_seat
                        coworker.save()
            
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
            
    return JsonResponse({"success": False, "error": "僅支援 POST 請求。"}, status=405)


@login_required
def meeting_attendance_view(request):
    from .models import YearlyAttendance, WeeklyAttendance, PrayerMeetingAttendance
    from django.contrib import messages
    from django.utils import timezone
    import datetime

    # Get local current date
    today = timezone.localdate()

    # Calculate default Sunday (most recent past Sunday: Sunday on or before today)
    default_sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    # Calculate default Thursday (most recent past Thursday: Thursday on or before today)
    default_thursday = today - datetime.timedelta(days=(today.weekday() - 3) % 7)

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        
        try:
            if action == 'adult':
                date_str = request.POST.get('date', '').strip()
                first = request.POST.get('first_service', '').strip()
                second = request.POST.get('second_service', '').strip()
                evening = request.POST.get('evening_service', '').strip()
                
                # Validation
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                first_val = int(first) if first != '' else None
                second_val = int(second) if second != '' else None
                evening_val = int(evening) if evening != '' else None
                
                if first_val is not None and first_val < 0: raise ValueError("第一堂人數不能為負數")
                if second_val is not None and second_val < 0: raise ValueError("第二堂人數不能為負數")
                if evening_val is not None and evening_val < 0: raise ValueError("晚堂人數不能為負數")
                
                WeeklyAttendance.objects.update_or_create(
                    date=date_obj,
                    defaults={
                        'first_service': first_val,
                        'second_service': second_val,
                        'evening_service': evening_val,
                    }
                )
                messages.success(request, f"成功更新 {date_str} 的成人主日聚會人數！")
                
            elif action == 'prayer':
                date_str = request.POST.get('date', '').strip()
                att = request.POST.get('attendance', '').strip()
                
                # Validation
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                att_val = int(att)
                if att_val < 0: raise ValueError("人數不能為負數")
                
                PrayerMeetingAttendance.objects.update_or_create(
                    date=date_obj,
                    defaults={
                        'attendance': att_val,
                    }
                )
                messages.success(request, f"成功更新 {date_str} 的禱告會人數！")
                
            elif action == 'children':
                date_str = request.POST.get('date', '').strip()
                att = request.POST.get('attendance', '').strip()
                
                # Validation
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                att_val = int(att)
                if att_val < 0: raise ValueError("人數不能為負數")
                
                WeeklyAttendance.objects.update_or_create(
                    date=date_obj,
                    defaults={
                        'children': att_val,
                    }
                )
                messages.success(request, f"成功更新 {date_str} 的兒主聚會人數！")
                
            elif action == 'youth':
                date_str = request.POST.get('date', '').strip()
                att = request.POST.get('attendance', '').strip()
                
                # Validation
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                att_val = int(att)
                if att_val < 0: raise ValueError("人數不能為負數")
                
                WeeklyAttendance.objects.update_or_create(
                    date=date_obj,
                    defaults={
                        'youth': att_val,
                    }
                )
                messages.success(request, f"成功更新 {date_str} 的青少聚會人數！")
            
            else:
                messages.error(request, "未知的操作行為。")
                
        except ValueError as ve:
            messages.error(request, f"輸入資料有誤: {ve}")
        except Exception as e:
            messages.error(request, f"更新失敗: {e}")
            
        return redirect('eureka:meeting-attendance')

    # GET Request: Fetch stats
    # 1. Yearly Statistics for Chart.js
    yearly_qs = YearlyAttendance.objects.all().order_by('year')
    yearly_years = [y.year for y in yearly_qs]
    yearly_attendance = [y.attendance for y in yearly_qs]
    yearly_baptized = [y.baptized for y in yearly_qs]
    
    # 2. Weekly Attendance (last 52 weeks)
    weekly_list = WeeklyAttendance.objects.all().order_by('-date')[:52]
    
    # 3. Prayer Meeting Attendance
    prayer_list = PrayerMeetingAttendance.objects.all().order_by('-date')[:52]

    # Generate dropdown choices for Sundays (last 52 and next 12)
    sunday_choices = []
    for i in range(12, -53, -1):
        sun = default_sunday + datetime.timedelta(days=i*7)
        sunday_choices.append(sun)
        
    # Generate dropdown choices for Thursdays (last 52 and next 12)
    thursday_choices = []
    for i in range(12, -53, -1):
        thu = default_thursday + datetime.timedelta(days=i*7)
        thursday_choices.append(thu)

    context = {
        'yearly_years': yearly_years,
        'yearly_attendance': yearly_attendance,
        'yearly_baptized': yearly_baptized,
        'weekly_list': weekly_list,
        'prayer_list': prayer_list,
        'sunday_choices': sunday_choices,
        'thursday_choices': thursday_choices,
        'default_sunday': default_sunday,
        'default_thursday': default_thursday,
    }
    return render(request, 'eureka/meeting_attendance.html', context)


# ==================== SHIFT CRUD VIEWS ====================
from django.utils.dateparse import parse_time

def _get_time_val(val):
    if not val or not val.strip():
        return None
    return parse_time(val.strip())

@login_required
def shift_list_view(request):
    """同工班表列表及管理"""
    can_edit_shifts = request.user.is_superuser or request.user.has_perm('eureka.change_staffshift')
    shifts = StaffShift.objects.all().order_by('shift_code')
    return render(request, 'eureka/shift_list.html', {
        'shifts': shifts,
        'can_edit_shifts': can_edit_shifts,
    })

@login_required
def shift_create_view(request):
    """新增班表"""
    if not (request.user.is_superuser or request.user.has_perm('eureka.add_staffshift')):
        messages.error(request, "權限不足，無法新增班表。")
        return redirect('eureka:shift-list')

    if request.method == 'POST':
        shift_code = request.POST.get('shift_code', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not shift_code:
            messages.error(request, "班表代號為必填欄位。")
            return redirect('eureka:shift-list')
            
        if StaffShift.objects.filter(shift_code=shift_code).exists():
            messages.error(request, f"班表代號 {shift_code} 已存在。")
            return redirect('eureka:shift-list')

        try:
            StaffShift.objects.create(
                shift_code=shift_code,
                description=description,
                mon_start=_get_time_val(request.POST.get('mon_start')),
                mon_end=_get_time_val(request.POST.get('mon_end')),
                tue_start=_get_time_val(request.POST.get('tue_start')),
                tue_end=_get_time_val(request.POST.get('tue_end')),
                wed_start=_get_time_val(request.POST.get('wed_start')),
                wed_end=_get_time_val(request.POST.get('wed_end')),
                thu_start=_get_time_val(request.POST.get('thu_start')),
                thu_end=_get_time_val(request.POST.get('thu_end')),
                fri_start=_get_time_val(request.POST.get('fri_start')),
                fri_end=_get_time_val(request.POST.get('fri_end')),
                sat_start=_get_time_val(request.POST.get('sat_start')),
                sat_end=_get_time_val(request.POST.get('sat_end')),
                sun_start=_get_time_val(request.POST.get('sun_start')),
                sun_end=_get_time_val(request.POST.get('sun_end')),
            )
            messages.success(request, f"班表 {shift_code} 新增成功。")
        except Exception as e:
            messages.error(request, f"新增班表失敗: {e}")
            
    return redirect('eureka:shift-list')

@login_required
def shift_edit_view(request, shift_id):
    """編輯班表"""
    if not (request.user.is_superuser or request.user.has_perm('eureka.change_staffshift')):
        messages.error(request, "權限不足，無法修改班表。")
        return redirect('eureka:shift-list')
        
    shift = get_object_or_404(StaffShift, pk=shift_id)

    if request.method == 'POST':
        shift_code = request.POST.get('shift_code', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not shift_code:
            messages.error(request, "班表代號為必填欄位。")
            return redirect('eureka:shift-list')
            
        if StaffShift.objects.filter(shift_code=shift_code).exclude(pk=shift_id).exists():
            messages.error(request, f"班表代號 {shift_code} 已存在。")
            return redirect('eureka:shift-list')

        try:
            shift.shift_code = shift_code
            shift.description = description
            shift.mon_start = _get_time_val(request.POST.get('mon_start'))
            shift.mon_end = _get_time_val(request.POST.get('mon_end'))
            shift.tue_start = _get_time_val(request.POST.get('tue_start'))
            shift.tue_end = _get_time_val(request.POST.get('tue_end'))
            shift.wed_start = _get_time_val(request.POST.get('wed_start'))
            shift.wed_end = _get_time_val(request.POST.get('wed_end'))
            shift.thu_start = _get_time_val(request.POST.get('thu_start'))
            shift.thu_end = _get_time_val(request.POST.get('thu_end'))
            shift.fri_start = _get_time_val(request.POST.get('fri_start'))
            shift.fri_end = _get_time_val(request.POST.get('fri_end'))
            shift.sat_start = _get_time_val(request.POST.get('sat_start'))
            shift.sat_end = _get_time_val(request.POST.get('sat_end'))
            shift.sun_start = _get_time_val(request.POST.get('sun_start'))
            shift.sun_end = _get_time_val(request.POST.get('sun_end'))
            shift.save()
            messages.success(request, f"班表 {shift_code} 修改成功。")
        except Exception as e:
            messages.error(request, f"修改班表失敗: {e}")
            
    return redirect('eureka:shift-list')

@login_required
def shift_delete_view(request, shift_id):
    """刪除班表"""
    if not (request.user.is_superuser or request.user.has_perm('eureka.delete_staffshift')):
        messages.error(request, "權限不足，無法刪除班表。")
        return redirect('eureka:shift-list')
        
    shift = get_object_or_404(StaffShift, pk=shift_id)
    shift_code = shift.shift_code
    
    try:
        shift.delete()
        messages.success(request, f"班表 {shift_code} 已被刪除。")
    except Exception as e:
        messages.error(request, f"刪除班表失敗: {e}")
        
    return redirect('eureka:shift-list')



