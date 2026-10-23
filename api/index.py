"""Vercel 서버리스 진입점 — Django(backend/)를 WSGI 앱으로 띄운다.

DB 는 두 가지 방식을 지원한다.
- DATABASE_URL 이 있으면(권장): 모든 인스턴스가 같은 Postgres 를 쓴다. 서버가 시작될 때
  마이그레이션하고, 비어 있으면 데모 데이터를 넣는다. 매일 한 번 Cron 이 처음 상태로 되돌린다.
- 없으면: 시드된 SQLite 를 /tmp 로 복사해 쓴다. 인스턴스마다 DB 가 따로라서
  방문자가 새로 만든 데이터는 다른 인스턴스에서 안 보일 수 있다.

업로드 파일(IR 등)은 어느 경우든 /tmp 에 저장되므로 인스턴스가 바뀌면 사라질 수 있다.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TMP = Path("/tmp/vmatch")
PROTECTED = TMP / "protected_media"
TMP.mkdir(parents=True, exist_ok=True)
PROTECTED.mkdir(exist_ok=True)

USE_POSTGRES = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))
if not USE_POSTGRES:
    db_path = TMP / "db.sqlite3"
    if not db_path.exists():
        shutil.copyfile(BACKEND / "demo" / "demo.sqlite3", db_path)
    os.environ.setdefault("DJANGO_DB_PATH", str(db_path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_MEDIA_ROOT", str(TMP / "media"))
os.environ.setdefault("DJANGO_PROTECTED_MEDIA_ROOT", str(PROTECTED))

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()

if USE_POSTGRES:
    from django.core.management import call_command  # noqa: E402
    from django.db import connections  # noqa: E402

    call_command("demo_db", "ensure", verbosity=0)
    connections.close_all()  # 준비용 연결은 닫고, 요청은 새 연결로 처리
