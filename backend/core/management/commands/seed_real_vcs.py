"""
실제 VC 데이터(core/data/vc_data.json) 적재.

JSON 은 loaddata 형식처럼 보이지만, 정규화 스키마(VCPreference 1:1, website 등)와
필드가 달라 loaddata 로는 적재할 수 없다. 이 명령이 필드를 매핑해서 넣는다.
  - link                → VCProfile.website
  - preferred_*, min/max_investment → VCPreference(1:1)
  - 'All' 산업 / '전국' 지역은 매칭 엔진에서 와일드카드로 처리됨.

사용:
  python manage.py seed_real_vcs            # upsert(firm_name 기준)
  python manage.py seed_real_vcs --reset    # 계정 미연결 VC 전부 삭제 후 재적재
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from core.models import VCProfile

DATA = Path(__file__).resolve().parent.parent.parent / 'data' / 'vc_data.json'


class Command(BaseCommand):
    help = '실제 VC 데이터를 적재한다(core/data/vc_data.json).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='계정 미연결(user=None) VC를 모두 삭제 후 재적재')

    def handle(self, *args, **opts):
        if not DATA.exists():
            self.stderr.write(f'데이터 파일이 없습니다: {DATA}')
            return

        if opts['reset']:
            n, _ = VCProfile.objects.filter(user__isnull=True).delete()
            self.stdout.write(f'기존 미연결 VC 삭제: {n}건')

        rows = json.loads(DATA.read_text(encoding='utf-8'))
        from core.recommend import normalize_stage
        created = 0
        for row in rows:
            f = row.get('fields', row)
            # bio 보강: vc_summary + 투자 thesis(target/focus_sectors) 결합
            bio = f.get('bio', '') or f.get('vc_summary', '') or ''
            th = f.get('investment_thesis') or {}
            if isinstance(th, dict):
                extra = []
                if th.get('target'):
                    extra.append(f"투자 대상: {th['target']}")
                if th.get('focus_sectors'):
                    extra.append('주력 분야: ' + ', '.join(th['focus_sectors']))
                if extra and bio:
                    bio = bio + '\n' + ' / '.join(extra)
                elif extra:
                    bio = ' / '.join(extra)
            obj, was_created = VCProfile.objects.get_or_create(
                firm_name=f['firm_name'],
                defaults=dict(
                    user=None,
                    website=f.get('link', '') or f.get('website', ''),
                    bio=bio,
                    vc_summary=f.get('vc_summary', ''),
                    eval_emphasis=f.get('eval_emphasis', []) or [],
                ),
            )
            # 기존 항목도 최신 값으로 갱신
            obj.website = f.get('link', '') or f.get('website', '') or obj.website
            obj.bio = bio or obj.bio
            obj.vc_summary = f.get('vc_summary', obj.vc_summary)
            obj.eval_emphasis = f.get('eval_emphasis', obj.eval_emphasis) or []
            obj.save()

            stages = [normalize_stage(s) for s in (f.get('preferred_stages', []) or [])]
            obj.set_preference(
                preferred_industries=f.get('preferred_industries', []) or [],
                preferred_stages=stages,
                preferred_regions=f.get('preferred_regions', []) or [],
                min_investment=f.get('min_investment', 0) or 0,
                max_investment=f.get('max_investment', 0) or 0,
            )
            created += int(was_created)

        total = VCProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'실제 VC 적재 완료: {created}건 신규 (전체 VC {total}건)'))
