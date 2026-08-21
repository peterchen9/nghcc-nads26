import os
import time
import shutil
import subprocess
import tarfile
import threading
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, FileResponse, JsonResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_POST
import paramiko

from .models import BackupConfig, BackupHistory

# Thread lock to prevent concurrent backup operations
backup_lock = threading.Lock()

BACKUP_DIR = '/mnt/usb1t/nads26'

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def sync_backups_from_directory(backup_dir):
    """Scan the backup directory and synchronize database records with physical files."""
    if not os.path.exists(backup_dir):
        return

    try:
        files = os.listdir(backup_dir)
    except Exception:
        return

    existing_filenames = set(BackupHistory.objects.values_list('filename', flat=True))

    # 1. Register new files found in directory
    for filename in files:
        # Accept our format nads26_backup_*.tar.gz or any general .tar.gz/.zip archive
        if not (filename.endswith('.tar.gz') or filename.endswith('.zip')):
            continue

        filepath = os.path.join(backup_dir, filename)
        if not os.path.isfile(filepath):
            continue

        if filename not in existing_filenames:
            try:
                stat = os.stat(filepath)
                # Try parsing time from our format nads26_backup_YYYYMMDD_HHMMSS
                created_time = None
                if filename.startswith('nads26_backup_') and len(filename) >= 29:
                    date_str = filename[14:29]  # '20260812_085854'
                    try:
                        parsed_dt = datetime.datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                        created_time = timezone.make_aware(parsed_dt, timezone.get_current_timezone())
                    except ValueError:
                        pass

                if not created_time:
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                    created_time = timezone.make_aware(mtime, timezone.get_current_timezone())

                BackupHistory.objects.create(
                    filename=filename,
                    filepath=filepath,
                    filesize=stat.st_size,
                    status='success',
                    created_at=created_time,
                    trigger_type='manual',
                    comment='自動偵測匯入的備份檔'
                )
            except Exception:
                pass

    # 2. Prune records whose files are no longer in the directory
    for hist in BackupHistory.objects.filter(status='success'):
        if not os.path.exists(hist.filepath):
            hist.delete()

@login_required
@user_passes_test(lambda u: u.is_superuser)
def backup_dashboard(request):
    # Enforce database configuration defaults matching /mnt/usb1t/nads26 local backup
    config = BackupConfig.get_solo()
    if config.backup_path != BACKUP_DIR or config.dest_type != 'local' or not config.schedule_enabled:
        config.backup_path = BACKUP_DIR
        config.dest_type = 'local'
        config.schedule_enabled = True  # Keep enabled so scheduled tasks run
        config.save()

    # Synchronize backup files with physical directory
    sync_backups_from_directory(BACKUP_DIR)

    # Check backup directory connection status
    mount_exists = os.path.exists(BACKUP_DIR)
    mount_writable = os.access(BACKUP_DIR, os.W_OK) if mount_exists else False

    disk_info = None
    if mount_exists:
        try:
            total, used, free = shutil.disk_usage(BACKUP_DIR)
            disk_info = {
                'total': format_size(total),
                'used': format_size(used),
                'free': format_size(free),
                'percent': f"{(used / total) * 100:.1f}%",
                'percent_num': int((used / total) * 100) if total > 0 else 0
            }
        except Exception:
            pass

    history = BackupHistory.objects.all().order_by('-created_at')

    # Format size for display
    for item in history:
        item.formatted_size = format_size(item.filesize) if item.filesize else "0 B"

    return render(request, 'backup/backup_dashboard.html', {
        'config': config,
        'history': history,
        'mount_exists': mount_exists,
        'mount_writable': mount_writable,
        'disk_info': disk_info,
        'backup_dir_path': BACKUP_DIR,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def save_config(request):
    # Legacy handler - redirection
    return redirect('backup-dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def update_comment(request, pk):
    history = get_object_or_404(BackupHistory, pk=pk)
    history.comment = request.POST.get('comment', '').strip()
    history.save()
    return JsonResponse({'status': 'success'})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_backup(request, pk):
    history = get_object_or_404(BackupHistory, pk=pk)

    # Delete local file
    if os.path.exists(history.filepath):
        try:
            os.remove(history.filepath)
        except Exception:
            pass

    history.delete()
    return redirect('backup-dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def download_backup(request, pk):
    history = get_object_or_404(BackupHistory, pk=pk)

    # Verify path is safe to prevent path traversal
    resolved_path = os.path.abspath(history.filepath)
    custom_dir = os.path.abspath(BACKUP_DIR)

    if not resolved_path.startswith(custom_dir):
        raise Http404("無權存取該檔案路徑。")

    if not os.path.exists(resolved_path):
        raise Http404("備份檔案不存在。")

    response = FileResponse(open(resolved_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{history.filename}"'
    return response

@login_required
@user_passes_test(lambda u: u.is_superuser)
def view_log(request, pk):
    history = get_object_or_404(BackupHistory, pk=pk)
    return JsonResponse({'log': history.log})

# Generator helper to perform the backup process and stream log messages to client
def run_backup_generator(trigger_type='manual'):
    log_messages = []

    def log(message):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {message}"
        log_messages.append(line)
        return f"data: {line}\n\n"

    # Acquire lock to prevent concurrent runs
    if not backup_lock.acquire(blocking=False):
        yield f"data: [ERROR] 備份作業已在進行中，請稍後再試。\n\n"
        return

    history_record = None
    local_tar_path = None
    filename = None

    try:
        yield log("========== 開始備份作業 ==========")

        # Determine paths
        local_archive_root = BACKUP_DIR
        if not os.path.exists(local_archive_root):
            yield log(f"建立備份目錄: {local_archive_root}...")
            os.makedirs(local_archive_root, exist_ok=True)

        # Temp dir for db dump
        temp_dir = os.path.join(local_archive_root, 'temp_dump')
        os.makedirs(temp_dir, exist_ok=True)

        now = datetime.datetime.now()
        timestamp_str = now.strftime('%Y%m%d_%H%M%S')
        filename = f"nads26_backup_{timestamp_str}.tar.gz"
        local_tar_path = os.path.join(local_archive_root, filename)

        # 1. Initialize History Record
        history_record = BackupHistory.objects.create(
            filename=filename,
            filepath=local_tar_path,
            filesize=0,
            status='pending',
            trigger_type=trigger_type,
            log=''
        )

        # 2. Database Export
        yield log("正在導出資料庫...")
        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']

        sql_dump_file = os.path.join(temp_dir, "db.sql")

        if 'mysql' in db_engine:
            db_name = db_settings['NAME']
            db_user = db_settings['USER']
            db_password = db_settings['PASSWORD']
            db_host = db_settings['HOST']
            db_port = db_settings['PORT']

            # Construct mysqldump command securely as list (prevents shell injection)
            cmd = ["mysqldump", "-h", db_host, "-u", db_user, f"-p{db_password}", "--skip-ssl", db_name]
            if db_port:
                cmd.extend(["-P", str(db_port)])

            yield log(f"執行 MySQL 資料庫導出 (主機: {db_host})...")
            with open(sql_dump_file, 'w') as f_out:
                process = subprocess.Popen(cmd, stdout=f_out, stderr=subprocess.PIPE, text=True)
                stderr_output = process.communicate()[1]

            if process.returncode != 0:
                raise Exception(f"mysqldump 失敗 (代碼 {process.returncode}): {stderr_output}")
            yield log("資料庫導出成功。")

        else:
            # SQLite fallback
            sqlite_path = db_settings['NAME']
            yield log(f"檢測到 SQLite 資料庫，複製 db 檔案: {sqlite_path}...")
            if os.path.exists(sqlite_path):
                shutil.copy2(sqlite_path, sql_dump_file)
                yield log("SQLite 檔案複製成功。")
            else:
                yield log("[WARNING] 未找到 SQLite 資料庫檔案。")

        # 3. Packaging Project Files
        yield log("正在打包專案目錄及資料庫...")

        exclude_dirs = {'mysql_data', 'backups', 'private_media', '__pycache__', '.git', '.idea', 'venv', '.venv', 'staticfiles'}

        with tarfile.open(local_tar_path, "w:gz") as tar:
            # Add database dump at the root of the archive
            if os.path.exists(sql_dump_file):
                tar.add(sql_dump_file, arcname="db.sql")

            # Add project directory source files
            file_count = 0
            for root, dirs, files in os.walk(settings.BASE_DIR):
                # Filter directories in-place to exclude unwanted folders
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                # Exclude NAS mount directory specifically to prevent OOM
                rel_root = os.path.relpath(root, settings.BASE_DIR).replace('\\', '/')
                if rel_root == 'media':
                    dirs[:] = [d for d in dirs if d != 'NADS_FileCenter']

                for file in files:
                    if file.endswith('.tar.gz') or file.endswith('.sql'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.join("project", os.path.relpath(file_path, settings.BASE_DIR))
                    tar.add(file_path, arcname=arcname)

                    file_count += 1
                    if file_count % 500 == 0:
                        yield log(f"已打包 {file_count} 個檔案...")

        yield log(f"檔案打包完成，共打包 {file_count} 個檔案。")

        # Clean up temp dump folder
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        filesize = os.path.getsize(local_tar_path)
        history_record.filesize = filesize
        yield log(f"備份壓縮檔大小: {format_size(filesize)}")
        yield log(f"備份檔案已直接儲存於目錄: {local_archive_root}")

        # 4. Apply Retention Policy
        yield log("正在執行備份保留規則清理...")
        config = BackupConfig.get_solo()
        successful_backups = BackupHistory.objects.filter(status='success', trigger_type=trigger_type).order_by('-created_at')

        active_list = list(successful_backups)

        if config.retention_type == 'count':
            keep_count = config.retention_value
            yield log(f"保留規則: 保留最新 {keep_count} 份備份。")
            if len(active_list) >= keep_count:
                to_prune = active_list[keep_count - 1:]
                for old_rec in to_prune:
                    if os.path.exists(old_rec.filepath):
                        try:
                            os.remove(old_rec.filepath)
                            yield log(f"已刪除過期本地備份檔案: {old_rec.filename}")
                        except Exception as ex:
                            yield log(f"[WARNING] 刪除本地過期檔案失敗: {ex}")
                    old_rec.delete()
        else:
            keep_days = config.retention_value
            yield log(f"保留規則: 保留 {keep_days} 天內的備份。")
            cutoff = timezone.now() - datetime.timedelta(days=keep_days)
            to_prune = BackupHistory.objects.filter(status='success', trigger_type=trigger_type, created_at__lt=cutoff)

            for old_rec in to_prune:
                if os.path.exists(old_rec.filepath):
                    try:
                        os.remove(old_rec.filepath)
                        yield log(f"已刪除過期本地備份檔案: {old_rec.filename}")
                    except Exception as ex:
                        yield log(f"[WARNING] 刪除本地過期檔案失敗: {ex}")
                old_rec.delete()

        # 5. Mark Success
        yield log("========== 備份作業成功完成 ==========")
        history_record.status = 'success'

    except Exception as e:
        yield log(f"[ERROR] 備份過程中發生錯誤: {str(e)}")
        yield log("========== 備份作業失敗 ==========")
        if history_record:
            history_record.status = 'failed'

        # Remove partial local file if failure
        if local_tar_path and os.path.exists(local_tar_path):
            try:
                os.remove(local_tar_path)
            except Exception:
                pass
    finally:
        backup_lock.release()

        # Save logs into history database
        if history_record:
            history_record.log = "\n".join(log_messages)
            history_record.save()

@login_required
@user_passes_test(lambda u: u.is_superuser)
def run_backup(request):
    """View to initiate an immediate backup and stream progress logs."""
    response = StreamingHttpResponse(
        run_backup_generator(trigger_type='manual'),
        content_type='text/event-stream'
    )
    # Disable caching for Server-Sent Events
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
