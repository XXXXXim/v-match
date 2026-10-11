"""
데모용 시드 스타트업 생성.

  python manage.py seed_startups          # 없으면 생성(이미 있으면 건너뜀)
  python manage.py seed_startups --reset  # 시드 스타트업 전부 지우고 재생성

주의: 전부 가상의 회사다. 실제 기업명/실제 재무가 아니다.
산업/단계/지역 값은 frontend/src/constants/options.js 와 정확히 일치해야 한다.
"""
from django.core.management.base import BaseCommand

from core.models import StartupProfile

_STAGE_IDX = {'Seed': 0, 'Pre-A': 1, 'Series A': 2, 'Series B': 3, 'Series C+': 4}

def _ext(stage, funding, team, rev, year):
    """단계/규모 기반으로 확장 평가 지표를 그럴듯하게 파생(데모용)."""
    i = _STAGE_IDX.get(stage, 0)
    _edu = ['대졸', '대졸', '석사', '박사', '석사'][i]
    return dict(
        founder_education=_edu,
        founder_experience_years=4 + i * 2,
        prior_exits=1 if i >= 3 else 0,
        mau=int(rev * 1200 + i * 8000 + team * 300),
        retention_rate=min(90, 45 + i * 8),
        mom_growth=max(5, 35 - i * 6),
        market_size=8000 + i * 9000 + funding * 50,
        market_growth=max(8, 30 - i * 3),
        cac=8 + i * 2,
        ltv=int((8 + i * 2) * (2.5 + i * 0.4)),
        burn_rate=int(funding * 60),
        runway_months=max(8, 22 - i * 2),
    )

# (name, industry, stage, region, funding_needed(억), team, revenue(억), founded, desc)
SEED = [
    ('클라우드데스크', 'SaaS', 'Series A', '서울', 30, 24, 18, 2021, '중소기업용 올인원 협업·문서 SaaS. 구독 매출 비중 90%.'),
    ('페이브릿지', 'Fintech', 'Series B', '서울', 80, 60, 95, 2019, '소상공인 임베디드 결제·정산 인프라.'),
    ('메디라이트', 'Healthcare', 'Pre-A', '경기', 12, 11, 3, 2022, '만성질환 원격 모니터링 및 처방 연계 플랫폼.'),
    ('뉴럴베이스', 'AI/ML', 'Seed', '서울', 8, 7, 0, 2023, '제조 현장 비전 검사용 경량 AI 모델 솔루션.'),
    ('마켓루프', 'E-commerce', 'Series A', '경기', 25, 30, 40, 2020, '리커머스(중고 명품) 검수·중개 마켓플레이스.'),
    ('러닝셀', 'EdTech', 'Seed', '대전', 6, 6, 1, 2023, '초중등 AI 맞춤형 수학 학습 앱.'),
    ('셀제닉스', 'Bio', 'Series A', '대전', 45, 18, 2, 2020, '면역세포치료제 후보물질 개발 바이오텍.'),
    ('픽셀하트', 'Gaming', 'Pre-A', '부산', 15, 14, 5, 2021, '서브컬처 수집형 모바일 RPG 개발 스튜디오.'),
    ('로드패스', 'Mobility', 'Series B', '서울', 90, 70, 60, 2018, '중형 화물 운송 디지털 포워딩 플랫폼.'),
    ('그린루트', 'Other', 'Seed', '기타', 5, 5, 0, 2024, '도심형 폐기물 수거 경로 최적화 서비스.'),

    ('데이터윙', 'SaaS', 'Pre-A', '서울', 14, 13, 6, 2022, 'BI 대시보드 자동화 노코드 분석 툴.'),
    ('렌딧코어', 'Fintech', 'Series A', '서울', 35, 28, 22, 2020, '대안신용평가 기반 중금리 대출 중개.'),
    ('바이탈로그', 'Healthcare', 'Series A', '경기', 28, 22, 9, 2021, '웨어러블 연동 임상 데이터 수집 플랫폼.'),
    ('센티언트랩', 'AI/ML', 'Series B', '서울', 120, 85, 70, 2018, '기업용 검색·RAG 엔진 및 LLMOps.'),
    ('카트젠', 'E-commerce', 'Seed', '부산', 7, 8, 2, 2023, 'D2C 브랜드용 풀필먼트·CS 자동화.'),
    ('코드플레이', 'EdTech', 'Series A', '서울', 22, 20, 14, 2020, '실무형 코딩 부트캠프 + 취업 연계.'),
    ('지노바이오', 'Bio', 'Series C+', '대전', 200, 95, 30, 2015, '유전체 분석 기반 동반진단 키트.'),
    ('네온스튜디오', 'Gaming', 'Series A', '경기', 40, 45, 25, 2019, 'PC/콘솔 인디 액션 게임 퍼블리싱.'),
    ('휠셰어', 'Mobility', 'Seed', '서울', 9, 9, 1, 2023, '전동 모빌리티 B2B 구독 관리.'),
    ('에코패키지', 'Other', 'Pre-A', '경기', 11, 10, 4, 2022, '생분해 포장재 제조 및 공급.'),

    ('스택플로우', 'SaaS', 'Series B', '서울', 75, 55, 50, 2018, '개발팀 인시던트 대응·온콜 관리 SaaS.'),
    ('퀵세틀', 'Fintech', 'Seed', '경기', 6, 6, 0, 2024, '프리랜서 즉시 정산·세금 자동화.'),
    ('케어링크', 'Healthcare', 'Series B', '서울', 85, 64, 48, 2017, '요양·돌봄 인력 매칭 및 운영 플랫폼.'),
    ('비전포지', 'AI/ML', 'Pre-A', '대전', 13, 12, 2, 2022, '위성·드론 영상 분석 AI.'),
    ('샵스택', 'E-commerce', 'Series B', '서울', 95, 80, 110, 2017, '크로스보더 이커머스 통합 운영 솔루션.'),
    ('튜터민트', 'EdTech', 'Pre-A', '부산', 10, 9, 3, 2022, '화상 1:1 외국어 튜터링 마켓.'),
    ('바이오시드', 'Bio', 'Seed', '대전', 9, 8, 0, 2023, '미생물 기반 대체 단백질 소재.'),
    ('플레이루프', 'Gaming', 'Seed', '서울', 5, 6, 0, 2024, '하이퍼캐주얼 게임 라이브옵스 툴.'),
    ('파킹온', 'Mobility', 'Series A', '경기', 30, 26, 20, 2020, '공유 주차장 실시간 예약 플랫폼.'),
    ('어반팜', 'Other', 'Series A', '기타', 26, 24, 12, 2020, '도심 수직농장 운영 및 유통.'),

    ('플로우데스크', 'SaaS', 'Seed', '서울', 6, 5, 0, 2024, '영업팀용 AI 미팅 노트·CRM 연동.'),
    ('크레딧링', 'Fintech', 'Series C+', '서울', 180, 130, 160, 2015, '기업 지출관리·법인카드 핀테크.'),
    ('헬스노트', 'Healthcare', 'Seed', '부산', 7, 7, 1, 2023, '개인 건강기록(PHR) 통합 앱.'),
    ('딥센스', 'AI/ML', 'Series A', '서울', 38, 30, 16, 2020, '음성 감정·콜센터 품질 분석 AI.'),
    ('리세일허브', 'E-commerce', 'Pre-A', '경기', 12, 11, 5, 2022, '패션 중고거래 정품 인증 플랫폼.'),
    ('스킬업랩', 'EdTech', 'Series B', '서울', 70, 58, 42, 2018, '직장인 구독형 실무 강의 플랫폼.'),
    ('애드바이오', 'Bio', 'Series B', '대전', 110, 70, 12, 2017, '항체 신약 개발 플랫폼.'),
    ('루나게임즈', 'Gaming', 'Series C+', '경기', 220, 160, 240, 2014, '글로벌 미드코어 모바일 게임 개발.'),
    ('트럭온', 'Mobility', 'Pre-A', '부산', 13, 12, 6, 2022, '근거리 라스트마일 배송 중개.'),
    ('서스테인', 'Other', 'Seed', '기타', 5, 5, 0, 2024, '기업 탄소배출 측정·리포팅 SaaS.'),
]


class Command(BaseCommand):
    help = '데모용 가상 스타트업 시드 생성'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='기존 시드(계정 미연결 스타트업) 삭제 후 재생성')

    def handle(self, *args, **opts):
        if opts['reset']:
            # 시드는 user=None 으로 생성되므로 그것만 안전하게 삭제
            deleted, _ = StartupProfile.objects.filter(user__isnull=True).delete()
            self.stdout.write(self.style.WARNING(f'시드 {deleted}건 삭제'))

        created = 0
        for (name, industry, stage, region, funding, team, rev, year, desc) in SEED:
            obj, was_created = StartupProfile.objects.get_or_create(
                name=name,
                defaults=dict(
                    user=None, industry=industry, stage=stage, region=region,
                    funding_needed=funding * 10000, team_size=team, revenue=rev * 10000,
                    founded_year=year, description=desc,
                    **_ext(stage, funding, team, rev, year),
                ),
            )
            created += int(was_created)

        total = StartupProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'시드 완료: {created}건 신규 생성 (전체 스타트업 {total}건)'
        ))
