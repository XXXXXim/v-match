"""
데모용 시드 VC(투자사) 생성. 스타트업 입장의 'VC 추천' 기능 시연에 필요.

  python manage.py seed_vcs          # 없으면 생성
  python manage.py seed_vcs --reset  # 계정 미연결 시드 VC 삭제 후 재생성

주의: 전부 가상의 투자사다. 실제 VC/실제 투자조건이 아니다.
선호 산업/단계/지역 값은 frontend/src/constants/options.js 와 일치해야 한다.
"""
from django.core.management.base import BaseCommand

from core.models import VCProfile

# (firm_name, industries, stages, regions, min억, max억, bio, website)
SEED = [
    ('넥스트시드파트너스', ['SaaS', 'Fintech', 'AI/ML'], ['Seed', 'Pre-A'],
     ['서울', '경기'], 3, 30, '초기 B2B SaaS·핀테크 전문 시드 투자.', 'https://nextseed.example.com'),
    ('한강벤처스', ['Fintech', 'E-commerce'], ['Seed', 'Series A'],
     ['서울'], 5, 50, '소비자·핀테크 분야 초기~성장 투자.', 'https://hangang.example.com'),
    ('블루오션캐피탈', ['Healthcare', 'Bio'], ['Series A', 'Series B'],
     ['서울', '대전'], 30, 200, '바이오·헬스케어 성장 단계 집중.', 'https://blueocean.example.com'),
    ('세종임팩트', ['EdTech', 'Other'], ['Seed', 'Pre-A'],
     ['대전', '기타'], 3, 20, '교육·소셜임팩트 초기 투자.', 'https://sejong-impact.example.com'),
    ('퍼시픽그로스', ['SaaS', 'AI/ML'], ['Series A', 'Series B'],
     ['서울', '경기'], 30, 150, '엔터프라이즈 SW·AI 스케일업 투자.', 'https://pacificgrowth.example.com'),
    ('남산엔젤클럽', ['SaaS', 'Fintech', 'AI/ML', 'E-commerce'], ['Seed'],
     ['서울'], 1, 15, '시드 단계 폭넓게 투자하는 엔젤 신디케이트.', 'https://namsanangels.example.com'),
    ('테크프론티어', ['AI/ML', 'Mobility'], ['Series A', 'Series B', 'Series C+'],
     ['서울', '경기'], 50, 300, '딥테크·모빌리티 대형 투자.', 'https://techfrontier.example.com'),
    ('부산이노베이션', ['Mobility', 'Gaming', 'Other'], ['Seed', 'Pre-A'],
     ['부산', '기타'], 5, 40, '동남권 거점 초기 투자.', 'https://busaninno.example.com'),
    ('그린하이파트너스', ['Bio', 'Healthcare', 'Other'], ['Seed', 'Series A'],
     ['대전', '서울'], 10, 80, '바이오·기후·소재 분야 투자.', 'https://greenhigh.example.com'),
    ('코리아핀테크인베스트', ['Fintech'], ['Pre-A', 'Series A', 'Series B'],
     ['서울'], 20, 120, '핀테크 단일 섹터 집중 투자.', 'https://kfintech.example.com'),
]


class Command(BaseCommand):
    help = '데모용 가상 VC(투자사) 시드 생성'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='계정 미연결 시드 VC 삭제 후 재생성')

    def handle(self, *args, **opts):
        if opts['reset']:
            deleted, _ = VCProfile.objects.filter(user__isnull=True).delete()
            self.stdout.write(self.style.WARNING(f'시드 VC {deleted}건 삭제'))

        created = 0
        for (firm, inds, stages, regions, lo, hi, bio, website) in SEED:
            obj, was_created = VCProfile.objects.get_or_create(
                firm_name=firm,
                defaults=dict(user=None, bio=bio, website=website),
            )
            if obj.website != website:
                obj.website = website
                obj.save(update_fields=['website'])
            # 선호조건은 1:1 VCPreference 로 저장
            obj.set_preference(
                preferred_industries=inds,
                preferred_stages=stages,
                preferred_regions=regions,
                min_investment=lo * 10000,
                max_investment=hi * 10000,
            )
            created += int(was_created)

        total = VCProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'VC 시드 완료: {created}건 신규 (전체 VC {total}건)'
        ))
