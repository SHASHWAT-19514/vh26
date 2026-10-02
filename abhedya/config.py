from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv('ABHEDYA_DATA_DIR', ROOT / 'data')).resolve()
CONFIG_DIR = ROOT / 'config'
ENV = os.getenv('ABHEDYA_ENV', 'development').lower()
API_KEY = os.getenv('ABHEDYA_API_KEY', '')
MAX_UPLOAD_BYTES = int(os.getenv('ABHEDYA_MAX_UPLOAD_BYTES', str(2 * 1024**3)))
RATE_LIMIT = int(os.getenv('ABHEDYA_RATE_LIMIT', '120'))
RATE_WINDOW_SECONDS = int(os.getenv('ABHEDYA_RATE_WINDOW_SECONDS', '60'))
TRUSTED_HOSTS = [x.strip() for x in os.getenv('ABHEDYA_TRUSTED_HOSTS', '').split(',') if x.strip()]
ALLOWED_ORIGINS = [x.strip() for x in os.getenv('ABHEDYA_ALLOWED_ORIGINS', '').split(',') if x.strip()]


def load_yaml(name: str) -> dict:
    with (CONFIG_DIR / name).open(encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def detection_config() -> dict:
    return load_yaml('detection.yaml')


def config_hash() -> str:
    payload = json.dumps({'detection': detection_config(), 'env': ENV}, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_runtime() -> None:
    if ENV == 'production' and len(API_KEY) < 32:
        raise RuntimeError('ABHEDYA_API_KEY must be at least 32 characters in production')
    if MAX_UPLOAD_BYTES < 1024 * 1024:
        raise RuntimeError('ABHEDYA_MAX_UPLOAD_BYTES must be at least 1 MiB')


def ensure_dirs() -> None:
    for p in [DATA_DIR, DATA_DIR / 'inbox', DATA_DIR / 'datasets', DATA_DIR / 'tmp', DATA_DIR / 'backups', ROOT / 'logs', ROOT / 'benchmarks/results']:
        p.mkdir(parents=True, exist_ok=True)
