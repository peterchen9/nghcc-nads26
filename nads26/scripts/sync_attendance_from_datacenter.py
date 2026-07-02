import pymysql

def sync():
    # Source: host's local datacenter DB on port 3306
    src_config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'peter',
        'password': 'xara5463',
        'database': 'datacenter',
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    # Target: local nads26db container on port 33069
    dst_config = {
        'host': '127.0.0.1',
        'port': 33069,
        'user': 'root',
        'password': 'xara5463',
        'database': 'nads26db',
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    print("Connecting to source (datacenter)...")
    src_conn = pymysql.connect(**src_config)
    src_cur = src_conn.cursor()
    
    print("Connecting to target (nads26db)...")
    dst_conn = pymysql.connect(**dst_config)
    dst_cur = dst_conn.cursor()
    
    print("Fetching attendance records from daka_by_person...")
    src_cur.execute("SELECT church_id, data_str, percent_year, percent_12_month, first_daka FROM daka_by_person")
    rows = src_cur.fetchall()
    print(f"Found {len(rows)} records in daka_by_person.")
    
    updated_count = 0
    for r in rows:
        church_id = r['church_id']
        data_str = r['data_str'] or ''
        percent_year = r['percent_year'] or ''
        percent_12_month = r['percent_12_month'] or ''
        first_daka = r['first_daka'] or ''
        
        # Update target members table
        dst_cur.execute("""
            UPDATE members 
            SET data_str = %s, percent_year = %s, percent_12_month = %s, first_daka = %s
            WHERE church_id = %s
        """, (data_str, percent_year, percent_12_month, first_daka, church_id))
        
        if dst_cur.rowcount > 0:
            updated_count += 1
            
    dst_conn.commit()
    print(f"Sync complete. Updated {updated_count} member attendance records in local members table.")
    
    src_cur.close()
    src_conn.close()
    dst_cur.close()
    dst_conn.close()

if __name__ == '__main__':
    sync()
