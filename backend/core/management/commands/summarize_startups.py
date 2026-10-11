"""
스타트업 카탈로그의 추천 카드용 '간결 요약(summary)'을 GPT로 생성/갱신한다.

  python manage.py summarize_startups          # summary 비어있는 곳만
  python manage.py summarize_startups --all     # 전체 재생성

OPENAI_API_KEY 가 없으면 시드 시 만든 규칙기반 요약을 그대로 둔다.
"""
from django.core.management.base import BaseCommand

from core.models import StartupProfile
from core.ai_report import has_llm, _llm_generate

INSTR = (
    '너는 VC 투자심사역을 돕는 어시스턴트다. 아래 스타트업 정보를 투자자 관점에서 '
    '2~3문장으로 간결하게 요약하라. 무엇을 하는 회사인지 + 핵심 강점(매출·고객·특허·해외 등)을 '
    '담되, 과장 없이 사실만. 불릿/머리말 없이 자연스러운 한국어 문장으로만 출력.'
)


class Command(BaseCommand):
    help = '스타트업 추천 카드용 AI 간결 요약 생성'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='전체 재생성')

    def handle(self, *args, **opts):
        if not has_llm():
            self.stdout.write(self.style.WARNING(
                'OPENAI_API_KEY 미설정 — 규칙기반 요약을 유지합니다(변경 없음).'))
            return

        qs = StartupProfile.objects.all()
        if not opts['all']:
            qs = qs.filter(summary='')
        n = 0
        for s in qs:
            info = (f'회사명: {s.name}\n산업/단계/지역: {s.industry}/{s.stage}/{s.region}\n'
                    f'차별점: {s.differentiation}\n상세: {s.description[:1500]}')
            text, src = _llm_generate(INSTR, info, json_mode=False, timeout=30)
            if text and src != 'fallback':
                s.summary = text.strip()
                s.save(update_fields=['summary'])
                n += 1
                self.stdout.write(f'  ✓ {s.name}')
        self.stdout.write(self.style.SUCCESS(f'요약 생성 완료: {n}건'))
