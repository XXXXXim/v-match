"""
FIT 점수 엔진 평가 (정답 라벨 없이 엔진을 검증하는 방법).

VC-스타트업 매칭에는 "이 둘이 맞다"는 정답 데이터가 없다. 그래서 정답 대신 엔진이 반드시 지켜야 하는
성질을 정해 두고, 실데이터(VC 20 × 스타트업 50 = 1,000쌍) 전체에서 몇 %가 지키는지 잰다.

1. 재현성     같은 입력 → 같은 점수 (LLM 이 점수에 관여하지 않는다는 설계 검증)
2. 범위·변별력 점수가 0~100 안에 있고, 한 점수에 몰리지 않는가 (분포, 동점 비율)
3. 단조성     특허·고객·해외진출·매출·후속투자·팀이 '늘었는데' 점수가 '떨어지면' 위반 (메타모픽 테스트)
4. thesis 반영 산업이 맞는 쌍이 안 맞는 쌍보다 점수가 높은가
5. 데이터 계약 VC 데이터의 산업·평가중시 항목 이름과 스타트업 단계가 엔진이 아는 어휘와 맞는가
   (어휘가 안 맞으면 계산은 돌아가도 조용히 0점·무시 처리된다 → 숫자로 드러낸다)

Django 모델에 의존하지 않는다. 속성만 있으면 되므로 테스트·관리 명령 어디서든 쓸 수 있다.
"""
import copy
import statistics

from .evaluate import DIMS
from .recommend import IND_KEYWORDS, STAGE_ORDER, _industry_score, calculate_recommendation

# 단조성 검사에 쓰는 '좋아지는' 변화들 (이름, 스타트업을 바꾸는 함수)
IMPROVEMENTS = [
    ('특허 +5건', lambda s: s.signals.__setitem__('patents', (s.signals.get('patents') or 0) + 5)),
    ('주요 고객 +1곳', lambda s: s.signals.__setitem__('key_customers', list(s.signals.get('key_customers') or []) + ['신규 고객'])),
    ('해외 진출', lambda s: s.signals.__setitem__('has_overseas', True)),
    ('성과 +1건', lambda s: s.signals.__setitem__('achievement_count', (s.signals.get('achievement_count') or 0) + 1)),
    ('매출 증가', lambda s: setattr(s, 'revenue', (s.revenue or 0) * 2 + 10000)),
    ('후속투자 +10억', lambda s: s.signals.__setitem__('follow_on_funding', (s.signals.get('follow_on_funding') or 0) + 100000)),
    ('팀 +5명', lambda s: setattr(s, 'team_size', (s.team_size or 0) + 5)),
]


def _clone(startup):
    s = copy.copy(startup)
    s.signals = dict(startup.signals or {})
    return s


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def run(vcs, startups):
    vcs, startups = list(vcs), list(startups)
    pairs = [(v, s) for v in vcs for s in startups]

    # 1·2. 재현성, 범위, 분포
    scores, deterministic = [], 0
    for v, s in pairs:
        a = calculate_recommendation(v, s)
        b = calculate_recommendation(v, _clone(s))
        deterministic += a[0] == b[0] and a[1] == b[1]
        scores.append(a[0])
    in_range = sum(0 <= x <= 100 for x in scores)

    top5_tie = 0
    for v in vcs:
        top = sorted((calculate_recommendation(v, s)[0] for s in startups), reverse=True)[:5]
        top5_tie += len(set(top)) < len(top)

    # 3. 단조성 (메타모픽)
    checks, violations = 0, []
    for name, change in IMPROVEMENTS:
        for v, s in pairs:
            better = _clone(s)
            change(better)
            before, after = calculate_recommendation(v, s)[0], calculate_recommendation(v, better)[0]
            checks += 1
            if after < before:
                violations.append({'change': name, 'vc': str(getattr(v, 'firm_name', '')),
                                   'startup': str(getattr(s, 'name', '')), 'before': before, 'after': after})

    # 4. thesis 반영: 산업 일치 여부별 평균 점수
    matched, unmatched = [], []
    for (v, s), score in zip(pairs, scores):
        r, _ = _industry_score(v, s)
        (matched if r >= 1.0 else unmatched).append(score)

    # 5. 데이터 계약 (어휘 일치)
    known_ind = set(IND_KEYWORDS) | {'All', 'Other'} | {s.industry for s in startups}
    vc_labels = [i for v in vcs for i in (v.preferred_industries or [])]
    unknown_ind = sorted({i for i in vc_labels if i not in known_ind})
    emph = [e for v in vcs for e in (v.eval_emphasis or [])]
    unknown_emph = sorted({e for e in emph if e not in DIMS})
    off_stage = sorted({s.stage for s in startups if s.stage not in STAGE_ORDER})
    vc_no_industry_hit = [str(getattr(v, 'firm_name', '')) for v in vcs
                          if all(_industry_score(v, s)[0] < 1.0 for s in startups)]

    def ratio(a, b):
        return round(a / b, 3) if b else 0.0

    return {
        'pairs': len(pairs), 'vcs': len(vcs), 'startups': len(startups),
        'determinism_rate': ratio(deterministic, len(pairs)),
        'in_range_rate': ratio(in_range, len(pairs)),
        'distribution': {
            'mean': round(statistics.mean(scores), 1), 'stdev': round(statistics.pstdev(scores), 1),
            'min': min(scores), 'p10': _pct(scores, 10), 'median': _pct(scores, 50),
            'p90': _pct(scores, 90), 'max': max(scores), 'distinct_values': len(set(scores)),
        },
        'vc_top5_with_ties_rate': ratio(top5_tie, len(vcs)),
        'monotonicity': {'checks': checks, 'violations': len(violations),
                         'pass_rate': ratio(checks - len(violations), checks), 'examples': violations[:5]},
        'thesis': {
            'industry_matched_pairs': len(matched), 'industry_unmatched_pairs': len(unmatched),
            'mean_matched': round(statistics.mean(matched), 1) if matched else None,
            'mean_unmatched': round(statistics.mean(unmatched), 1) if unmatched else None,
        },
        'data_contract': {
            'vc_industry_label_coverage': ratio(sum(i in known_ind for i in vc_labels), len(vc_labels)),
            'unknown_vc_industry_labels': unknown_ind,
            'vcs_with_no_industry_match': vc_no_industry_hit,
            'eval_emphasis_coverage': ratio(sum(e in DIMS for e in emph), len(emph)),
            'unknown_eval_emphasis': unknown_emph,
            'stage_normalized_rate': ratio(sum(s.stage in STAGE_ORDER for s in startups), len(startups)),
            'unnormalized_stages': off_stage,
        },
    }
