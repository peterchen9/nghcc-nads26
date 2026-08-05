import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Course, CourseClass, CoursePost, CourseClassRecording, MakeUpRecord

class CourseModelTest(TestCase):
    
    def test_course_code_generation(self):
        """測試課程代號自動產生與遞增"""
        current_year = datetime.datetime.now().year
        prefix = f"RS{current_year}"
        
        # 1. 建立第一個課程
        course1 = Course.objects.create(
            subject="Python 入門",
            introduction="基礎語法",
            teachers="阿明老師",
            class_time="每週六 10:00",
            total_classes=2,
            hours_per_class=120
        )
        self.assertEqual(course1.code, f"{prefix}001")
        
        # 2. 建立第二個課程，代號應該自動遞增
        course2 = Course.objects.create(
            subject="Django 進階",
            introduction="實戰開發",
            teachers="小華老師",
            class_time="每週日 14:00",
            total_classes=3,
            hours_per_class=120
        )
        self.assertEqual(course2.code, f"{prefix}002")

    def test_course_cascade_delete(self):
        """測試刪除課程時應連帶刪除對應的課表項目"""
        course = Course.objects.create(
            subject="測試課程",
            teachers="老師",
            class_time="時間",
            total_classes=2
        )
        class1 = CourseClass.objects.create(
            course=course,
            class_number=1,
            subject="第一堂"
        )
        class2 = CourseClass.objects.create(
            course=course,
            class_number=2,
            subject="第二堂"
        )
        
        # 確認二筆課堂存在
        self.assertEqual(CourseClass.objects.filter(course=course).count(), 2)
        
        # 紀錄 ID
        course_id = course.id
        
        # 刪除課程主檔
        course.delete()
        
        # 確認連帶刪除成功
        self.assertEqual(CourseClass.objects.filter(course_id=course_id).count(), 0)


class CourseViewsTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        
    def test_views_require_login(self):
        """測試未登入時的重新導向"""
        list_url = reverse('education:course-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 302) # 重新導向至登入頁
        
    def test_course_crud_flow(self):
        """測試完整的課程 CRUD 視圖流程"""
        # 登入使用者
        self.client.login(username="testuser", password="password123")
        
        # 1. 讀取清單頁面 (目前應為空)
        list_url = reverse('education:course-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "查無任何課程規劃資料")
        
        # 2. 建立新課程
        add_url = reverse('education:course-add')
        post_data = {
            'subject': '新系統設計',
            'introduction': '這是一門設計課程。',
            'teachers': '張老師',
            'class_leader': '班長甲',
            'total_classes': '3',
            'hours_per_class': '90',
            'class_time': '每週二 19:30',
            'makeup_required': 'on', # 需補課
            
            # 堂次細項資料
            'class_date_1': '2026-08-05',
            'class_subject_1': '系統架構',
            'class_teacher_1': '張老師',
            'class_date_2': '2026-08-12',
            'class_subject_2': '資料庫設計',
            'class_teacher_2': '張老師',
            'class_date_3': '2026-08-19',
            'class_subject_3': '安全性設計',
            'class_teacher_3': '張老師',
        }
        response = self.client.post(add_url, post_data)
        
        # 應成功並重新導向至細節頁面
        self.assertEqual(response.status_code, 302)
        
        # 確認資料庫已寫入
        self.assertEqual(Course.objects.count(), 1)
        course = Course.objects.first()
        self.assertEqual(course.subject, '新系統設計')
        self.assertEqual(course.total_classes, 3)
        self.assertEqual(course.makeup_required, True)
        self.assertEqual(CourseClass.objects.filter(course=course).count(), 3)
        
        # 3. 檢視細節頁面
        detail_url = reverse('education:course-detail', args=[course.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '新系統設計')
        self.assertContains(response, '張老師')
        self.assertContains(response, '資料庫設計')
        
        # 4. 編輯課程 (縮減為二堂)
        edit_url = reverse('education:course-edit', args=[course.pk])
        edit_data = {
            'subject': '新系統設計 (更新版)',
            'introduction': '這是一門設計課程。',
            'teachers': '張老師',
            'class_leader': '班長乙',
            'total_classes': '2', # 縮減為二堂
            'hours_per_class': '90',
            'class_time': '每週二 19:30',
            # 取消補課
            
            # 堂次細項資料
            'class_date_1': '2026-08-05',
            'class_subject_1': '系統架構與設計',
            'class_teacher_1': '張老師',
            'class_date_2': '2026-08-12',
            'class_subject_2': '資料庫實作',
            'class_teacher_2': '李老師',
        }
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        
        # 重新整理資料庫
        course.refresh_from_db()
        self.assertEqual(course.subject, '新系統設計 (更新版)')
        self.assertEqual(course.class_leader, '班長乙')
        self.assertEqual(course.total_classes, 2)
        self.assertEqual(course.makeup_required, False)
        # 確認第三堂已被自動清除，剩餘二堂
        self.assertEqual(CourseClass.objects.filter(course=course).count(), 2)
        
        # 5. 刪除課程
        delete_url = reverse('education:course-delete', args=[course.pk])
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Course.objects.count(), 0)

    def test_stage2_features(self):
        """測試討論版、手機錄音上傳、安全音訊串流以及學員登記補課"""
        # 1. 準備基礎資料
        course = Course.objects.create(
            subject="測試課程丙",
            teachers="黃老師",
            class_time="每週五 10:00",
            total_classes=1,
            hours_per_class=60
        )
        c_class = CourseClass.objects.create(
            course=course,
            class_number=1,
            subject="第一堂",
            teacher="黃老師"
        )
        
        # 未登入進行討論版、錄音與補課操作應重新導向至登入頁
        board_url = reverse('education:course-board', args=[course.pk])
        response = self.client.get(board_url)
        self.assertEqual(response.status_code, 302)
        
        # 2. 登入使用者
        self.client.login(username="testuser", password="password123")
        
        # 3. 測試討論版 (POST 發表公告)
        response = self.client.post(board_url, {
            'title': '課程延期公告',
            'content': '明天因颱風放假，課堂順延一週。'
        })
        self.assertEqual(response.status_code, 302) # 重導向回討論版
        
        # 確認公告已寫入資料庫
        self.assertEqual(CoursePost.objects.filter(course=course).count(), 1)
        post = CoursePost.objects.get(course=course)
        self.assertEqual(post.title, '課程延期公告')
        self.assertEqual(post.author, self.user)
        
        # 討論版 GET 檢視
        response = self.client.get(board_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '課程延期公告')
        self.assertContains(response, '明天因颱風放假')
        
        # 4. 測試教師錄音上傳 API (POST 音訊 Blob)
        upload_url = reverse('education:class-upload-recording', args=[c_class.pk])
        mock_audio = SimpleUploadedFile(
            "my_recording.webm", 
            b"fake_webm_audio_content_datastream", 
            content_type="audio/webm"
        )
        response = self.client.post(upload_url, {'audio': mock_audio})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # 確認錄音檔在資料庫中已建立
        self.assertEqual(CourseClassRecording.objects.filter(course_class=c_class).count(), 1)
        recording = CourseClassRecording.objects.get(course_class=c_class)
        self.assertEqual(recording.filename, "my_recording.webm")
        
        # 5. 測試上傳不支援的檔案格式
        bad_file = SimpleUploadedFile(
            "script.py", 
            b"print('hello')", 
            content_type="text/x-python"
        )
        response = self.client.post(upload_url, {'audio': bad_file})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        
        # 6. 測試安全音訊串流 serve_recording_audio_view
        audio_url = reverse('education:serve-recording-audio', args=[recording.pk])
        
        # 先登出，訪客應無法存取
        self.client.logout()
        response = self.client.get(audio_url)
        self.assertEqual(response.status_code, 302)
        
        # 重新登入，學員應可存取
        self.client.login(username="testuser", password="password123")
        response = self.client.get(audio_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Content-Type'], 'audio/webm')
        
        # 7. 測試學員補課登記
        makeup_url = reverse('education:course-makeup', args=[course.pk])
        response = self.client.get(makeup_url)
        self.assertEqual(response.status_code, 200)
        
        # 登記補課
        complete_url = reverse('education:class-makeup-complete', args=[c_class.pk])
        response = self.client.post(complete_url)
        self.assertEqual(response.status_code, 302) # 重導向回學員補課頁
        
        # 確認補課紀錄已寫入
        self.assertEqual(MakeUpRecord.objects.filter(user=self.user, course_class=c_class).count(), 1)

        # 8. 測試教室欄位儲存與選單
        # 使用 classroom_id=2 模擬編輯課程，確認 classroom_name 自動被設定為 '201'
        edit_url = reverse('education:course-edit', args=[course.pk])
        edit_data = {
            'subject': '測試課程丙 - 更新教室',
            'teachers': '黃老師',
            'total_classes': '1',
            'hours_per_class': '60',
            'class_time': '每週五 10:00',
            'classroom_id': '2', # 201 教室
            'class_date_1': '2026-08-05',
            'class_subject_1': '第一堂',
            'class_teacher_1': '黃老師',
        }
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        
        course.refresh_from_db()
        self.assertEqual(course.classroom_id, 2)
        self.assertEqual(course.classroom_name, '201')

        # 9. 測試課程產出文件視圖
        docs_url = reverse('education:course-documents', args=[course.pk])
        response = self.client.get(docs_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '課程公告')
        self.assertContains(response, '教室門貼')

        # 公告列印頁
        ann_url = reverse('education:doc-announcement', args=[course.pk])
        response = self.client.get(ann_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '測試課程丙 - 更新教室')

        # 門貼列印頁
        door_url = reverse('education:doc-doorsign', args=[course.pk])
        response = self.client.get(door_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '201')

        # 回應單列印頁
        feed_url = reverse('education:doc-feedback', args=[course.pk])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '學習成效回應單')

        # 點名表列印頁
        att_url = reverse('education:doc-attendance', args=[course.pk])
        response = self.client.get(att_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '課堂點名簽到表')

        # 10. 測試課程層級教師手機錄音網頁與 QR Code
        course_rec_url = reverse('education:course-record', args=[course.pk])
        response = self.client.get(course_rec_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '教師手機課程錄音')

        course_qr_url = reverse('education:course-qrcode', args=[course.pk])
        response = self.client.get(course_qr_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers['Content-Type'] in ['image/png', 'image/svg+xml'])
