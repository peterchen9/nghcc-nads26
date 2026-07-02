"""
重新匯入 hymns.xls 到 nads25db.hymns（beat 欄位改為文字）
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
sys.path.insert(0, '/home/apps/djangocms26')
django.setup()

import xlrd
from django.db import connections

XLS_PATH = '/home/apps/cms26_flutter/hymns.xls'


def main():
    conn = connections['nads25db']
    cursor = conn.cursor()

    # 重建表，beat 改為 VARCHAR
    print('📋 重建 nads25db.hymns 表（beat 改為 VARCHAR）...')
    cursor.execute('DROP TABLE IF EXISTS hymns')
    cursor.execute('''
    CREATE TABLE hymns (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stroke_id VARCHAR(20) NOT NULL DEFAULT '',
        tune VARCHAR(20) NOT NULL DEFAULT '' COMMENT '調性',
        beat VARCHAR(50) NOT NULL DEFAULT '' COMMENT '拍號',
        hymntitle VARCHAR(200) NOT NULL DEFAULT '' COMMENT '曲名',
        source VARCHAR(500) NOT NULL DEFAULT '' COMMENT '來源',
        score_file VARCHAR(200) NOT NULL DEFAULT '' COMMENT '樂譜檔案',
        mp3_file VARCHAR(200) NOT NULL DEFAULT '' COMMENT 'MP3 檔案',
        midi VARCHAR(200) NOT NULL DEFAULT '' COMMENT 'MIDI 檔案',
        update_date VARCHAR(200) NOT NULL DEFAULT '' COMMENT '更新',
        resv1 VARCHAR(200) NOT NULL DEFAULT '' COMMENT '保留欄位1',
        resv2 VARCHAR(200) NOT NULL DEFAULT '' COMMENT '保留欄位2',
        resv3 VARCHAR(200) NOT NULL DEFAULT '' COMMENT '保留欄位3',
        resv4 VARCHAR(200) NOT NULL DEFAULT '' COMMENT '保留欄位4',
        INDEX idx_stroke_id (stroke_id),
        INDEX idx_hymntitle (hymntitle)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='詩歌資料庫'
    ''')
    print('✅ Table recreated (beat is VARCHAR)')

    wb = xlrd.open_workbook(XLS_PATH)
    sheet = wb.sheets()[0]
    total_rows = sheet.nrows - 1
    print(f'📖 讀取 {total_rows} 筆...')

    insert_sql = '''
    INSERT INTO hymns (stroke_id, tune, beat, hymntitle, source,
                       score_file, mp3_file, midi, update_date,
                       resv1, resv2, resv3, resv4)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''

    count = 0
    for r in range(1, sheet.nrows):
        stroke_id = str(sheet.cell_value(r, 0)).strip()
        tune = str(sheet.cell_value(r, 1)).strip()

        # beat 當文字處理
        beat_val = sheet.cell_value(r, 2)
        beat_type = sheet.cell_type(r, 2)
        if beat_type == 3 and beat_val:
            # Excel 的數值日期 → 直接取原始數值的字串
            beat_str = str(int(beat_val)) if beat_val == int(beat_val) else str(beat_val)
        elif beat_type == 2 and beat_val:
            beat_str = str(int(beat_val)) if beat_val == int(beat_val) else str(beat_val)
        else:
            beat_str = str(beat_val).strip() if beat_val else ''

        hymntitle = str(sheet.cell_value(r, 3)).strip()
        source = str(sheet.cell_value(r, 4)).strip()
        score_file = str(sheet.cell_value(r, 5)).strip()
        mp3_file = str(sheet.cell_value(r, 6)).strip()
        midi_val = str(sheet.cell_value(r, 7)).strip()
        update_date = str(sheet.cell_value(r, 8)).strip()
        resv1 = str(sheet.cell_value(r, 9)).strip()
        resv2 = str(sheet.cell_value(r, 10)).strip()
        resv3 = str(sheet.cell_value(r, 11)).strip()
        resv4 = str(sheet.cell_value(r, 12)).strip()

        cursor.execute(insert_sql, (
            stroke_id, tune, beat_str, hymntitle, source,
            score_file, mp3_file, midi_val, update_date,
            resv1, resv2, resv3, resv4
        ))
        count += 1
        if count % 500 == 0:
            print(f'  ⏳ {count}/{total_rows}...')

    print(f'✅ 匯入完成: {count} 筆')

    cursor.execute('SELECT COUNT(*) FROM hymns')
    print(f'📊 共 {cursor.fetchone()[0]} 筆')

    cursor.execute('SELECT id, stroke_id, tune, beat, hymntitle FROM hymns LIMIT 5')
    print('\n前 5 筆:')
    for row in cursor.fetchall():
        print(f'  {row}')


if __name__ == '__main__':
    main()
