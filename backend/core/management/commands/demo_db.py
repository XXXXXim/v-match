"""
공개 데모 DB 준비·초기화.

  python manage.py demo_db ensure   # 마이그레이션 후, 비어 있으면 데모 데이터 적재 (서버 시작 때)
  python manage.py demo_db reset    # 모든 데이터를 지우고 데모 데이터로 되돌림 (매일 자동 초기화)

데모 데이터는 backend/demo/demo_fixture.json 이다. VC 20곳·스타트업 50곳, 데모 계정 2개와 토큰,
미리 성사된 매칭 1건이 들어 있다. 서버리스는 여러 인스턴스가 동시에 뜰 수 있으므로,
Postgres 에서는 advisory lock 으로 한 인스턴스만 준비 작업을 하게 한다.
"""
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

FIXTURE = Path(settings.BASE_DIR) / 'demo' / 'demo_fixture.json'
LOCK_ID = 7_310_042  # 이 앱 전용 임의의 잠금 번호


@contextmanager
def _single_runner():
    """Postgres 면 advisory lock 으로 직렬화한다. SQLite 는 인스턴스별 파일이라 잠글 필요 없음.

    migrate·flush 도중 Django 가 DB 연결을 닫고 새로 열 수 있어서, 잠금은 Django 연결이 아닌
    별도 연결에 걸어 두고 작업이 끝날 때까지 그 연결을 유지한다(연결이 닫히면 잠금도 풀림).
    """
    if connection.vendor != 'postgresql':
        yield
        return
    import psycopg

    db = connection.settings_dict
    lock_conn = psycopg.connect(
        dbname=db['NAME'], user=db['USER'], password=db['PASSWORD'],
        host=db['HOST'], port=db['PORT'] or None, autocommit=True,
        **db.get('OPTIONS', {}),
    )
    try:
        lock_conn.execute('SELECT pg_advisory_lock(%s)', [LOCK_ID])
        yield
    finally:
        lock_conn.close()  # 연결을 닫으면 세션 잠금이 함께 풀린다


class Command(BaseCommand):
    help = '공개 데모 DB를 준비(ensure)하거나 처음 상태로 초기화(reset)한다.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['ensure', 'reset'])

    def handle(self, *args, **opts):
        from accounts.models import User

        with _single_runner():
            call_command('migrate', interactive=False, verbosity=0)
            if opts['action'] == 'reset':
                call_command('flush', interactive=False, verbosity=0)
                call_command('loaddata', str(FIXTURE), verbosity=0)
                self.stdout.write('데모 데이터를 처음 상태로 되돌렸습니다.')
            elif not User.objects.exists():
                call_command('loaddata', str(FIXTURE), verbosity=0)
                self.stdout.write('빈 DB에 데모 데이터를 적재했습니다.')
            else:
                self.stdout.write('데모 데이터가 이미 있습니다.')
