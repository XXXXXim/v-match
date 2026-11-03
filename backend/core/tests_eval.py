"""FIT 엔진 평가 회귀 테스트 — 데모 실데이터(VC 20 × 스타트업 50)로 엔진 성질이 깨지지 않는지 지킨다."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from core import fit_eval
from core.models import StartupProfile, VCProfile

FIXTURE = Path(settings.BASE_DIR) / 'demo' / 'demo_fixture.json'


class FitEngineEvalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('loaddata', str(FIXTURE), verbosity=0)
        cls.res = fit_eval.run(VCProfile.objects.all(), StartupProfile.objects.all())

    def test_runs_on_all_pairs(self):
        self.assertEqual(self.res['pairs'], self.res['vcs'] * self.res['startups'])
        self.assertGreater(self.res['pairs'], 0)

    def test_deterministic_and_in_range(self):
        self.assertEqual(self.res['determinism_rate'], 1.0)
        self.assertEqual(self.res['in_range_rate'], 1.0)

    def test_improvements_never_lower_score(self):
        m = self.res['monotonicity']
        self.assertEqual(m['violations'], 0, m['examples'])

    def test_industry_match_scores_higher(self):
        t = self.res['thesis']
        self.assertGreater(t['mean_matched'], t['mean_unmatched'])
