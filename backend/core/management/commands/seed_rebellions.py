"""
데모 시드: 삼성벤처투자(VC) + 리벨리온(스타트업) + 매칭 + AI 리포트.

실제 공개자료·2025 감사보고서 기반. 삼성벤처투자는 리벨리온 시리즈C에 실제 참여.
금액 단위: 모델은 '만원', 원데이터는 '억원' → ×10000 변환.

사용: python manage.py seed_rebellions
"""
from django.core.management.base import BaseCommand
from core.models import VCProfile, StartupProfile, Match, AIReport, Like
from accounts.models import User

OK = 10000  # 억원 → 만원


class Command(BaseCommand):
    help = '삼성벤처투자 × 리벨리온 데모 데이터 시드'

    def add_arguments(self, parser):
        parser.add_argument('--matched', action='store_true',
                            help='매칭+AI리포트까지 미리 생성(기본: 매칭 전 상태)')

    def handle(self, *args, **opt):
        vc = self._seed_vc()
        startup = self._seed_startup()
        self._link_accounts(vc, startup)
        if opt['matched']:
            # 완성 상태: 매칭 + AI리포트까지 미리 생성
            match = self._seed_match(vc, startup)
            self._seed_report(vc, startup, match)
        else:
            # 매칭 전 상태: 기존 좋아요/매칭/리포트 정리 → 시연 때 직접 매칭
            self._clear_match(vc, startup)
            self.stdout.write('  매칭 전 상태 — 추천 리스트에서 좋아요로 매칭하세요')
        self.stdout.write(self.style.SUCCESS('✓ 데모 시드 완료: 삼성벤처투자 × 리벨리온'))

    # ---------------------------------------------------------------
    def _seed_vc(self):
        vc, created = VCProfile.objects.get_or_create(firm_name='삼성벤처투자')
        vc.website = 'https://www.samsungventure.co.kr'
        vc.bio = (
            '1999년 설립된 삼성 그룹의 기업형 벤처캐피탈(CVC). '
            'AUM 약 4.2조원, 누적 1,188개사 투자·75개 펀드 결성. '
            '서울·실리콘밸리·보스턴·런던·텔아비브 등 글로벌 네트워크 보유. '
            'AI·로봇·반도체·바이오·에너지 등 딥테크 중심 투자.'
        )
        vc.vc_summary = (
            '삼성 계열사와의 전략적 시너지를 중시하는 대형 CVC. '
            '반도체·AI 인프라 등 기술 난이도가 높은 후기 단계 투자에 강점. '
            '시리즈 A~프리IPO 전반을 커버.'
        )
        vc.eval_emphasis = ['team', 'market', 'traction']
        vc.save()
        vc.set_preference(
            preferred_industries=['AI 반도체', 'AI', '반도체', '로봇', '바이오', '에너지'],
            preferred_stages=['Series A', 'Series B', 'Series C', 'Growth'],
            preferred_regions=['서울', '대한민국'],
            preferred_education=['박사', '석사'],
            min_investment=100 * OK,      # 100억
            max_investment=5000 * OK,     # 5,000억
        )
        self.stdout.write(f'  VC {"생성" if created else "갱신"}: 삼성벤처투자')
        return vc

    # ---------------------------------------------------------------
    def _seed_startup(self):
        s, created = StartupProfile.objects.get_or_create(name='리벨리온')
        s.industry = 'AI 반도체'
        s.stage = 'Series C'
        s.region = '서울'
        s.funding_needed = 3000 * OK         # 3,000억 (차기 희망)
        s.team_size = 220
        s.revenue = int(320.217 * OK)        # 2025 매출 320.217억
        s.founded_year = 2020
        s.founder_experience_years = 15
        s.prior_exits = 0
        s.mau = 0                            # B2B 반도체
        s.retention_rate = 0
        s.mom_growth = 0                     # 연간 실적은 financials에서 YoY 자동계산
        s.market_size = 300000               # AI 추론 반도체 시장(억원, 데모 추정)
        s.market_growth = 30                 # CAGR(%)
        s.cac = 0
        s.ltv = 0
        s.burn_rate = int(1204.6459 / 12 * OK)   # 2025 영업손실 / 12 ≈ 월 100억
        s.runway_months = 36                 # 프리IPO 4억달러 조달 후 여유
        s.founder_education = '박사'
        s.differentiation = (
            'ATOM·Rebel100 자체 설계 NPU. UCIe-Advanced 칩렛 구조와 HBM3E 기반 '
            '대규모 LLM·MoE 추론 가속. PyTorch·vLLM·Triton 등 주류 생태계 지원.'
        )
        s.description = (
            'AI 추론 반도체(NPU) 설계 팬리스. 2024년 사피온코리아와 합병, '
            'KT Cloud·SK텔레콤·Red Hat·Arm 등과 협력. 대한민국·미국·일본·'
            '사우디에 제품 공급. 2026년 3월 4억달러 프리IPO 조달(기업가치 약 23.4억달러).'
        )
        s.summary = 'Arm·삼성이 투자한 AI 추론 반도체 유니콘. 2025 매출 320억(+209% YoY).'
        s.signals = {
            'total_funding_usd_million': 850,
            'latest_valuation_usd_million': 2340,
            'partners': ['KT Cloud', 'SK텔레콤', 'Red Hat', 'Arm'],
            'deployment_countries': ['대한민국', '미국', '일본', '사우디아라비아'],
            'merger': '사피온코리아 합병(2024-12)',
            'gross_margin_percent_2025': 50.0,
        }
        # 감사보고서 재무 (억원 → 만원)
        s.financials = {
            'corp_code': None, 'source': '2025 연결 감사보고서',
            'years': {
                '2024': {
                    'revenue': int(103.4917 * OK), 'operating_profit': int(-871.7 * OK),
                    'net_income': int(-2343.5 * OK),
                },
                '2025': {
                    'revenue': int(320.217 * OK), 'operating_profit': int(-1204.6459 * OK),
                    'net_income': int(-2069 * OK),
                },
            },
        }
        s.save()
        self.stdout.write(f'  Startup {"생성" if created else "갱신"}: 리벨리온 (2025 매출 {s.revenue:,}만원)')
        return s

    # ---------------------------------------------------------------
    def _clear_match(self, vc, startup):
        """좋아요/매칭/AI리포트 정리 — 깨끗한 시연 시작 상태로 되돌린다."""
        AIReport.objects.filter(match__vc=vc, match__startup=startup).delete()
        n_m = Match.objects.filter(vc=vc, startup=startup).delete()[0]
        n_l = Like.objects.filter(vc=vc, startup=startup).delete()[0]
        if n_m or n_l:
            self.stdout.write(f'  정리: 매칭 {n_m}건, 좋아요 {n_l}건 삭제')

    # ---------------------------------------------------------------
    def _seed_match(self, vc, startup):
        match, created = Match.objects.get_or_create(
            vc=vc, startup=startup,
            defaults={'status': 'matched', 'requested_by': 'vc'},
        )
        self.stdout.write(f'  Match {"생성" if created else "기존"}: #{match.id}')
        return match

    # ---------------------------------------------------------------
    def _link_accounts(self, vc, startup):
        """데모 로그인 계정 생성 + 프로필 연결 (이메일 인증 생략)."""
        accounts = [
            ('samsung', 'vc', vc, '삼성벤처투자'),
            ('rebellions', 'startup', startup, '리벨리온'),
        ]
        for username, role, profile, disp in accounts:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': role, 'name': disp,
                          'email': f'{username}@vmatch.demo', 'email_verified': True})
            user.role = role
            user.email_verified = True
            user.set_password('vmatch1234!')
            user.save()
            profile.user = user
            profile.save(update_fields=['user'])
            self.stdout.write(f'  계정 {"생성" if created else "갱신"}: {username} / vmatch1234! ({disp})')

    # ---------------------------------------------------------------
    def _seed_report(self, vc, startup, match):
        from core.ai_report import generate_ai_report
        score, summary, source, rj = generate_ai_report(vc, startup)
        AIReport.objects.update_or_create(
            match=match,
            defaults={'fit_score': score, 'summary': summary,
                      'source': source, 'report_json': rj},
        )
        nfin = len([m for sec in rj.get('sections', []) for m in sec.get('metrics', [])])
        self.stdout.write(f'  AIReport: fit={score} source={source} (지표 {nfin}개)')
