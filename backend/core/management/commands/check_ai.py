"""
AI 리포트용 OpenAI 키 진단.

  python manage.py check_ai          # .env 의 키를 Django 가 읽었는지 확인
  python manage.py check_ai --call   # 실제 OpenAI 호출 1회 테스트(키 유효성·에러 원인 표시)
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from core.ai_report import has_llm, llm_test, _model


def _mask(k):
    return (k[:8] + '...' + k[-4:]) if k and len(k) > 14 else ('***' if k else '(빈 값)')


class Command(BaseCommand):
    help = 'AI 리포트용 OpenAI 키 설정 확인 및 실호출 테스트'

    def add_arguments(self, parser):
        parser.add_argument('--call', action='store_true', help='실제 OpenAI 호출 테스트')

    def handle(self, *args, **opts):
        key = (settings.OPENAI_API_KEY or '').strip()
        self.stdout.write('--- .env 로딩 상태 ---')
        self.stdout.write(f'  OPENAI_API_KEY: {_mask(key)} (길이 {len(key)})')
        self.stdout.write(f'  OPENAI_MODEL  : {_model()}')

        if not has_llm():
            self.stdout.write(self.style.ERROR(
                '\n❌ OPENAI_API_KEY 가 비어 있습니다. backend/.env 를 확인하고 서버를 재시작하세요.'))
            return

        self.stdout.write(self.style.SUCCESS('\n✅ 키 감지됨 (provider=openai)'))
        self.stdout.write('   호출 경로: https://api.openai.com/v1/chat/completions')

        if not opts['call']:
            self.stdout.write('\n실제 호출까지 테스트하려면:  python manage.py check_ai --call')
            return

        self.stdout.write('\n--- 실호출 테스트 ---')
        ok, label, detail = llm_test()
        if ok:
            self.stdout.write(self.style.SUCCESS(f'✅ 호출 성공: {detail[:60]}'))
            self.stdout.write('   → 앱의 AI 리포트도 정상 동작합니다. (매칭 상세에서 "↻ 리포트 다시 생성")')
            return

        self.stdout.write(self.style.ERROR(f'❌ 호출 실패: {label}'))
        if detail:
            self.stdout.write(f'   응답: {detail}')
        d = (detail or '') + ' ' + label
        if 'CERTIFICATE_VERIFY_FAILED' in d or 'SSL' in d or 'URLError' in d:
            self.stdout.write(self.style.WARNING(
                '   → SSL 인증서 문제(주로 macOS). 아래 중 하나로 해결:\n'
                '     1) pip install -r requirements.txt   (certifi 설치)\n'
                '     2) macOS python.org 설치본이면: '
                '"/Applications/Python 3.x/Install Certificates.command" 실행\n'
                '     설치 후 서버 재시작하고 다시 시도하세요.'))
        elif '401' in d or 'invalid_api_key' in d or 'Incorrect API key' in d:
            self.stdout.write(self.style.WARNING(
                '   → 키가 틀렸거나 폐기됨. platform.openai.com 에서 새 키 발급 후 .env 교체.'))
        elif '429' in d or 'insufficient_quota' in d or 'quota' in d:
            self.stdout.write(self.style.WARNING(
                '   → 결제/크레딧 부족. platform.openai.com 결제(billing)에서 결제수단 등록·크레딧 '
                '충전이 필요합니다. (신규 키는 대부분 여기서 막힘)'))
        elif '404' in d or 'model' in d.lower():
            self.stdout.write(self.style.WARNING(
                f'   → 모델 접근 불가. .env 의 OPENAI_MODEL={_model()} 을 gpt-4o-mini 등 허용 모델로 변경.'))
        else:
            self.stdout.write(self.style.WARNING(
                '   → 네트워크/방화벽 또는 키 형식 문제일 수 있습니다.'))
