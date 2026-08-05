import datetime
import os
import uuid
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from .models import Course, CourseClass, CoursePost, CourseClassRecording, MakeUpRecord

def get_classrooms_safe():
    try:
        from modules.facility.views import _rooms
        return _rooms()
    except (ImportError, Exception):
        # Fallback for testing/uninstalled settings
        return [
            {'id': 1, 'room_name': '101'},
            {'id': 2, 'room_name': '201'},
            {'id': 3, 'room_name': 'B01'},
        ]

def get_classroom_by_id_safe(room_id):
    if not room_id:
        return None
    try:
        from modules.facility.views import _room_by_id
        return _room_by_id(room_id)
    except (ImportError, Exception):
        # Fallback for testing
        rooms = {
            1: {'id': 1, 'room_name': '101'},
            2: {'id': 2, 'room_name': '201'},
            3: {'id': 3, 'room_name': 'B01'},
        }
        try:
            return rooms.get(int(room_id))
        except (ValueError, TypeError):
            return None

@login_required
def course_list_view(request):
    """課程列表頁面"""
    courses = Course.objects.all()
    
    # 搜尋與篩選
    q = request.GET.get('q', '').strip()
    if q:
        courses = courses.filter(
            models.Q(code__icontains=q) |
            models.Q(subject__icontains=q) |
            models.Q(teachers__icontains=q) |
            models.Q(class_leader__icontains=q)
        )
        
    makeup_filter = request.GET.get('makeup', '').strip()
    if makeup_filter == '1':
        courses = courses.filter(makeup_required=True)
    elif makeup_filter == '0':
        courses = courses.filter(makeup_required=False)

    year_filter = request.GET.get('year', '').strip()
    if year_filter:
        courses = courses.filter(code__contains=f"RS{year_filter}")

    # 計算統計數據
    total_count = courses.count()
    makeup_count = courses.filter(makeup_required=True).count()
    total_hours = sum(c.total_classes * c.hours_per_class for c in courses) / 60.0

    # 取得現有所有年份供篩選
    available_years = sorted(
        list(set(c.code[2:6] for c in Course.objects.all() if len(c.code) >= 6)),
        reverse=True
    )

    context = {
        'courses': courses,
        'q': q,
        'makeup_filter': makeup_filter,
        'year_filter': year_filter,
        'available_years': available_years,
        'total_count': total_count,
        'makeup_count': makeup_count,
        'total_hours': f"{total_hours:.1f}" if total_hours > 0 else "0",
    }
    return render(request, 'education/course_list.html', context)


@login_required
def course_detail_view(request, pk):
    """課程詳細內容頁面"""
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.all().order_by('class_number')
    
    context = {
        'course': course,
        'classes': classes,
    }
    return render(request, 'education/course_detail.html', context)


@login_required
def course_create_view(request):
    """新增課程頁面"""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        introduction = request.POST.get('introduction', '').strip()
        teachers = request.POST.get('teachers', '').strip()
        class_leader = request.POST.get('class_leader', '').strip()
        
        try:
            total_classes = int(request.POST.get('total_classes', 1))
        except ValueError:
            total_classes = 1
            
        try:
            hours_per_class = int(request.POST.get('hours_per_class', 60))
        except ValueError:
            hours_per_class = 60

        class_time = request.POST.get('class_time', '').strip()
        makeup_required = request.POST.get('makeup_required') == 'on'
        
        classroom_id_str = request.POST.get('classroom_id', '').strip()
        classroom_id = None
        classroom_name = ""
        if classroom_id_str:
            room_detail = get_classroom_by_id_safe(classroom_id_str)
            if room_detail:
                try:
                    classroom_id = int(room_detail['id'])
                    classroom_name = room_detail['room_name']
                except (ValueError, TypeError, KeyError):
                    pass

        if not subject or not teachers or not class_time:
            messages.error(request, "請填寫所有必填欄位 (課程主題、師資、上課時間)")
            return render(request, 'education/course_form.html', {
                'action': 'create',
                'classrooms': get_classrooms_safe()
            })

        try:
            with transaction.atomic():
                # 建立課程主檔
                course = Course.objects.create(
                    subject=subject,
                    introduction=introduction,
                    teachers=teachers,
                    class_leader=class_leader,
                    total_classes=total_classes,
                    hours_per_class=hours_per_class,
                    class_time=class_time,
                    classroom_id=classroom_id,
                    classroom_name=classroom_name,
                    makeup_required=makeup_required
                )
                
                # 建立課程表 (課程單堂細項)
                for i in range(1, total_classes + 1):
                    date_str = request.POST.get(f'class_date_{i}', '').strip()
                    c_subject = request.POST.get(f'class_subject_{i}', '').strip()
                    c_teacher = request.POST.get(f'class_teacher_{i}', '').strip()
                    
                    class_date = None
                    if date_str:
                        try:
                            class_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                            
                    CourseClass.objects.create(
                        course=course,
                        class_number=i,
                        date=class_date,
                        subject=c_subject or f"第 {i} 堂課",
                        teacher=c_teacher or teachers
                    )
                
            messages.success(request, f"課程 {course.code} 規劃建立成功！")
            return redirect(reverse('education:course-detail', args=[course.pk]))
        except Exception as e:
            messages.error(request, f"儲存失敗，錯誤原因：{str(e)}")
            
    # GET 請求
    context = {
        'action': 'create',
        'default_classes_count': 1,
        'classrooms': get_classrooms_safe(),
    }
    return render(request, 'education/course_form.html', context)


@login_required
def course_update_view(request, pk):
    """編輯課程頁面"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        introduction = request.POST.get('introduction', '').strip()
        teachers = request.POST.get('teachers', '').strip()
        class_leader = request.POST.get('class_leader', '').strip()
        
        try:
            total_classes = int(request.POST.get('total_classes', 1))
        except ValueError:
            total_classes = course.total_classes
            
        try:
            hours_per_class = int(request.POST.get('hours_per_class', 60))
        except ValueError:
            hours_per_class = course.hours_per_class

        class_time = request.POST.get('class_time', '').strip()
        makeup_required = request.POST.get('makeup_required') == 'on'

        classroom_id_str = request.POST.get('classroom_id', '').strip()
        classroom_id = None
        classroom_name = ""
        if classroom_id_str:
            room_detail = get_classroom_by_id_safe(classroom_id_str)
            if room_detail:
                try:
                    classroom_id = int(room_detail['id'])
                    classroom_name = room_detail['room_name']
                except (ValueError, TypeError, KeyError):
                    pass

        if not subject or not teachers or not class_time:
            messages.error(request, "請填寫所有必填欄位 (課程主題、師資、上課時間)")
            return redirect(reverse('education:course-edit', args=[course.pk]))

        try:
            with transaction.atomic():
                # 更新課程主檔
                course.subject = subject
                course.introduction = introduction
                course.teachers = teachers
                course.class_leader = class_leader
                course.total_classes = total_classes
                course.hours_per_class = hours_per_class
                course.class_time = class_time
                course.classroom_id = classroom_id
                course.classroom_name = classroom_name
                course.makeup_required = makeup_required
                course.save()
                
                # 更新或建立各堂課資訊
                for i in range(1, total_classes + 1):
                    date_str = request.POST.get(f'class_date_{i}', '').strip()
                    c_subject = request.POST.get(f'class_subject_{i}', '').strip()
                    c_teacher = request.POST.get(f'class_teacher_{i}', '').strip()
                    
                    class_date = None
                    if date_str:
                        try:
                            class_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    
                    # 嘗試更新或建立新堂次
                    c_class, created = CourseClass.objects.get_or_create(
                        course=course,
                        class_number=i,
                        defaults={
                            'date': class_date,
                            'subject': c_subject or f"第 {i} 堂課",
                            'teacher': c_teacher or teachers
                        }
                    )
                    if not created:
                        c_class.date = class_date
                        c_class.subject = c_subject or f"第 {i} 堂課"
                        c_class.teacher = c_teacher or teachers
                        c_class.save()
                
                # 刪除多出的堂次 (若次數縮減了)
                CourseClass.objects.filter(course=course, class_number__gt=total_classes).delete()

            messages.success(request, f"課程 {course.code} 規劃更新成功！")
            return redirect(reverse('education:course-detail', args=[course.pk]))
        except Exception as e:
            messages.error(request, f"更新失敗，錯誤原因：{str(e)}")

    # GET 請求
    classes = course.classes.all().order_by('class_number')
    context = {
        'action': 'edit',
        'course': course,
        'classes': classes,
        'classrooms': get_classrooms_safe(),
    }
    return render(request, 'education/course_form.html', context)


@login_required
def course_delete_view(request, pk):
    """刪除課程"""
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        code = course.code
        course.delete()
        messages.success(request, f"課程 {code} 刪除成功。")
        return redirect(reverse('education:course-list'))
    
    # 預防以 GET 方式進入刪除
    return HttpResponseRedirect(reverse('education:course-list'))


@login_required
def course_board_view(request, pk):
    """討論版"""
    course = get_object_or_404(Course, pk=pk)
    posts = course.posts.all().order_by('-created_at')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not title or not content:
            messages.error(request, "標題與內容皆為必填！")
        else:
            CoursePost.objects.create(
                course=course,
                author=request.user,
                title=title,
                content=content
            )
            messages.success(request, "公告發佈成功！")
            return redirect(reverse('education:course-board', args=[course.pk]))
            
    context = {
        'course': course,
        'posts': posts,
    }
    return render(request, 'education/course_board.html', context)


@login_required
def class_record_view(request, class_id):
    """教師手機錄音頁面"""
    c_class = get_object_or_404(CourseClass, pk=class_id)
    recording = getattr(c_class, 'recording', None)
    
    context = {
        'class_obj': c_class,
        'recording': recording,
    }
    return render(request, 'education/class_record.html', context)


@login_required
def class_upload_recording_api(request, class_id):
    """教師端 AJAX 自動上傳錄音"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '必須使用 POST 方法'}, status=405)
        
    c_class = get_object_or_404(CourseClass, pk=class_id)
    audio_file = request.FILES.get('audio')
    
    if not audio_file:
        return JsonResponse({'status': 'error', 'message': '未接收到錄音檔案'}, status=400)
        
    # 驗證附檔名與 MIME type
    original_name = audio_file.name or 'recording.webm'
    ext = os.path.splitext(original_name)[1].lower()
    if not ext:
        ext = '.webm'
        
    ALLOWED_EXTENSIONS = {'.webm', '.ogg', '.mp3', '.wav', '.m4a', '.mp4'}
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({'status': 'error', 'message': f'不支援的檔案格式: {ext}'}, status=400)
        
    content_type = audio_file.content_type or ''
    if not content_type.startswith('audio/') and content_type != 'application/octet-stream':
        # WebM audio recorded blobs are sometimes sent as application/octet-stream by some mobile devices/libraries
        pass
        
    # 驗證檔案大小，限制為 50MB (52,428,800 bytes)
    MAX_SIZE = 50 * 1024 * 1024
    if audio_file.size > MAX_SIZE:
        return JsonResponse({'status': 'error', 'message': '錄音檔案大小超過 50MB 限制'}, status=400)
        
    # 產生安全不可預測的檔名 (UUID)
    secure_filename = f"{uuid.uuid4().hex}{ext}"
    audio_file.name = secure_filename
    
    try:
        with transaction.atomic():
            # 檢查是否已存在錄音紀錄，若有則先刪除實體檔案以釋放空間
            recording, created = CourseClassRecording.objects.get_or_create(
                course_class=c_class,
                defaults={
                    'audio_file': audio_file,
                    'filename': original_name,
                    'file_size': audio_file.size
                }
            )
            
            if not created:
                # 刪除舊檔案
                if recording.audio_file:
                    try:
                        recording.audio_file.delete(save=False)
                    except Exception:
                        pass
                recording.audio_file = audio_file
                recording.filename = original_name
                recording.file_size = audio_file.size
                recording.save()
                
        return JsonResponse({'status': 'success', 'recording_id': recording.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'檔案儲存失敗：{str(e)}'}, status=500)


@login_required
def course_makeup_view(request, pk):
    """學員補課網頁"""
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.all().order_by('class_number')
    
    class_list = []
    for c in classes:
        recording = getattr(c, 'recording', None)
        is_completed = MakeUpRecord.objects.filter(user=request.user, course_class=c).exists()
        completed_record = MakeUpRecord.objects.filter(user=request.user, course_class=c).first()
        
        class_list.append({
            'class': c,
            'recording': recording,
            'is_completed': is_completed,
            'completed_at': completed_record.completed_at if completed_record else None
        })
        
    context = {
        'course': course,
        'class_list': class_list,
    }
    return render(request, 'education/course_makeup.html', context)


@login_required
def class_makeup_complete_view(request, class_id):
    """登記補課完成"""
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('education:course-list'))
        
    c_class = get_object_or_404(CourseClass, pk=class_id)
    
    # 登記補課
    MakeUpRecord.objects.get_or_create(user=request.user, course_class=c_class)
    
    messages.success(request, f"已成功登記第 {c_class.class_number} 堂課 【{c_class.subject}】 的補課！")
    return redirect(reverse('education:course-makeup', args=[c_class.course.pk]))


@login_required
def serve_recording_audio_view(request, recording_id):
    """安全串流/下載錄音檔，只開放給已登入使用者"""
    recording = get_object_or_404(CourseClassRecording, pk=recording_id)
    
    try:
        # 開啟私有儲存區的檔案
        file_handle = recording.audio_file.open('rb')
        
        # 猜測 MIME Type
        content_type, _ = mimetypes.guess_type(recording.filename)
        if not content_type:
            content_type = 'audio/webm'  # fallback
        elif content_type == 'video/webm':
            content_type = 'audio/webm'
            
        response = FileResponse(file_handle, content_type=content_type)
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except FileNotFoundError:
        raise Http404("錄音檔案不存在")


@login_required
def course_documents_view(request, pk):
    """課程產出文件選單頁面"""
    course = get_object_or_404(Course, pk=pk)
    context = {
        'course': course,
    }
    return render(request, 'education/course_documents.html', context)


@login_required
def doc_announcement_view(request, pk):
    """產出文件：課程公告"""
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.all().order_by('class_number')
    context = {
        'course': course,
        'classes': classes,
    }
    return render(request, 'education/doc_announcement.html', context)


@login_required
def doc_doorsign_view(request, pk):
    """產出文件：教室門貼"""
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.all().order_by('class_number')
    context = {
        'course': course,
        'classes': classes,
    }
    return render(request, 'education/doc_doorsign.html', context)


@login_required
def doc_feedback_view(request, pk):
    """產出文件：課程回應單"""
    course = get_object_or_404(Course, pk=pk)
    context = {
        'course': course,
    }
    return render(request, 'education/doc_feedback.html', context)


@login_required
def doc_attendance_view(request, pk):
    """產出文件：點名表"""
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.all().order_by('class_number')
    # 產生 25 個空白學員列供簽到
    blank_rows = range(1, 26)
    
    # 產生絕對手機錄音網址，供前端生成文字
    record_url = request.build_absolute_uri(
        reverse('education:course-record', args=[course.pk])
    )
    
    context = {
        'course': course,
        'classes': classes,
        'blank_rows': blank_rows,
        'record_url': record_url,
    }
    return render(request, 'education/doc_attendance.html', context)


@login_required
def course_qrcode_view(request, pk):
    """產生指向課程手機錄音頁面的二維碼"""
    course = get_object_or_404(Course, pk=pk)
    
    target_url = request.build_absolute_uri(
        reverse('education:course-record', kwargs={'pk': course.pk})
    )
    
    try:
        import qrcode
        from io import BytesIO
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf)
        return HttpResponse(buf.getvalue(), content_type='image/png')
    except Exception as e:
        # Fallback to an SVG representing the URL if qrcode library is missing or fails
        svg_content = f"<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><rect width='120' height='120' fill='#f1f5f9'/><text x='10' y='60' font-size='8'>{target_url}</text></svg>"
        return HttpResponse(svg_content, content_type="image/svg+xml")


@login_required
def course_record_view(request, pk):
    """為每一課程建立一個補課錄音網頁，供教師用手機選擇堂次並錄音上傳"""
    course = get_object_or_404(Course, pk=pk)
    classes = course.classes.all().order_by('class_number')
    
    # 建立 JSON 格式的堂次狀態，供前端 JS 切換
    class_data = []
    for c in classes:
        has_rec = hasattr(c, 'recording') and bool(c.recording.audio_file)
        class_data.append({
            'id': c.id,
            'number': c.class_number,
            'subject': c.subject or f"第 {c.class_number} 堂課",
            'teacher': c.teacher or course.teachers,
            'has_recording': has_rec,
            'upload_url': reverse('education:class-upload-recording', args=[c.id]),
            'uploaded_at': c.recording.uploaded_at.strftime('%Y-%m-%d %H:%M') if has_rec else ''
        })
        
    import json
    context = {
        'course': course,
        'classes': classes,
        'class_data_json': json.dumps(class_data),
    }
    return render(request, 'education/course_record.html', context)
