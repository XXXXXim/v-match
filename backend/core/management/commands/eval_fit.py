"""
FIT 점수 엔진 평가를 실행한다 (API 키 불필요).

  python manage.py eval_fit                 # 현재 DB의 VC × 스타트업 전체 쌍 평가
  python manage.py eval_fit --out PATH      # 결과 JSON 저장 위치 (기본: ../docs/eval/fit_eval.json)

데모 데이터로 재현하려면:
  DJANGO_DB_PATH=/tmp/eval.sqlite3 python manage.py demo_db ensure && DJANGO_DB_PATH=/tmp/eval.sqlite3 python manage.py eval_fit
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core import fit_eval
from core.models import StartupProfile, VCProfile

DEFAULT_OUT = Path(settings.BASE_DIR).parent / 'docs' / 'eval' / 'fit_eval.json'


class Command(BaseCommand):
    help = 'FIT 점수 엔진 평가 (재현성·범위·단조성·thesis 반영·데이터 계약)'

    def add_arguments(self, parser):
        parser.add_argument('--out', default=str(DEFAULT_OUT))

    def handle(self, *args, **opts):
        res = fit_eval.run(VCProfile.objects.all(), StartupProfile.objects.all())
        out = Path(opts['out'])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')

        d, m, t, c = res['distribution'], res['monotonicity'], res['thesis'], res['data_contract']
        w = self.stdout.write
        w(f"VC {res['vcs']} × 스타트업 {res['startups']} = {res['pairs']}쌍")
        w(f"[재현성] {res['determinism_rate']:.0%}   [0~100 범위] {res['in_range_rate']:.0%}")
        w(f"[분포] 평균 {d['mean']} · 표준편차 {d['stdev']} · p10 {d['p10']} · 중앙 {d['median']} · p90 {d['p90']} "
          f"· 서로 다른 점수 {d['distinct_values']}개 · Top5에 동점 있는 VC {res['vc_top5_with_ties_rate']:.0%}")
        w(f"[단조성] {m['checks']}건 중 위반 {m['violations']}건 (통과 {m['pass_rate']:.1%})")
        w(f"[thesis] 산업 일치 {t['industry_matched_pairs']}쌍 평균 {t['mean_matched']} vs 불일치 "
          f"{t['industry_unmatched_pairs']}쌍 평균 {t['mean_unmatched']}")
        w(f"[데이터 계약] VC 산업 라벨 인식률 {c['vc_industry_label_coverage']:.0%} · 평가중시 항목 인식률 "
          f"{c['eval_emphasis_coverage']:.0%} · 단계 정규화율 {c['stage_normalized_rate']:.0%}")
        w(f"  산업 일치가 한 곳도 없는 VC: {len(c['vcs_with_no_industry_match'])}곳")
        w(f"  모르는 산업 라벨 {len(c['unknown_vc_industry_labels'])}개: {', '.join(c['unknown_vc_industry_labels'][:12])} …")
        w(f"  모르는 평가중시 항목: {', '.join(c['unknown_eval_emphasis'])}")
        w(f"  정규화 안 된 단계: {', '.join(c['unnormalized_stages'])}")
        w(f"→ {out}")
