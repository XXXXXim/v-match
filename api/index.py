"""Vercel 서버리스 진입점 — Django(backend/)를 WSGI 앱으로 띄운다.

배포 파일 시스템은 읽기 전용이라, 시드된 데모 DB를 /tmp 로 복사하고, 업로드 폴더도 /tmp 에 만든다.
/tmp 는 인스턴스마다 따로 있고 콜드 스타트 때 초기화되므로, 데모 데이터는 주기적으로 처음 상태로 돌아간다.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TMP = Path("/tmp/vmatch")
DB_PATH = TMP / "db.sqlite3"
PROTECTED = TMP / "protected_media"

TMP.mkdir(parents=True, exist_ok=True)
if not DB_PATH.exists():
    shutil.copyfile(BACKEND / "demo" / "demo.sqlite3", DB_PATH)
PROTECTED.mkdir(exist_ok=True)  # IR 업로드용 비공개 폴더(배포본에는 업로드 파일이 없음)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DB_PATH", str(DB_PATH))
os.environ.setdefault("DJANGO_MEDIA_ROOT", str(TMP / "media"))
os.environ.setdefault("DJANGO_PROTECTED_MEDIA_ROOT", str(PROTECTED))

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
