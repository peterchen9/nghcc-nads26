from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.conf import settings
from .models import Page, BaptismSession, BaptismPerson, FuneralService

def page_detail(request, slug='home'):
    # Default to 'home' if no slug is provided
    page = Page.objects.filter(slug=slug, is_active=True).first()
    return render(request, 'pages/page_detail.html', {'page': page, 'slug': slug})

@login_required
def edit_home(request):
    if not request.user.is_superuser:
        raise PermissionDenied("您無權進行此操作。")
    page, created = Page.objects.get_or_create(
        slug='home',
        defaults={
            'title': '首頁',
            'content': '<h1>歡迎使用北門行政平台</h1>',
            'is_active': True
        }
    )
    return redirect(f'/admin/pages/page/{page.id}/change/')

@login_required
def qr_generator(request):
    return render(request, 'pages/qr_generator.html')

from .models import MediaCollection
import paramiko
import mimetypes
import tempfile
import subprocess
import os
from django.http import FileResponse, Http404

class SFTPFileWrapper:
    def __init__(self, sftp_file, sftp_client, transport):
        self.sftp_file = sftp_file
        self.sftp_client = sftp_client
        self.transport = transport
        
    def read(self, *args, **kwargs):
        return self.sftp_file.read(*args, **kwargs)
        
    def seek(self, *args, **kwargs):
        return self.sftp_file.seek(*args, **kwargs)
        
    def tell(self):
        return self.sftp_file.tell()
        
    def close(self):
        try:
            self.sftp_file.close()
        finally:
            try:
                self.sftp_client.close()
            finally:
                self.transport.close()


def _nas_connection_settings():
    config = {
        'host': settings.NAS_MEDIA_HOST,
        'port': settings.NAS_MEDIA_PORT,
        'username': settings.NAS_MEDIA_USER,
        'password': settings.NAS_MEDIA_PASSWORD,
    }
    if not all((config['host'], config['username'], config['password'])):
        raise RuntimeError('NAS media connection environment variables are not configured.')
    return config

@login_required
def media_collection(request):
    query = request.GET.get('q', '').strip()
    files = MediaCollection.objects.all()
    if query:
        from django.db.models import Q
        files = files.filter(Q(filename__icontains=query) | Q(path__icontains=query))
    files = files.order_by('path')
    for f in files:
        gb = f.size / 1073741824.0
        if gb == 0:
            f.size_gb_str = "0.000 GB"
        elif gb < 0.001:
            f.size_gb_str = f"{gb:.4f} GB"
        else:
            f.size_gb_str = f"{gb:.3f} GB"
        f.size_gb = gb
    return render(request, 'pages/media_collection.html', {'files': files, 'query': query})

@login_required
def media_download(request, pk):
    media = get_object_or_404(MediaCollection, pk=pk)
    try:
        nas = _nas_connection_settings()
        transport = paramiko.Transport((nas['host'], nas['port']))
        transport.connect(username=nas['username'], password=nas['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp_file = sftp.open(media.path, 'rb')
        wrapped_file = SFTPFileWrapper(sftp_file, sftp, transport)
        
        content_type = mimetypes.guess_type(media.filename)[0] or 'application/octet-stream'
        response = FileResponse(
            wrapped_file,
            content_type=content_type,
            as_attachment=True,
            filename=media.filename
        )
        return response
    except Exception as e:
        raise Http404(f"無法從 NAS 取得檔案: {e}")

@login_required
def media_edit_download(request, pk):
    media = get_object_or_404(MediaCollection, pk=pk)
    start_time = request.GET.get('start', '00:00:00').strip()
    end_time = request.GET.get('end', '').strip()
    custom_name = request.GET.get('name', '').strip()
    
    if not custom_name:
        custom_name = media.filename
    else:
        orig_ext = os.path.splitext(media.filename)[1]
        if not custom_name.endswith(orig_ext):
            custom_name += orig_ext

    try:
        nas = _nas_connection_settings()
        transport = paramiko.Transport((nas['host'], nas['port']))
        transport.connect(username=nas['username'], password=nas['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        temp_dir = tempfile.mkdtemp()
        temp_input = os.path.join(temp_dir, 'input' + os.path.splitext(media.filename)[1])
        temp_output = os.path.join(temp_dir, 'output' + os.path.splitext(media.filename)[1])
        
        sftp.get(media.path, temp_input)
        sftp.close()
        transport.close()
        
        cmd = ['ffmpeg', '-y', '-ss', start_time]
        if end_time:
            cmd.extend(['-to', end_time])
        cmd.extend(['-i', temp_input, '-c', 'copy', temp_output])
        
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p.communicate()
        
        if p.returncode != 0 or not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
            cmd_fallback = ['ffmpeg', '-y', '-ss', start_time]
            if end_time:
                cmd_fallback.extend(['-to', end_time])
            cmd_fallback.extend(['-i', temp_input, temp_output])
            p_fallback = subprocess.Popen(cmd_fallback, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            p_fallback.communicate()
            
        if not os.path.exists(temp_output):
            raise Http404("剪輯處理失敗，無法產生輸出檔案。")
            
        content_type = mimetypes.guess_type(custom_name)[0] or 'application/octet-stream'
        response = FileResponse(
            open(temp_output, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=custom_name
        )
        
        original_streaming = response.streaming_content
        def cleanup():
            try:
                yield from original_streaming
            finally:
                try:
                    if os.path.exists(temp_input): os.remove(temp_input)
                    if os.path.exists(temp_output): os.remove(temp_output)
                    if os.path.exists(temp_dir): os.rmdir(temp_dir)
                except Exception:
                    pass
        response.streaming_content = cleanup()
        return response
    except Exception as e:
        raise Http404(f"剪輯下載發生錯誤: {e}")


@login_required
def planned_feature(request):
    return render(request, 'planned.html')


@login_required
def under_construction(request, title):
    return render(request, 'pages/under_construction.html', {'title': title})


@login_required
def baptism_list_view(request):
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    from django.db.models import Count
    
    persons = BaptismPerson.objects.all().order_by('-date', 'id')
    sessions = BaptismSession.objects.all().order_by('-date', '-id')
    
    # Serialize persons to dicts
    persons_data = []
    for p in persons:
        persons_data.append({
            'id': p.id,
            'date': p.date.strftime('%Y/%m/%d'),
            'pastor': p.pastor,
            'name': p.name,
            'gender': p.gender,
            'category': p.category,
            'note': p.note,
            'session_id': p.session_id or '',
            'interview_pastor': p.interview_pastor,
            'gift_bible': p.gift_bible,
            'verse': p.verse,
            'is_completed': p.is_completed,
        })
        
    sessions_data = []
    for s in sessions:
        sessions_data.append({
            'id': s.id,
            'date': s.date.strftime('%Y/%m/%d'),
            'location': s.location,
            'pastor': s.pastor,
        })
        
    # Stats for the header widgets (only counting completed baptisms)
    completed_persons = [x for x in persons_data if x.get('is_completed')]
    total_count = len(completed_persons)
    adult_count = sum(1 for x in completed_persons if x.get('category') == '成人')
    infant_count = sum(1 for x in completed_persons if x.get('category') == '嬰兒洗')
    confirm_count = sum(1 for x in completed_persons if x.get('category') == '堅信禮')
    
    # Calculate yearly counts grouped by category for the stacked bar chart (only completed baptisms)
    yearly_stats = BaptismPerson.objects.filter(is_completed=True).values('date__year', 'category').annotate(count=Count('id')).order_by('date__year')
    
    years_data = {}
    for stat in yearly_stats:
        year = stat['date__year']
        if not year:
            continue
        category = stat['category']
        count = stat['count']
        if year not in years_data:
            years_data[year] = {'成人': 0, '嬰兒洗': 0, '堅信禮': 0}
        
        # Normalize category keys
        if category in years_data[year]:
            years_data[year][category] = count
        else:
            # Fallback/merge if category names differ slightly
            if '成人' in category:
                years_data[year]['成人'] += count
            elif '嬰兒' in category:
                years_data[year]['嬰兒洗'] += count
            elif '堅信' in category:
                years_data[year]['堅信禮'] += count
            
    sorted_years = sorted(list(years_data.keys()))
    chart_labels = [str(y) for y in sorted_years]
    chart_adults = [years_data[y]['成人'] for y in sorted_years]
    chart_infants = [years_data[y]['嬰兒洗'] for y in sorted_years]
    chart_confirms = [years_data[y]['堅信禮'] for y in sorted_years]
            
    context = {
        'title': '洗禮名單',
        'persons_json': json.dumps(persons_data, cls=DjangoJSONEncoder),
        'sessions': sessions_data,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_adults_json': json.dumps(chart_adults),
        'chart_infants_json': json.dumps(chart_infants),
        'chart_confirms_json': json.dumps(chart_confirms),
        'stats': {
            'total': total_count,
            'adult': adult_count,
            'infant': infant_count,
            'confirm': confirm_count,
        }
    }
    return render(request, 'pages/baptism_list.html', context)


from django.views.decorators.http import require_POST
from django.http import JsonResponse
import datetime

@login_required
@require_POST
def baptism_edit_view(request, pk):
    person = get_object_or_404(BaptismPerson, pk=pk)
    try:
        date_str = request.POST.get('date', '').strip()
        pastor = request.POST.get('pastor', '').strip()
        name = request.POST.get('name', '').strip()
        gender = request.POST.get('gender', '').strip()
        category = request.POST.get('category', '').strip()
        note = request.POST.get('note', '').strip()
        interview_pastor = request.POST.get('interview_pastor', '').strip()
        gift_bible = request.POST.get('gift_bible', '').strip()
        verse = request.POST.get('verse', '').strip()
        
        is_completed_val = request.POST.get('is_completed', '').strip()
        # Handle 'true', 'on', '1' or checkbox checks
        is_completed = (is_completed_val in ('true', 'on', '1', 'True'))
        
        if not name or not date_str:
            return JsonResponse({'success': False, 'error': '姓名與日期為必填欄位。'})
            
        person.date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        person.pastor = pastor
        person.name = name
        person.gender = gender
        person.category = category
        person.note = note
        person.interview_pastor = interview_pastor
        person.gift_bible = gift_bible
        person.verse = verse
        person.is_completed = is_completed
        person.save()
        
        return JsonResponse({
            'success': True,
            'person': {
                'id': person.id,
                'date': person.date.strftime('%Y/%m/%d'),
                'pastor': person.pastor,
                'name': person.name,
                'gender': person.gender,
                'category': person.category,
                'note': person.note,
                'interview_pastor': person.interview_pastor,
                'gift_bible': person.gift_bible,
                'verse': person.verse,
                'is_completed': person.is_completed,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def baptism_new_session_view(request):
    try:
        date_str = request.POST.get('date', '').strip()
        location = request.POST.get('location', '').strip()
        pastor = request.POST.get('pastor', '').strip()
        
        if not date_str or not location or not pastor:
            return JsonResponse({'success': False, 'error': '日期、場次/地點與主領牧師皆為必填。'})
            
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        session = BaptismSession.objects.create(
            date=date_obj,
            location=location,
            pastor=pastor
        )
        return JsonResponse({
            'success': True,
            'session': {
                'id': session.id,
                'date': session.date.strftime('%Y/%m/%d'),
                'location': session.location,
                'pastor': session.pastor,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def baptism_register_view(request):
    try:
        session_id = request.POST.get('session_id', '').strip()
        name = request.POST.get('name', '').strip()
        gender = request.POST.get('gender', '').strip()
        category = request.POST.get('category', '').strip()
        interview_pastor = request.POST.get('interview_pastor', '').strip()
        gift_bible = request.POST.get('gift_bible', '').strip()
        verse = request.POST.get('verse', '').strip()
        note = request.POST.get('note', '').strip()
        
        if not session_id or not name:
            return JsonResponse({'success': False, 'error': '請選擇洗禮場次並輸入受洗人姓名。'})
            
        session = get_object_or_404(BaptismSession, pk=session_id)
        
        person = BaptismPerson.objects.create(
            date=session.date,
            pastor=session.pastor,
            name=name,
            gender=gender,
            category=category,
            note=note,
            session=session,
            interview_pastor=interview_pastor,
            gift_bible=gift_bible,
            verse=verse,
            is_completed=False  # Registered applicants are set as NOT completed by default
        )
        
        return JsonResponse({
            'success': True,
            'person': {
                'id': person.id,
                'date': person.date.strftime('%Y/%m/%d'),
                'pastor': person.pastor,
                'name': person.name,
                'gender': person.gender,
                'category': person.category,
                'note': person.note,
                'interview_pastor': person.interview_pastor,
                'gift_bible': person.gift_bible,
                'verse': person.verse,
                'is_completed': person.is_completed,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def baptism_batch_complete_view(request):
    try:
        import json
        body = json.loads(request.body)
        person_ids = body.get('person_ids', [])
        
        if not person_ids:
            return JsonResponse({'success': False, 'error': '請選擇要完成受洗的報名者。'})
            
        BaptismPerson.objects.filter(id__in=person_ids).update(is_completed=True)
        
        # Return updated records
        updated_persons = BaptismPerson.objects.filter(id__in=person_ids)
        serialized = []
        for p in updated_persons:
            serialized.append({
                'id': p.id,
                'date': p.date.strftime('%Y/%m/%d'),
                'pastor': p.pastor,
                'name': p.name,
                'gender': p.gender,
                'category': p.category,
                'note': p.note,
                'session_id': p.session_id or '',
                'interview_pastor': p.interview_pastor,
                'gift_bible': p.gift_bible,
                'verse': p.verse,
                'is_completed': p.is_completed,
            })
            
        return JsonResponse({'success': True, 'persons': serialized})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def baptism_member_profile_view(request, name):
    from modules.eureka.models import Member
    import os
    from django.conf import settings
    
    member = Member.objects.filter(name=name).first()
    if member:
        photo_filename = f"{member.church_id}.jpg"
        photo_path = os.path.join(settings.MEDIA_ROOT, 'eureka', 'photo', photo_filename)
        has_photo = os.path.exists(photo_path)
        photo_url = f"/eureka/photo/{photo_filename}" if has_photo else None
        
        return render(request, 'pages/member_profile_snippet.html', {
            'member': member,
            'has_photo': has_photo,
            'photo_url': photo_url
        })
    else:
        return render(request, 'pages/member_profile_empty.html', {'name': name})


DEFAULT_FUNERAL_SHIFTS = [
    {"group_no": 1, "preacher": "董牧師", "leader": "慕聖牧師", "scripture_prayer": "明月牧師"},
    {"group_no": 2, "preacher": "明月牧師", "leader": "仲甫傳道", "scripture_prayer": "明珠牧師"},
    {"group_no": 3, "preacher": "玉筍牧師", "leader": "宜庭牧師", "scripture_prayer": "璦珺師母"},
    {"group_no": 4, "preacher": "宜庭牧師", "leader": "沐恩傳道", "scripture_prayer": "一琴師母"},
    {"group_no": 5, "preacher": "仲甫傳道", "leader": "囿余傳道", "scripture_prayer": "明珠牧師"},
    {"group_no": 6, "preacher": "慕聖牧師", "leader": "仲甫傳道", "scripture_prayer": "囿余傳道"},
    {"group_no": 7, "preacher": "沐恩傳道", "leader": "宜庭牧師", "scripture_prayer": "奇英師母"},
    {"group_no": 8, "preacher": "囿余傳道", "leader": "沐恩傳道", "scripture_prayer": "一琴師母"},
]


def ensure_default_funeral_shifts():
    from .models import FuneralShift
    if not FuneralShift.objects.exists():
        for shift_data in DEFAULT_FUNERAL_SHIFTS:
            FuneralShift.objects.create(**shift_data)


@login_required
def funeral_list_view(request):
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    from modules.eureka.models import Member
    from .models import FuneralShift

    ensure_default_funeral_shifts()
    shifts_qs = FuneralShift.objects.all().order_by('group_no')
    shifts_data = list(shifts_qs.values('id', 'group_no', 'preacher', 'leader', 'scripture_prayer'))

    services = FuneralService.objects.all().order_by('-service_date', 'id')
    services_data = []
    for s in services:
        services_data.append({
            'id': s.id,
            'deceased_name': s.deceased_name,
            'deceased_date_of_birth': s.deceased_date_of_birth.strftime('%Y-%m-%d') if s.deceased_date_of_birth else '',
            'deceased_date_of_death': s.deceased_date_of_death.strftime('%Y-%m-%d') if s.deceased_date_of_death else '',
            'deceased_age': s.deceased_age or '',
            'family_contact': s.family_contact,
            'family_relationship': s.family_relationship,
            'family_phone': s.family_phone,
            'service_date': s.service_date.strftime('%Y/%m/%d'),
            'service_time': s.service_time,
            'location': s.location,
            'note': s.note,
            'pastor': s.pastor,
            'preacher': s.preacher,
            'leader': s.leader,
            'pianist': s.pianist,
            'sound': s.sound,
            'projection': s.projection,
            'ushers': s.ushers,
            'choir': s.choir,
            'traffic': s.traffic,
            'coffining': s.coffining,
            'cremation': s.cremation,
            'scripture': s.scripture,
            'prayer': s.prayer,
            'burial': s.burial,
            'is_completed': s.is_completed,
        })

    # Fetch autocomplete list of members
    member_names = list(Member.objects.values_list('name', flat=True).distinct().order_by('name'))

    context = {
        'title': '安息禮拜',
        'services_json': json.dumps(services_data, cls=DjangoJSONEncoder),
        'member_names_json': json.dumps(member_names),
        'shifts_json': json.dumps(shifts_data, cls=DjangoJSONEncoder),
    }
    return render(request, 'pages/funeral_list.html', context)


@login_required
def funeral_shifts_view(request):
    import json
    from django.db import transaction
    from .models import FuneralShift

    ensure_default_funeral_shifts()

    if request.method == 'GET':
        shifts = list(FuneralShift.objects.all().order_by('group_no').values('id', 'group_no', 'preacher', 'leader', 'scripture_prayer'))
        return JsonResponse({'success': True, 'shifts': shifts})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            shifts_input = body.get('shifts', [])

            with transaction.atomic():
                FuneralShift.objects.all().delete()
                new_shifts = []
                for s in shifts_input:
                    try:
                        g_no = int(s.get('group_no', 0))
                    except (ValueError, TypeError):
                        continue
                    if g_no <= 0:
                        continue
                    new_shifts.append(FuneralShift(
                        group_no=g_no,
                        preacher=str(s.get('preacher', '')).strip(),
                        leader=str(s.get('leader', '')).strip(),
                        scripture_prayer=str(s.get('scripture_prayer', '')).strip()
                    ))
                FuneralShift.objects.bulk_create(new_shifts)

            updated_shifts = list(FuneralShift.objects.all().order_by('group_no').values('id', 'group_no', 'preacher', 'leader', 'scripture_prayer'))
            return JsonResponse({'success': True, 'shifts': updated_shifts})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})



@login_required
@require_POST
def funeral_new_view(request):
    try:
        deceased_name = request.POST.get('deceased_name', '').strip()
        service_date_str = request.POST.get('service_date', '').strip()
        
        if not deceased_name or not service_date_str:
            return JsonResponse({'success': False, 'error': '故人姓名與禮拜日期為必填欄位。'})
            
        birth_str = request.POST.get('deceased_date_of_birth', '').strip()
        death_str = request.POST.get('deceased_date_of_death', '').strip()
        age_str = request.POST.get('deceased_age', '').strip()
        
        deceased_date_of_birth = datetime.datetime.strptime(birth_str, '%Y-%m-%d').date() if birth_str else None
        deceased_date_of_death = datetime.datetime.strptime(death_str, '%Y-%m-%d').date() if death_str else None
        deceased_age = int(age_str) if age_str else None
        
        service_date = datetime.datetime.strptime(service_date_str, '%Y-%m-%d').date()
        
        service = FuneralService.objects.create(
            deceased_name=deceased_name,
            deceased_date_of_birth=deceased_date_of_birth,
            deceased_date_of_death=deceased_date_of_death,
            deceased_age=deceased_age,
            family_contact=request.POST.get('family_contact', '').strip(),
            family_relationship=request.POST.get('family_relationship', '').strip(),
            family_phone=request.POST.get('family_phone', '').strip(),
            service_date=service_date,
            service_time=request.POST.get('service_time', '').strip(),
            location=request.POST.get('location', '').strip(),
            note=request.POST.get('note', '').strip(),
            pastor=request.POST.get('pastor', '').strip(),
            preacher=request.POST.get('preacher', '').strip(),
            leader=request.POST.get('leader', '').strip(),
            pianist=request.POST.get('pianist', '').strip(),
            sound=request.POST.get('sound', '').strip(),
            projection=request.POST.get('projection', '').strip(),
            ushers=request.POST.get('ushers', '').strip(),
            choir=request.POST.get('choir', '').strip(),
            traffic=request.POST.get('traffic', '').strip(),
            coffining=request.POST.get('coffining', '').strip(),
            cremation=request.POST.get('cremation', '').strip(),
            scripture=request.POST.get('scripture', '').strip(),
            prayer=request.POST.get('prayer', '').strip(),
            burial=request.POST.get('burial', '').strip(),
            is_completed=False
        )
        
        return JsonResponse({
            'success': True,
            'service': {
                'id': service.id,
                'deceased_name': service.deceased_name,
                'deceased_date_of_birth': service.deceased_date_of_birth.strftime('%Y-%m-%d') if service.deceased_date_of_birth else '',
                'deceased_date_of_death': service.deceased_date_of_death.strftime('%Y-%m-%d') if service.deceased_date_of_death else '',
                'deceased_age': service.deceased_age or '',
                'family_contact': service.family_contact,
                'family_relationship': service.family_relationship,
                'family_phone': service.family_phone,
                'service_date': service.service_date.strftime('%Y/%m/%d'),
                'service_time': service.service_time,
                'location': service.location,
                'note': service.note,
                'pastor': service.pastor,
                'preacher': service.preacher,
                'leader': service.leader,
                'pianist': service.pianist,
                'sound': service.sound,
                'projection': service.projection,
                'ushers': service.ushers,
                'choir': service.choir,
                'traffic': service.traffic,
                'coffining': service.coffining,
                'cremation': service.cremation,
                'scripture': service.scripture,
                'prayer': service.prayer,
                'burial': service.burial,
                'is_completed': service.is_completed,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def funeral_edit_view(request, pk):
    service = get_object_or_404(FuneralService, pk=pk)
    try:
        deceased_name = request.POST.get('deceased_name', '').strip()
        service_date_str = request.POST.get('service_date', '').strip()
        
        if not deceased_name or not service_date_str:
            return JsonResponse({'success': False, 'error': '故人姓名與禮拜日期為必填欄位。'})
            
        birth_str = request.POST.get('deceased_date_of_birth', '').strip()
        death_str = request.POST.get('deceased_date_of_death', '').strip()
        age_str = request.POST.get('deceased_age', '').strip()
        
        deceased_date_of_birth = datetime.datetime.strptime(birth_str, '%Y-%m-%d').date() if birth_str else None
        deceased_date_of_death = datetime.datetime.strptime(death_str, '%Y-%m-%d').date() if death_str else None
        deceased_age = int(age_str) if age_str else None
        
        service_date = datetime.datetime.strptime(service_date_str, '%Y-%m-%d').date()
        is_completed_val = request.POST.get('is_completed', '').strip()
        is_completed = (is_completed_val in ('true', 'on', '1', 'True'))
        
        service.deceased_name = deceased_name
        service.deceased_date_of_birth = deceased_date_of_birth
        service.deceased_date_of_death = deceased_date_of_death
        service.deceased_age = deceased_age
        service.family_contact = request.POST.get('family_contact', '').strip()
        service.family_relationship = request.POST.get('family_relationship', '').strip()
        service.family_phone = request.POST.get('family_phone', '').strip()
        service.service_date = service_date
        service.service_time = request.POST.get('service_time', '').strip()
        service.location = request.POST.get('location', '').strip()
        service.note = request.POST.get('note', '').strip()
        service.pastor = request.POST.get('pastor', '').strip()
        service.preacher = request.POST.get('preacher', '').strip()
        service.leader = request.POST.get('leader', '').strip()
        service.pianist = request.POST.get('pianist', '').strip()
        service.sound = request.POST.get('sound', '').strip()
        service.projection = request.POST.get('projection', '').strip()
        service.ushers = request.POST.get('ushers', '').strip()
        service.choir = request.POST.get('choir', '').strip()
        service.traffic = request.POST.get('traffic', '').strip()
        service.coffining = request.POST.get('coffining', '').strip()
        service.cremation = request.POST.get('cremation', '').strip()
        service.scripture = request.POST.get('scripture', '').strip()
        service.prayer = request.POST.get('prayer', '').strip()
        service.burial = request.POST.get('burial', '').strip()
        service.is_completed = is_completed
        service.save()
        
        return JsonResponse({
            'success': True,
            'service': {
                'id': service.id,
                'deceased_name': service.deceased_name,
                'deceased_date_of_birth': service.deceased_date_of_birth.strftime('%Y-%m-%d') if service.deceased_date_of_birth else '',
                'deceased_date_of_death': service.deceased_date_of_death.strftime('%Y-%m-%d') if service.deceased_date_of_death else '',
                'deceased_age': service.deceased_age or '',
                'family_contact': service.family_contact,
                'family_relationship': service.family_relationship,
                'family_phone': service.family_phone,
                'service_date': service.service_date.strftime('%Y/%m/%d'),
                'service_time': service.service_time,
                'location': service.location,
                'note': service.note,
                'pastor': service.pastor,
                'preacher': service.preacher,
                'leader': service.leader,
                'pianist': service.pianist,
                'sound': service.sound,
                'projection': service.projection,
                'ushers': service.ushers,
                'choir': service.choir,
                'traffic': service.traffic,
                'coffining': service.coffining,
                'cremation': service.cremation,
                'scripture': service.scripture,
                'prayer': service.prayer,
                'burial': service.burial,
                'is_completed': service.is_completed,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def funeral_batch_complete_view(request):
    try:
        import json
        body = json.loads(request.body)
        service_ids = body.get('service_ids', [])
        
        if not service_ids:
            return JsonResponse({'success': False, 'error': '請選擇要標記完成的安息禮拜。'})
            
        FuneralService.objects.filter(id__in=service_ids).update(is_completed=True)
        
        # Return updated records
        updated_services = FuneralService.objects.filter(id__in=service_ids)
        serialized = []
        for s in updated_services:
            serialized.append({
                'id': s.id,
                'deceased_name': s.deceased_name,
                'deceased_date_of_birth': s.deceased_date_of_birth.strftime('%Y-%m-%d') if s.deceased_date_of_birth else '',
                'deceased_date_of_death': s.deceased_date_of_death.strftime('%Y-%m-%d') if s.deceased_date_of_death else '',
                'deceased_age': s.deceased_age or '',
                'family_contact': s.family_contact,
                'family_relationship': s.family_relationship,
                'family_phone': s.family_phone,
                'service_date': s.service_date.strftime('%Y/%m/%d'),
                'service_time': s.service_time,
                'location': s.location,
                'note': s.note,
                'pastor': s.pastor,
                'preacher': s.preacher,
                'leader': s.leader,
                'pianist': s.pianist,
                'sound': s.sound,
                'projection': s.projection,
                'ushers': s.ushers,
                'choir': s.choir,
                'traffic': s.traffic,
                'coffining': s.coffining,
                'cremation': s.cremation,
                'scripture': s.scripture,
                'prayer': s.prayer,
                'burial': s.burial,
                'is_completed': s.is_completed,
            })
            
        return JsonResponse({'success': True, 'services': serialized})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def board_minutes_view(request):
    from .models import DeaconBoardMinutes
    query = request.GET.get('q', '').strip()
    year = request.GET.get('year', '').strip()
    
    minutes_list = DeaconBoardMinutes.objects.all().order_by('-meeting_date', '-id')
    
    if query:
        from django.db.models import Q
        minutes_list = minutes_list.filter(
            Q(title__icontains=query) | Q(summary__icontains=query)
        )
    
    if year:
        minutes_list = minutes_list.filter(meeting_date__year=year)
        
    # Get all available years for the dropdown filter
    available_dates = DeaconBoardMinutes.objects.dates('meeting_date', 'year', order='DESC')
    available_years = [d.year for d in available_dates]
    
    context = {
        'minutes_list': minutes_list,
        'query': query,
        'selected_year': year,
        'available_years': available_years,
    }
    return render(request, 'pages/board_minutes.html', context)






