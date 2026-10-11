"""
스타트업 실데이터 시드 (core/data/startup_data.json 적재).

  python manage.py seed_real_startups          # 없으면 생성
  python manage.py seed_real_startups --reset  # 기존(계정 미연결) 시드 삭제 후 재생성

startup_data.json 형식: Django fixture(model/pk/fields). 금액(funding_needed·revenue)은
원 단위로 넣으면 적재 시 만원 단위로 자동 변환된다. 중첩 필드(business_model·products·
forecast·achievements)에서 특허·후속투자·해외진출·고객 등 정량 신호를 추출해 signals 에 저장한다.
"""
from django.core.management.base import BaseCommand

from core.models import StartupProfile


def _fmt_eok(man):
    """만원 → '억' 표기(억 단위 반올림)."""
    man = int(man or 0)
    if man <= 0:
        return '0원'
    eok = man / 10000
    if eok >= 1:
        return f'{eok:.0f}억 원' if eok == int(eok) else f'{eok:.1f}억 원'
    return f'{man:,}만 원'


class Command(BaseCommand):
    help = '실데이터(startup_data.json) 기반 스타트업 시드'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='계정 미연결 시드 삭제 후 재생성')

    def handle(self, *args, **opts):
        if opts['reset']:
            deleted, _ = StartupProfile.objects.filter(user__isnull=True).delete()
            self.stdout.write(self.style.WARNING(f'시드 {deleted}건 삭제'))

        # core/data/startup_data.json 의 실데이터를 적재.
        # '여기에 ...' 같은 템플릿/빈 이름 행은 건너뛴다.
        created = self._load_json()

        total = StartupProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'시드 완료: {created}건 신규 (전체 스타트업 {total}건)'
        ))
        self.stdout.write(self.style.WARNING(
            '주의: 금액(funding_needed·revenue)은 원→만원 자동 변환되어 저장됩니다.'
        ))

    def _load_json(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent.parent / 'data' / 'startup_data.json'
        if not path.exists():
            return 0
        try:
            rows = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            self.stderr.write(f'startup_data.json 파싱 실패: {e}')
            return 0

        def won_to_man(v):
            """금액 입력을 만원 단위(저장 단위)로 정규화.
            큰 값(>=백만)은 원 단위로 보고 ÷10000, 작은 값(<백만, 0 제외)은
            억 단위로 보고 ×10000. (예: 800000000원→80000만원=8억, 8억→80000만원)"""
            try:
                v = int(v)
            except (TypeError, ValueError):
                return 0
            if v <= 0:
                return 0
            if v < 1000000:          # 백만 미만 → '억' 단위 입력으로 간주
                return v * 10000
            return int(round(v / 10000))   # 원 단위 → 만원

        def enrich(f):
            """중첩 데이터(business_model·products·forecast·achievements)에서
            AI 리포트용 텍스트 + 정량 신호(signals)를 추출."""
            import re
            bm = f.get('business_model') or {}
            prods = f.get('products') or []
            fc = f.get('forecast') or {}
            ach = f.get('achievements') or []
            ov = (f.get('overseas_expansion') or {}).get('activities') or []

            desc_parts = [f.get('description', '')]
            if f.get('business_content'):
                desc_parts.append('주요 사업: ' + ' / '.join(f['business_content'][:4]))
            if bm.get('revenue_model'):
                desc_parts.append('수익모델: ' + ', '.join(bm['revenue_model']))
            if bm.get('major_customers'):
                desc_parts.append('주요 고객: ' + ', '.join(bm['major_customers'][:4]))
            if bm.get('major_markets'):
                desc_parts.append('주요 시장: ' + ', '.join(bm['major_markets'][:4]))
            if prods:
                desc_parts.append('제품: ' + ', '.join(p.get('name', '') for p in prods[:4]))
            pc = fc.get('patent_count') or {}
            patents = int(pc.get('domestic', 0) or 0) + int(pc.get('overseas', 0) or 0)
            ip_total = int(fc.get('intellectual_property_count', 0) or 0)
            patents = max(patents, ip_total)
            if patents:
                desc_parts.append(f'지식재산권/특허 약 {patents}건')
            # 후속투자 금액: achievements 텍스트에서 '약 NNN억원 후속/투자' 추출(원→만원)
            follow_on = 0
            for a in ach:
                t = a.get('description', '')
                if ('투자' in t) or ('후속' in t):
                    m = re.search(r'약?\s*([\d,]+)\s*억', t)
                    if m:
                        follow_on = max(follow_on, int(m.group(1).replace(',', '')) * 10000)
            achievement_lines = [a.get('description', '') for a in ach][:6]
            if achievement_lines:
                desc_parts.append('주요 성과: ' + ' / '.join(achievement_lines))
            if ov:
                desc_parts.append('해외 진출: ' + ' / '.join(ov[:3]))

            description = '\n'.join(p for p in desc_parts if p)
            diff = ' / '.join((bm.get('special_features') or [])[:5])
            signals = {
                'patents': patents,
                'follow_on_funding': follow_on,          # 만원
                'has_overseas': bool(ov),
                'key_customers': (bm.get('major_customers') or [])[:5],
                'key_markets': (bm.get('major_markets') or [])[:5],
                'revenue_model': (bm.get('revenue_model') or [])[:3],
                'achievement_count': len(ach),
                'products_count': len(prods),
            }
            # 간결 요약(핵심만): 한 줄 소개 + 핵심 지표 칩
            base = (f.get('description') or '').split('.')[0].split('\n')[0].strip()
            chips = []
            rv = won_to_man(f.get('revenue', 0))
            if rv:
                chips.append(f'연매출 {_fmt_eok(rv)}')
            if follow_on:
                chips.append(f'후속투자 {_fmt_eok(follow_on)}')
            if patents:
                chips.append(f'특허 {patents}건')
            if bm.get('major_customers'):
                chips.append(f'고객 {bm["major_customers"][0]} 등')
            if ov:
                chips.append('해외 진출')
            summary = base
            if chips:
                summary = (base + '  ·  ' if base else '') + ' · '.join(chips[:4])
            return description, diff, signals, summary

        n = 0
        for row in rows:
            f = row.get('fields', row)
            name = (f.get('name') or '').strip()
            if not name or '여기에' in name:      # 템플릿/빈 행 스킵
                continue
            description, diff, signals, summary = enrich(f)
            from core.recommend import normalize_stage
            raw_stage = f.get('stage', '')
            canon_stage = normalize_stage(raw_stage)
            # 원래 단계 설명이 표준코드와 다르면 description 에 보존
            if raw_stage and raw_stage != canon_stage:
                description = f'[단계: {raw_stage}]\n' + description
            vals = dict(
                industry=f.get('industry', ''), stage=canon_stage,
                region=f.get('region') or f.get('location', ''),
                funding_needed=won_to_man(f.get('funding_needed', 0)),
                team_size=f.get('team_size', 1) or 1,
                revenue=won_to_man(f.get('revenue', 0)),
                founded_year=f.get('founded_year', 2024) or 2024,
                description=description, differentiation=diff, signals=signals,
                summary=summary,
            )
            obj, was = StartupProfile.objects.get_or_create(
                name=name, defaults=dict(user=None, **vals))
            for k, v in vals.items():       # 기존 항목도 최신 값으로 갱신
                setattr(obj, k, v)
            obj.save()
            n += int(was)
        if n:
            self.stdout.write(f'  startup_data.json 에서 {n}건 추가 적재')
        return n
