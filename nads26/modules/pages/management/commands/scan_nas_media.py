import json
import paramiko
from django.core.management.base import BaseCommand
from modules.pages.models import MediaCollection

class Command(BaseCommand):
    help = 'Scans the NAS at 192.168.16.127 via SSH and updates MediaCollection records'

    def handle(self, *args, **options):
        self.stdout.write("Connecting to NAS 192.168.16.127 via SSH...")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('192.168.16.127', username='peter', password='Gala1051#', timeout=30)
        except Exception as e:
            self.stderr.write(f"Failed to connect to NAS: {e}")
            return

        remote_script = """
import os, subprocess, re, json
def get_duration(filepath):
    try:
        p = subprocess.Popen(["ffmpeg", "-i", filepath], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = p.communicate()
        m = re.search(r"Duration:\\s*(\\d{2}:\\d{2}:\\d{2})", err.decode("utf-8", errors="ignore"))
        return m.group(1) if m else "未知"
    except: return "未知"
res = []
skip_prefixes = ('@', '#')
for root, dirs, files in os.walk("/volume1"):
    dirs[:] = [d for d in dirs if not d.startswith(skip_prefixes)]
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in (".mp4", ".avi", ".mkv", ".mp3"):
            path = os.path.join(root, f)
            try:
                size = os.path.getsize(path)
            except:
                size = 0
            res.append({
                "filename": f,
                "path": path,
                "duration": get_duration(path),
                "size": size,
                "file_type": ext[1:]
            })
print(json.dumps(res, ensure_ascii=False))
"""
        
        self.stdout.write("Running remote scan script on NAS...")
        try:
            stdin, stdout, stderr = client.exec_command("python3")
            stdin.write(remote_script)
            stdin.close()
            
            output = stdout.read().decode('utf-8').strip()
            err_output = stderr.read().decode('utf-8').strip()
            client.close()
            
            if err_output:
                self.stderr.write(f"Remote script stderr: {err_output}")
            
            if not output:
                self.stderr.write("No output received from the remote script.")
                return
                
            media_files = json.loads(output)
        except Exception as e:
            self.stderr.write(f"Error during scanning: {e}")
            return
            
        self.stdout.write(f"Scan complete. Found {len(media_files)} files. Updating database...")
        
        try:
            MediaCollection.objects.all().delete()
            
            batch = [
                MediaCollection(
                    filename=item['filename'],
                    path=item['path'],
                    duration=item['duration'],
                    size=item['size'],
                    file_type=item['file_type']
                )
                for item in media_files
            ]
            MediaCollection.objects.bulk_create(batch)
            self.stdout.write(self.style.SUCCESS(f"Successfully updated database with {len(batch)} media files!"))
        except Exception as e:
            self.stderr.write(f"Failed to update database: {e}")
