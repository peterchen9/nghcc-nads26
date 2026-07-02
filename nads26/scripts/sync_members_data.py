import os
import sys
import django
import pymysql
from datetime import datetime

# Setup django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from modules.eureka.models import Member

def parse_date(date_str):
    if not date_str or date_str.strip() in ('', '0000-00-00', 'None', 'null'):
        return None
    date_str = date_str.strip().split(' ')[0] # take date part if datetime
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%Y%m%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def parse_int(val, default=None):
    if not val or str(val).strip() in ('', 'None', 'null'):
        return default
    try:
        return int(float(str(val).strip()))
    except ValueError:
        return default

def sync():
    # Remote DB config
    remote_config = {
        'host': '172.20.60.241',
        'port': 3306,
        'user': 'peter',
        'password': 'xara5463',
        'database': 'nads25db_raw',
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    print("Connecting to remote nads25db_raw database...")
    conn = pymysql.connect(**remote_config)
    cur = conn.cursor()
    
    print("Fetching records from imports_person...")
    cur.execute("SELECT * FROM imports_person")
    rows = cur.fetchall()
    print(f"Found {len(rows)} records in imports_person.")
    
    created_count = 0
    updated_count = 0
    
    for r in rows:
        church_id = int(r['church_id'])
        
        # Mapping values
        name = r['name'].strip() if r['name'] else ''
        section = r['section'].strip() if r['section'] else ''
        mobile1 = r['mobile1'].strip() if r['mobile1'] else ''
        email1 = r['email1'].strip() if r['email1'] else ''
        family1 = r['family1'].strip() if r['family1'] else ''
        gender = r['gender'].strip() if r['gender'] else ''
        address = r['address'].strip() if r['address'] else ''
        birthday = parse_date(r['birthday'])
        join_date = parse_date(r['joindate'])
        baptized = r['baptized'].strip() if r['baptized'] else ''
        presence = parse_int(r['presence'], default=0)
        note = r['note']
        family_id = parse_int(r['family_id'])
        dataindate = parse_date(r['dataindate'])
        marriage = r['marriage'].strip() if r['marriage'] else ''
        phone_h = r['telh1'].strip() if r['telh1'] else ''
        phone_o = r['telho'].strip() if r['telho'] else ''
        car_number = r['reserved2'].strip() if r['reserved2'] else ''
        line_id = r['reserved3'].strip() if r['reserved3'] else ''
        
        # Check if exists in local
        try:
            m = Member.objects.get(church_id=church_id)
            # Update fields
            m.name = name
            m.section = section
            m.mobile1 = mobile1
            m.email1 = email1
            m.family1 = family1
            m.gender = gender
            m.address = address
            m.birthday = birthday
            m.join_date = join_date
            m.baptized = baptized
            m.presence = presence
            m.note = note
            m.family_id = family_id
            m.dataindate = dataindate
            m.marriage = marriage
            m.phone_h = phone_h
            m.phone_o = phone_o
            m.car_number = car_number
            m.line_id = line_id
            m.save()
            updated_count += 1
        except Member.DoesNotExist:
            # Create new
            Member.objects.create(
                church_id=church_id,
                name=name,
                section=section,
                mobile1=mobile1,
                email1=email1,
                family1=family1,
                gender=gender,
                address=address,
                birthday=birthday,
                join_date=join_date,
                baptized=baptized,
                presence=presence,
                note=note,
                family_id=family_id,
                dataindate=dataindate,
                marriage=marriage,
                phone_h=phone_h,
                phone_o=phone_o,
                car_number=car_number,
                line_id=line_id
            )
            created_count += 1
            
    print(f"Sync complete. Updated: {updated_count}, Created: {created_count}")
    cur.close()
    conn.close()

if __name__ == '__main__':
    sync()
