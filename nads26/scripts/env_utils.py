import os
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]


def load_app_env(path=APP_DIR / '.env'):
    """Load simple KEY=VALUE entries without overriding process variables."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f'Required environment variable is not set: {name}')
    return value
