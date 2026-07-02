import json
import os
import platform
import re
import select
import socket
import ssl
import struct
import subprocess
import time
from datetime import datetime, timedelta
from http.cookiejar import CookieJar
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, HTTPCookieProcessor, Request, build_opener
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

TZ = ZoneInfo('Asia/Taipei')
UTC = ZoneInfo('UTC')
DEVICE_BASE_URL = getattr(settings, 'NU840_BASE_URL', 'https://app.nghcc.org.tw:8443')
DEVICE_USERNAME = getattr(settings, 'NU840_USERNAME', 'peter')
DEVICE_PASSWORD = getattr(settings, 'NU840_PASSWORD', 'xara5463')
LAN_HOST_TABLE = 'network_lan_host'
LAN_SNAPSHOT_TABLE = 'network_lan_snapshot'
SCAN_MAX_AGE = timedelta(hours=1)
WLAN_AP_KEYWORDS = (
    'wifi', 'wi-fi', 'wlan', 'access point', 'router', 'totolink',
    'tp-link', 'tplink', 'miwifi', 'cht wi-fi', 'bkwifi', 'nbg',
)
WLAN_AP_NAME_PATTERNS = (
    re.compile(r'(^|[-_\s])ap($|[-_\s0-9])', re.I),
    re.compile(r'^\d+[fb]($|[-_a-z0-9])', re.I),
    re.compile(r'^[b]1($|[-_\sa-z0-9])', re.I),
    re.compile(r'^\d+fr\d+', re.I),
)

INTERFACE_NAMES = {
    'zone0': 'LAN',
    'zone1': 'WAN1',
    'zone2': 'WAN2',
    'zone3': 'LAN2',
    'ppp4001': 'WAN1 PPPOE',
}


class TableParser(HTMLParser):
    def __init__(self, table_id=None):
        super().__init__(convert_charrefs=True)
        self.table_id = table_id
        self.in_target_table = table_id is None
        self.table_depth = 0
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = []
        self.rows = []
        self.current_cell_html = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'table' and (self.table_id is None or attrs_dict.get('id') == self.table_id):
            self.in_target_table = True
            self.table_depth += 1
        elif tag == 'table' and self.in_target_table:
            self.table_depth += 1

        if not self.in_target_table:
            return
        if tag == 'tr':
            self.in_row = True
            self.current_row = []
        elif tag in {'td', 'th'} and self.in_row:
            self.in_cell = True
            self.current_cell = []
            self.current_cell_html = []
        elif self.in_cell:
            self.current_cell_html.append(self.get_starttag_text() or '')

    def handle_endtag(self, tag):
        if self.in_target_table and self.in_cell:
            self.current_cell_html.append(f'</{tag}>')
        if tag in {'td', 'th'} and self.in_cell:
            text = ' '.join(''.join(self.current_cell).split())
            html = ''.join(self.current_cell_html)
            self.current_row.append({'text': text, 'html': html})
            self.in_cell = False
        elif tag == 'tr' and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_row = False
        elif tag == 'table' and self.in_target_table:
            self.table_depth -= 1
            if self.table_depth <= 0 and self.table_id is not None:
                self.in_target_table = False

    def handle_data(self, data):
        if self.in_target_table and self.in_cell:
            self.current_cell.append(data)


def _dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _ensure_tables():
    with connection.cursor() as cursor:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {LAN_HOST_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ip VARCHAR(45) NOT NULL,
                mac VARCHAR(32) NOT NULL DEFAULT '',
                hostname VARCHAR(255) NOT NULL DEFAULT '',
                os_name VARCHAR(255) NOT NULL DEFAULT '',
                interface_name VARCHAR(80) NOT NULL DEFAULT '',
                status VARCHAR(40) NOT NULL DEFAULT '',
                last_seen DATETIME NULL,
                note TEXT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE KEY uniq_network_lan_host_ip_mac (ip, mac),
                INDEX idx_network_lan_host_status (status),
                INDEX idx_network_lan_host_seen (last_seen)
            )
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {LAN_SNAPSHOT_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                scanned_at DATETIME NOT NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'ok',
                error_message TEXT NULL,
                bandwidth_json LONGTEXT NULL,
                host_count INT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                INDEX idx_network_lan_snapshot_scanned_at (scanned_at)
            )
        """)


def _request(opener, path, data=None):
    url = f'{DEVICE_BASE_URL}{path}'
    body = urlencode(data).encode('utf-8') if data else None
    headers = {'User-Agent': 'NGHCC LAN Host Scanner/1.0'}
    request = Request(url, data=body, headers=headers)
    with opener.open(request, timeout=20) as response:
        return response.read().decode('utf-8', errors='replace')


def _login():
    context = ssl._create_unverified_context()
    opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=context))
    _request(opener, '/index.php', {
        'ulogin': DEVICE_USERNAME,
        'upasswd': DEVICE_PASSWORD,
        'lang': 'big5',
        'OK': '系統登入',
    })
    return opener


def _parse_interfaces(welcome_html):
    rows = []
    pattern = re.compile(
        r"<tr class=\"tbMark02\"[^>]*open_eth_tip\(event,\s*'([^']+)'[^)]*'([^']*)'\)[^>]*>\s*"
        r"<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>",
        re.S,
    )
    for dev, label, dev_cell, status_html, address in pattern.findall(welcome_html):
        rows.append({
            'device': _clean_text(dev_cell) or dev,
            'name': label or INTERFACE_NAMES.get(dev, dev),
            'address': _clean_text(address),
            'link': 'link_on' in status_html,
            'tx_bps': 0,
            'rx_bps': 0,
            'tx_label': '0 bps',
            'rx_label': '0 bps',
        })
    return rows


def _clean_text(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', value or '')).strip()


def _format_bps(bytes_per_second):
    try:
        value = float(bytes_per_second)
    except (TypeError, ValueError):
        return '0 Kbps'
    if value < 125000:
        return f'{round(value / 125)} Kbps'
    if value < 125000000:
        return f'{round(value / 1250) / 100:.2f} Mbps'
    return f'{round(value / 1250000) / 100:.2f} Gbps'


def _parse_bandwidth(diff_text, interfaces):
    by_device = {item['device']: item for item in interfaces}
    for line in diff_text.splitlines():
        parts = line.strip().split(',')
        if len(parts) < 3:
            continue
        dev = parts[0]
        if dev not in by_device:
            continue
        rx_bps = _safe_float(parts[1])
        tx_bps = _safe_float(parts[2])
        by_device[dev].update({
            'rx_bps': rx_bps,
            'tx_bps': tx_bps,
            'rx_label': _format_bps(rx_bps),
            'tx_label': _format_bps(tx_bps),
        })
    return interfaces


def _parse_realtime_fetch(text):
    data = {}
    for line in text.splitlines():
        parts = line.strip().split('|')
        if len(parts) != 4:
            continue
        data[parts[0]] = {
            'time': _safe_float(parts[1]),
            'tx': _safe_float(parts[2]),
            'rx': _safe_float(parts[3]),
        }
    return data


def _calculate_realtime_bandwidth(first_text, second_text, interfaces):
    first = _parse_realtime_fetch(first_text)
    second = _parse_realtime_fetch(second_text)
    for item in interfaces:
        dev = item['device']
        if dev not in first or dev not in second:
            continue
        elapsed = max(second[dev]['time'] - first[dev]['time'], 1)
        tx_bps = max(second[dev]['tx'] - first[dev]['tx'], 0) / elapsed
        rx_bps = max(second[dev]['rx'] - first[dev]['rx'], 0) / elapsed
        item.update({
            'rx_bps': rx_bps,
            'tx_bps': tx_bps,
            'rx_label': _format_bps(rx_bps),
            'tx_label': _format_bps(tx_bps),
        })
    return interfaces


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _parse_hosts(html):
    parser = TableParser('tb001')
    parser.feed(html)
    hosts = []
    for row in parser.rows[1:]:
        if len(row) < 8:
            continue
        status_html = row[6]['html']
        is_alive = 'link_on' in status_html
        if not is_alive:
            continue
        hosts.append({
            'hostname': row[2]['text'],
            'ip': row[3]['text'],
            'mac': row[4]['text'].lower(),
            'interface_name': row[5]['text'],
            'status': 'alive',
            'os_name': '',
            'last_seen': row[7]['text'],
        })
    return hosts


def _fetch_device_snapshot():
    opener = _login()
    welcome_html = _request(opener, '/Program/System/Sys_Welcome.php')
    first_fetch = _request(opener, '/Program/System/get_dev_realtime_multi_fetch.php')
    time.sleep(1.2)
    second_fetch = _request(opener, '/Program/System/get_dev_realtime_multi_fetch.php')
    hosts_html = _request(
        opener,
        '/Program/Logs/Lanipmac_List.php?by_subnet=All&by_interface=All&offset=0&slice=500&tbKey=status&tbOrder=DESC',
    )
    interfaces = _calculate_realtime_bandwidth(first_fetch, second_fetch, _parse_interfaces(welcome_html))
    hosts = _parse_hosts(hosts_html)
    return interfaces, hosts


def _parse_seen(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ)
    except ValueError:
        return None


def _as_aware(value):
    if value and timezone.is_naive(value):
        return timezone.make_aware(value, UTC)
    return value


def _save_scan(interfaces, hosts, status='ok', error_message=''):
    _ensure_tables()
    now = timezone.now()
    with connection.cursor() as cursor:
        if status == 'ok':
            cursor.execute(f"""
                UPDATE {LAN_HOST_TABLE}
                SET status = 'offline', updated_at = %s
                WHERE status = 'alive'
            """, [now])
        for host in hosts:
            last_seen = _parse_seen(host.get('last_seen')) or now
            cursor.execute(f"""
                INSERT INTO {LAN_HOST_TABLE}
                    (ip, mac, hostname, os_name, interface_name, status, last_seen, note, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, '', %s, %s)
                ON DUPLICATE KEY UPDATE
                    hostname = VALUES(hostname),
                    os_name = VALUES(os_name),
                    interface_name = VALUES(interface_name),
                    status = VALUES(status),
                    last_seen = VALUES(last_seen),
                    updated_at = VALUES(updated_at)
            """, [
                host['ip'], host['mac'], host['hostname'], host['os_name'],
                host['interface_name'], host['status'], last_seen, now, now,
            ])
        cursor.execute(f"""
            INSERT INTO {LAN_SNAPSHOT_TABLE}
                (scanned_at, status, error_message, bandwidth_json, host_count, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [now, status, error_message, json.dumps(interfaces, ensure_ascii=False), len(hosts), now])


def _latest_snapshot():
    _ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT scanned_at, status, error_message, bandwidth_json, host_count
            FROM {LAN_SNAPSHOT_TABLE}
            ORDER BY scanned_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    if not row:
        return None
    return {
        'scanned_at': row[0],
        'status': row[1],
        'error_message': row[2] or '',
        'bandwidth': json.loads(row[3] or '[]'),
        'host_count': row[4],
    }


def _hosts():
    _ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT ip, mac, hostname, os_name, interface_name, status, last_seen, note
            FROM {LAN_HOST_TABLE}
            WHERE status = 'alive'
            ORDER BY INET_ATON(ip), ip
        """)
        rows = _dictfetchall(cursor)
    for row in rows:
        if row.get('last_seen'):
            row['last_seen'] = timezone.localtime(_as_aware(row['last_seen']), TZ).strftime('%Y-%m-%d %H:%M:%S')
        row['os_name'] = row.get('os_name') or '未知'
    return rows


def _scan(force=False):
    snapshot = _latest_snapshot()
    if not force and snapshot and timezone.now() - _as_aware(snapshot['scanned_at']) < SCAN_MAX_AGE:
        return snapshot, _hosts()
    try:
        interfaces, hosts = _fetch_device_snapshot()
        _save_scan(interfaces, hosts)
    except (OSError, URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        _save_scan(snapshot['bandwidth'] if snapshot else [], [], 'error', str(exc))
    return _latest_snapshot(), _hosts()


def _payload(snapshot, hosts):
    scanned_at = ''
    if snapshot and snapshot.get('scanned_at'):
        scanned_at = timezone.localtime(_as_aware(snapshot['scanned_at']), TZ).strftime('%Y-%m-%d %H:%M:%S')
    return {
        'ok': bool(snapshot and snapshot.get('status') == 'ok'),
        'scanned_at': scanned_at,
        'status': snapshot.get('status') if snapshot else 'empty',
        'error_message': snapshot.get('error_message') if snapshot else '',
        'bandwidth': snapshot.get('bandwidth') if snapshot else [],
        'hosts': hosts,
        'host_count': len(hosts),
    }


def _is_wlan_ap(host):
    text = f"{host.get('hostname') or ''} {host.get('note') or ''}".lower()
    if any(keyword in text for keyword in WLAN_AP_KEYWORDS):
        return True
    return any(pattern.search(text) for pattern in WLAN_AP_NAME_PATTERNS)


def _subnet_key(ip):
    parts = (ip or '').split('.')
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return '.'.join(parts[:3])
    return ''


def _health_level(client_count, bps):
    if client_count >= 35 or bps >= 25000000:
        return 'hot'
    if client_count >= 18 or bps >= 8000000:
        return 'busy'
    return 'good'


def _wlan_aps_payload(snapshot, hosts):
    base = _payload(snapshot, hosts)
    bandwidth = base['bandwidth']
    ap_hosts = [host for host in hosts if _is_wlan_ap(host)]
    hosts_by_subnet = {}
    for host in hosts:
        hosts_by_subnet.setdefault(_subnet_key(host.get('ip')), []).append(host)

    ap_count_by_interface = {}
    for ap in ap_hosts:
        key = ap.get('interface_name') or ''
        ap_count_by_interface[key] = ap_count_by_interface.get(key, 0) + 1

    bandwidth_by_name = {item.get('name'): item for item in bandwidth}
    bandwidth_by_device = {item.get('device'): item for item in bandwidth}
    aps = []
    for ap in ap_hosts:
        subnet_hosts = hosts_by_subnet.get(_subnet_key(ap.get('ip')), [])
        client_count = max(0, len([host for host in subnet_hosts if host not in ap_hosts]))
        iface_name = ap.get('interface_name') or ''
        iface = bandwidth_by_name.get(iface_name) or bandwidth_by_device.get(iface_name) or {}
        share = max(ap_count_by_interface.get(iface_name, 1), 1)
        tx_bps = _safe_float(iface.get('tx_bps')) / share
        rx_bps = _safe_float(iface.get('rx_bps')) / share
        total_bps = tx_bps + rx_bps
        aps.append({
            'ip': ap.get('ip', ''),
            'mac': ap.get('mac', ''),
            'name': ap.get('hostname') or ap.get('ip', ''),
            'interface_name': iface_name,
            'client_count': client_count,
            'tx_bps': tx_bps,
            'rx_bps': rx_bps,
            'total_bps': total_bps,
            'tx_label': _format_bps(tx_bps),
            'rx_label': _format_bps(rx_bps),
            'total_label': _format_bps(total_bps),
            'level': _health_level(client_count, total_bps),
            'last_seen': ap.get('last_seen', ''),
            'note': ap.get('note', ''),
        })
    aps.sort(key=lambda item: (-item['client_count'], -item['total_bps'], item['name']))
    base.update({
        'aps': aps,
        'ap_count': len(aps),
        'client_count': sum(item['client_count'] for item in aps),
    })
    return base


def lan_hosts_page(request):
    snapshot = _latest_snapshot()
    hosts = _hosts() if snapshot else []
    return render(request, 'network/lan_hosts.html', {
        'snapshot_json': json.dumps(_payload(snapshot, hosts), ensure_ascii=False),
    })


def wlan_aps_page(request):
    snapshot = _latest_snapshot()
    hosts = _hosts() if snapshot else []
    return render(request, 'network/wlan_aps.html', {
        'snapshot_json': json.dumps(_wlan_aps_payload(snapshot, hosts), ensure_ascii=False),
    })


@require_POST
def lan_hosts_scan(request):
    force = request.POST.get('force') == '1'
    snapshot, hosts = _scan(force=force)
    return JsonResponse(_payload(snapshot, hosts))


@require_POST
def wlan_aps_scan(request):
    force = request.POST.get('force') == '1'
    snapshot, hosts = _scan(force=force)
    return JsonResponse(_wlan_aps_payload(snapshot, hosts))


@require_POST
def lan_hosts_note(request):
    _ensure_tables()
    ip = (request.POST.get('ip') or '').strip()
    mac = (request.POST.get('mac') or '').strip().lower()
    note = (request.POST.get('note') or '').strip()
    if not ip:
        return JsonResponse({'ok': False, 'error': 'missing ip'}, status=400)
    with connection.cursor() as cursor:
        cursor.execute(f"""
            UPDATE {LAN_HOST_TABLE}
            SET note = %s, updated_at = %s
            WHERE ip = %s AND mac = %s
        """, [note, timezone.now(), ip, mac])
    return JsonResponse({'ok': True, 'ip': ip, 'mac': mac, 'note': note})


def _checksum(source):
    total = 0
    length = len(source)
    index = 0
    while length > 1:
        total += (source[index] << 8) + source[index + 1]
        total &= 0xffffffff
        index += 2
        length -= 2
    if length:
        total += source[index] << 8
        total &= 0xffffffff
    total = (total >> 16) + (total & 0xffff)
    total += total >> 16
    return (~total) & 0xffff


def _icmp_ping(ip, count=3, timeout=2):
    icmp_proto = socket.getprotobyname('icmp')
    packet_id = os.getpid() & 0xffff
    output = []
    received = 0
    total_ms = 0.0

    with socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto) as sock:
        sock.settimeout(timeout)
        for sequence in range(1, count + 1):
            payload = struct.pack('d', time.time()) + b'NGHCC-LAN-HOSTS'
            header = struct.pack('!BBHHH', 8, 0, 0, packet_id, sequence)
            checksum = _checksum(header + payload)
            header = struct.pack('!BBHHH', 8, 0, checksum, packet_id, sequence)
            packet = header + payload
            started = time.time()
            sock.sendto(packet, (ip, 1))

            while True:
                remaining = timeout - (time.time() - started)
                if remaining <= 0:
                    output.append(f'Request timeout for icmp_seq {sequence}')
                    break
                readable, _, _ = select.select([sock], [], [], remaining)
                if not readable:
                    output.append(f'Request timeout for icmp_seq {sequence}')
                    break
                received_packet, address = sock.recvfrom(1024)
                ip_header_length = (received_packet[0] & 0x0f) * 4
                icmp_header = received_packet[ip_header_length:ip_header_length + 8]
                icmp_type, _, _, recv_id, recv_sequence = struct.unpack('!BBHHH', icmp_header)
                if address[0] == ip and icmp_type == 0 and recv_id == packet_id and recv_sequence == sequence:
                    elapsed_ms = (time.time() - started) * 1000
                    received += 1
                    total_ms += elapsed_ms
                    output.append(f'64 bytes from {ip}: icmp_seq={sequence} time={elapsed_ms:.1f} ms')
                    break

    loss = ((count - received) / count) * 100
    output.append(f'--- {ip} ping statistics ---')
    output.append(f'{count} packets transmitted, {received} received, {loss:.0f}% packet loss')
    if received:
        output.append(f'avg time {total_ms / received:.1f} ms')
    return received > 0, '\n'.join(output)


@require_POST
def lan_hosts_ping(request):
    ip = (request.POST.get('ip') or '').strip()
    if not re.match(r'^[0-9a-fA-F:.]+$', ip):
        return JsonResponse({'ok': False, 'error': 'invalid ip'}, status=400)

    if ':' not in ip:
        try:
            ok, output = _icmp_ping(ip)
            return JsonResponse({'ok': ok, 'ip': ip, 'returncode': 0 if ok else 1, 'output': output})
        except PermissionError:
            pass
        except OSError as exc:
            if getattr(exc, 'errno', None) != 1:
                return JsonResponse({'ok': False, 'ip': ip, 'output': str(exc)}, status=500)

    if platform.system().lower().startswith('win'):
        command = ['ping', '-n', '3', '-w', '2000', ip]
    else:
        command = ['ping', '-c', '3', '-W', '2', ip]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace',
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return JsonResponse({'ok': False, 'ip': ip, 'output': str(exc)}, status=500)

    output = (completed.stdout or '') + (completed.stderr or '')
    return JsonResponse({
        'ok': completed.returncode == 0,
        'ip': ip,
        'returncode': completed.returncode,
        'output': output.strip(),
    })
