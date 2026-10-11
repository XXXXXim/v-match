"""
확장 평가 엔진 (역량 평가 레이어).

기존 recommend.py = '투자 조건 적합도'(산업/단계/투자금/지역, thesis fit).
여기 evaluate.py = '역량 평가'(팀/트랙션/시장/재무) + 단계별 가중치 + VC 중시 항목.

원칙: 점수는 결정론적. 입력 필드가 비어있으면(0) 낮은 점수가 나오되,
기존 필드(team_size, revenue 등)를 활용해 시드 데이터도 0이 아닌 값이 나오게 한다.
"""

DIMS = ['team', 'traction', 'market', 'financials']
DIM_LABEL = {'team': '팀', 'traction': '트랙션', 'market': '시장', 'financials': '재무'}

# 단계별 우선순위(초기=팀 중심, 후기=트랙션/재무 중심). 합 = 1.0
STAGE_WEIGHTS = {
    'Seed':      {'team': 0.40, 'traction': 0.20, 'market': 0.25, 'financials': 0.15},
    'Pre-A':     {'team': 0.35, 'traction': 0.25, 'market': 0.22, 'financials': 0.18},
    'Series A':  {'team': 0.25, 'traction': 0.35, 'market': 0.20, 'financials': 0.20},
    'Series B':  {'team': 0.20, 'traction': 0.35, 'market': 0.18, 'financials': 0.27},
    'Series C+': {'team': 0.15, 'traction': 0.30, 'market': 0.20, 'financials': 0.35},
}
DEFAULT_WEIGHTS = {'team': 0.30, 'traction': 0.30, 'market': 0.20, 'financials': 0.20}

EMPHASIS_MULT = 1.6  # VC가 중시한 차원에 곱하는 가중


def _cap(v, hi):
    return max(0.0, min(float(v), float(hi)))


def dimension_scores(s):
    """스타트업의 차원별 점수(0~100). 실데이터 신호(signals)를 우선 활용."""
    sig = s.signals or {}
    patents = sig.get('patents', 0) or 0
    follow_on = sig.get('follow_on_funding', 0) or 0   # 만원
    n_customers = len(sig.get('key_customers') or [])
    overseas = bool(sig.get('has_overseas'))
    n_ach = sig.get('achievement_count', 0) or 0
    n_prod = sig.get('products_count', 0) or 0

    # 팀: 팀규모(35) + 창업자경력(25) + IP/기술력 프록시(특허, 40)
    team = (_cap(s.team_size, 30) / 30 * 35
            + _cap(s.founder_experience_years, 15) / 15 * 25
            + _cap(patents, 15) / 15 * 40)
    # 트랙션/실행: 주요고객(30) + 해외(20) + 성과(25) + 제품(15) + 매출(있으면 10)
    traction = (_cap(n_customers, 5) / 5 * 30
                + (20 if overseas else 0)
                + _cap(n_ach, 5) / 5 * 25
                + _cap(n_prod, 4) / 4 * 15
                + _cap(s.revenue, 500000) / 500000 * 10)
    # 시장: 해외 확장성(35) + 단계 성숙(35) + 고객 다양성(30)
    mat = {'Growth': 1.0, 'Series C+': 1.0, 'Series C': 0.95, 'Series B': 0.85,
           'Series A': 0.7, 'Pre-A': 0.5, 'Seed': 0.4, 'Pre-Seed': 0.3}.get(s.stage, 0.4)
    market = ((35 if overseas else 10) + mat * 35 + _cap(n_customers, 5) / 5 * 30)
    # 재무: IP 자산(35) + 후속투자(35) + 매출(30)
    financials = (_cap(patents, 15) / 15 * 35
                  + _cap(follow_on, 500000) / 500000 * 35
                  + _cap(s.revenue, 500000) / 500000 * 30)
    return {
        'team': round(min(team, 100), 1),
        'traction': round(min(traction, 100), 1),
        'market': round(min(market, 100), 1),
        'financials': round(min(financials, 100), 1),
    }


def effective_weights(stage, emphasis):
    """단계별 가중치에 VC 중시 항목 가중을 적용 후 재정규화."""
    base = dict(STAGE_WEIGHTS.get(stage, DEFAULT_WEIGHTS))
    emphasis = emphasis or []
    for d in DIMS:
        if d in emphasis:
            base[d] *= EMPHASIS_MULT
    total = sum(base.values()) or 1.0
    return {d: base[d] / total for d in DIMS}


def quality_score(dims, weights):
    return round(sum(dims[d] * weights[d] for d in DIMS))


def _level(v):
    return '강점' if v >= 70 else ('보통' if v >= 40 else '약점')


def evaluate(vc, startup, fit_score, fit_weight=0.6):
    """
    종합 평가. 반환 dict:
    - dimensions: 차원별 점수
    - weights: 적용된 (단계+VC중시) 가중치
    - quality_score: 역량 종합(0~100)
    - overall: fit*0.6 + quality*0.4 (0~100)
    - dim_report: 차원별 점수/가중치/강약 + VC 중시 여부
    """
    dims = dimension_scores(startup)
    weights = effective_weights(startup.stage, vc.eval_emphasis if vc else [])
    q = quality_score(dims, weights)
    overall = round(fit_score * fit_weight + q * (1 - fit_weight))
    emphasis = (vc.eval_emphasis if vc else []) or []
    dim_report = [{
        'key': d, 'label': DIM_LABEL[d], 'score': dims[d],
        'weight_pct': round(weights[d] * 100),
        'level': _level(dims[d]),
        'vc_emphasized': d in emphasis,
    } for d in DIMS]
    return {
        'dimensions': dims, 'weights': weights,
        'quality_score': q, 'overall': overall, 'dim_report': dim_report,
    }
