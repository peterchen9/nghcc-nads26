import os
import sys
import django
from openpyxl import Workbook

# Setup django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from modules.eureka.models import Member

def main():
    print("Querying section and family1 mappings...")
    # Query distinct pairs of non-empty section and family1
    mappings = Member.objects.values('section', 'family1').distinct().order_by('section', 'family1')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "牧區小組對應表"
    
    headers = ["牧區 (section)", "小組 (family1)"]
    ws.append(headers)
    
    count = 0
    for item in mappings:
        sec = item['section'].strip() if item['section'] else ''
        fam = item['family1'].strip() if item['family1'] else ''
        if sec or fam:
            ws.append([sec, fam])
            count += 1
            
    output_path = os.path.join(BASE_DIR, 'section_family_mapping.xlsx')
    wb.save(output_path)
    print(f"Excel file created successfully with {count} mappings at: {output_path}")

if __name__ == '__main__':
    main()
