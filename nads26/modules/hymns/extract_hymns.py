"""
詩歌 HTM 提取腳本
1. 在 nads25db.hymns 表新增 lyric, simplescore, midistr, htm_file 欄位
2. 掃描 /home/apps/hymn_files/htm/ 下的 .htm 檔
3. 根據檔名開頭 6 碼 (stroke_id) 匹配 hymns 記錄
4. 從 HTM 提取歌詞 (標楷體 48pt) 和簡譜 (SimpMusic Base)
5. 將簡譜轉為 MIDI 字串
6. 更新 hymns 表
"""
import os, sys, re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
sys.path.insert(0, '/home/apps/djangocms26')

import django
django.setup()
from django.db import connections

HTM_DIR = '/home/apps/hymn_files/htm'

# ═══════════════════════════════════════
# SimpMusic Base → 簡譜數字音符 映射
# ═══════════════════════════════════════
# 根據 簡譜製作方法1.jpg/2.jpg
# Row 1: 1234567 890-=
SIMPMUSIC_BASE_MAP = {
    # --- 基本音 (數字列 1-7) ---
    '1': '1', '2': '2', '3': '3', '4': '4',
    '5': '5', '6': '6', '7': '7',
    '9': '.', '0': '0', '-': '-', '=': 'n8',
    # --- 高八度 Shift+1-7 => ! @ # $ % ^ & ---
    '!': '1+', '@': '2+', '#': '3+', '$': '4+',
    '%': '5+', '^': '6+', '&': '7+',
    '*': '4+', '(': '_', ')': '_',
    # --- 八分音（下加一線 q-u）---
    'q': '1_', 'w': '2_', 'e': '3_', 'r': '4_',
    't': '5_', 'y': '6_', 'u': '7_',
    'i': '_',  # 底線延續
    'o': '.', 'p': '0_',
    '[': '|:', ']': ':|', '\\': '||',
    # --- 十六分音（雙下加線 a-j）---
    'a': '1__', 's': '2__', 'd': '3__', 'f': '4__',
    'g': '5__', 'h': '6__', 'j': '7__',
    'k': '_', 'l': '.', "'": 'n8',
    # --- 低八度+十六分 Shift+a-j => A-J ---
    'A': '1-__', 'S': '2-__', 'D': '3-__', 'F': '4-__',
    'G': '5-__', 'H': '6-__', 'J': '7-__',
    'K': '#', 'L': 'b', ':': 'b', '"': 'n',
    # --- 三十二分音 z-m ---
    'z': '1___', 'x': '2___', 'c': '3___', 'v': '4___',
    'b': '5___', 'n': '6___', 'm': '7___',
    ',': '_', '.': '.', '/': '0',
    # --- 低八度+三十二 Shift+z-m => Z-M ---
    'Z': '1-___', 'X': '2-___', 'C': '3-___', 'V': '4-___',
    'B': '5-___', 'N': '6-___', 'M': '7-___',
    '<': 'J', '>': 'J', '?': 'dw',
    # --- 特殊 ---
    '|': '|',  # 小節線
    ' ': ' ',  # 空格
}


def extract_from_htm(filepath):
    """從 HTM 檔提取歌詞和簡譜"""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
    except Exception as e:
        return None, None, str(e)

    # 嘗試 big5/cp950 編碼
    for enc in ['big5', 'cp950', 'utf-8']:
        try:
            text = raw.decode(enc, errors='replace')
            break
        except:
            text = raw.decode('utf-8', errors='replace')

    # 按 <p 分割段落
    paragraphs = text.split('<p ')

    lyrics = []
    scores = []

    for p in paragraphs:
        # 找所有 span
        span_re = re.compile(r"<span[^>]*?style='([^']*)'[^>]*?>([^<]*)", re.DOTALL)
        p_lyrics = []
        p_scores = []

        for m in span_re.finditer(p):
            style, content = m.group(1), m.group(2)
            clean = content.replace('&nbsp;', ' ').replace('&amp;', '&').strip()
            if not clean:
                continue

            if 'SimpMusic Base' in style:
                p_scores.append(clean)
            elif '標楷體' in style:
                # 檢查 font-size >= 40 (歌詞大字)
                fs = re.search(r'font-size:\s*([\d.]+)', style)
                if fs and float(fs.group(1)) >= 40:
                    p_lyrics.append(clean)

        if p_lyrics:
            lyrics.append(''.join(p_lyrics))
        if p_scores:
            scores.append(' '.join(p_scores))

    lyric_text = '\n'.join(lyrics)
    score_text = '\n'.join(scores)

    return lyric_text, score_text, None


def score_to_midi_str(score_text):
    """
    將簡譜字串轉為 MIDI 音符序列字串
    格式: "C4 D4 E4 | F4 G4 ..."
    """
    if not score_text:
        return ''

    # 簡譜數字到 MIDI 音符名的映射（C 大調）
    note_map = {
        '1': 'C', '2': 'D', '3': 'E', '4': 'F',
        '5': 'G', '6': 'A', '7': 'B', '0': 'R'  # R = 休止
    }

    midi_notes = []

    for line in score_text.split('\n'):
        for char in line:
            mapped = SIMPMUSIC_BASE_MAP.get(char, '')
            if not mapped or mapped in ('_', ' ', '.'):
                continue

            if mapped == '|':
                midi_notes.append('|')
                continue
            if mapped == '-':
                midi_notes.append('-')
                continue

            # 解析音高
            base_note = ''
            octave = 4  # 預設中央 C 的八度

            # 判斷修飾
            note_num = ''
            for c in mapped:
                if c.isdigit():
                    note_num = c
                elif c == '+':
                    octave = 5  # 高八度
                elif c == '-':
                    octave = 3  # 低八度

            if note_num in note_map:
                n = note_map[note_num]
                if n == 'R':
                    midi_notes.append('R')
                else:
                    midi_notes.append(f'{n}{octave}')

    return ' '.join(midi_notes)


def main():
    conn = connections['nads25db']
    cursor = conn.cursor()

    # Step 1: 新增欄位
    print('📋 新增欄位 lyric, simplescore, midistr, htm_file ...')
    for col, col_type in [
        ('lyric', 'TEXT'),
        ('simplescore', 'TEXT'),
        ('midistr', 'TEXT'),
        ('htm_file', 'VARCHAR(500)'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE hymns ADD COLUMN {col} {col_type} DEFAULT NULL")
            print(f'  ✅ 新增 {col}')
        except Exception as e:
            if 'Duplicate column' in str(e):
                print(f'  ⏭ {col} 已存在')
            else:
                print(f'  ⚠ {col}: {e}')

    # Step 2: 讀取 hymns 表，建立 stroke_id → id 映射
    cursor.execute('SELECT id, stroke_id, hymntitle FROM hymns')
    rows = cursor.fetchall()
    stroke_map = {}
    for rid, sid, title in rows:
        key = sid.strip()
        if key not in stroke_map:
            stroke_map[key] = (rid, title)
    print(f'\n📊 hymns 表共 {len(rows)} 筆，唯一 stroke_id {len(stroke_map)} 個')

    # Step 3: 掃描 HTM 檔案
    print(f'\n📂 掃描 {HTM_DIR} ...')
    htm_files = []
    for f in os.listdir(HTM_DIR):
        if f.lower().endswith('.htm') or f.lower().endswith('.html'):
            htm_files.append(f)
    htm_files.sort()
    print(f'  找到 {len(htm_files)} 個 HTM 檔')

    # Step 4: 匹配並提取
    matched = 0
    unmatched = 0
    extracted = 0
    errors_list = []

    for fname in htm_files:
        # 取前6碼作為 stroke_id
        m = re.match(r'^(\d{6})', fname)
        if not m:
            unmatched += 1
            continue

        stroke_id = m.group(1)

        if stroke_id not in stroke_map:
            unmatched += 1
            errors_list.append(f'  未匹配: {fname} (stroke_id={stroke_id})')
            continue

        hymn_id, hymn_title = stroke_map[stroke_id]
        matched += 1

        # 提取歌詞和簡譜
        filepath = os.path.join(HTM_DIR, fname)
        lyric, score, err = extract_from_htm(filepath)

        if err:
            errors_list.append(f'  解析錯誤: {fname}: {err}')
            continue

        # 轉 MIDI 字串
        midi_str = score_to_midi_str(score)

        # 歌詞取前 500 字，簡譜取前 2000 字
        lyric_trunc = lyric[:2000] if lyric else ''
        score_trunc = score[:5000] if score else ''
        midi_trunc = midi_str[:5000] if midi_str else ''

        # 更新 DB
        cursor.execute(
            '''UPDATE hymns
               SET lyric=%s, simplescore=%s, midistr=%s, htm_file=%s
               WHERE id=%s''',
            (lyric_trunc, score_trunc, midi_trunc, fname, hymn_id)
        )
        extracted += 1

        if extracted % 100 == 0:
            print(f'  ⏳ 已處理 {extracted}/{matched} ...')

    print(f'\n✅ 完成！')
    print(f'  匹配: {matched}')
    print(f'  提取: {extracted}')
    print(f'  未匹配: {unmatched}')

    if errors_list:
        print(f'\n⚠ 問題清單 ({len(errors_list)} 個):')
        for e in errors_list[:20]:
            print(e)
        if len(errors_list) > 20:
            print(f'  ... 以及 {len(errors_list) - 20} 個更多')

    # 驗證
    cursor.execute("SELECT COUNT(*) FROM hymns WHERE lyric IS NOT NULL AND lyric != ''")
    print(f'\n📊 有歌詞的記錄: {cursor.fetchone()[0]}')
    cursor.execute("SELECT COUNT(*) FROM hymns WHERE simplescore IS NOT NULL AND simplescore != ''")
    print(f'📊 有簡譜的記錄: {cursor.fetchone()[0]}')
    cursor.execute("SELECT COUNT(*) FROM hymns WHERE midistr IS NOT NULL AND midistr != ''")
    print(f'📊 有 MIDI 字串的記錄: {cursor.fetchone()[0]}')

    # 範例
    cursor.execute("SELECT id, stroke_id, hymntitle, LEFT(lyric,30), LEFT(midistr,50) FROM hymns WHERE lyric != '' LIMIT 5")
    print('\n前 5 筆範例:')
    for row in cursor.fetchall():
        print(f'  [{row[1]}] {row[2][:20]} | 歌詞: {row[3]} | MIDI: {row[4]}')


if __name__ == '__main__':
    main()
