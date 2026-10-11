"""
섹션별 정량 지표(metrics) 계산 모듈.

설계 원칙
---------
- 지표 '값'은 LLM 이 아니라 DB(StartupProfile) + DART 재무에서 결정론적으로 계산한다.
- 각 지표는 단계(stage)별 벤치마크와 비교해 status(good/ok/risk)를 부여한다.
- LLM 은 섹션 comment(해석 1~2문장)만 생성한다. metrics 에는 관여하지 않는다.
"""

# 단계별 벤치마크 (KVCA 마켓 브리프·업계 통념 기준의 보수적 추정값)
# 실데이터 확보 시 이 표만 교체하면 전체 판정이 갱신된다.
STAGE_ALIASES = {
    'seed': 'seed', '시드': 'seed', 'pre-seed': 'seed', '프리시드': 'seed',
    'pre-a': 'pre_a', 'pre_a': 'pre_a', '프리a': 'pre_a', '프리A': 'pre_a',
    'series a': 'series_a', 'a': 'series_a', '시리a': 'series_a', '시리A': 'series_a',
    'series b': 'series_b', 'b': 'series_b', '시리b': 'series_b', '시리B': 'series_b',
    'series c': 'series_c', 'c': 'series_c', '시리c': 'series_c', '시리C': 'series_c',
    'growth': 'series_c', '그로스': 'series_c', 'pre-ipo': 'series_c', '프리ipo': 'series_c',
}

BENCHMARKS = {
    'seed':    dict(arr=6000,   mom=15, ltv_cac=2.5, runway=12, gross=40, mau=20, retention=30, cagr=10),
    'pre_a':   dict(arr=18000,  mom=12, ltv_cac=3.0, runway=12, gross=50, mau=15, retention=40, cagr=10),
    'series_a':dict(arr=60000,  mom=10, ltv_cac=3.0, runway=15, gross=60, mau=10, retention=50, cagr=12),
    'series_b':dict(arr=200000, mom=8,  ltv_cac=3.5, runway=18, gross=65, mau=8,  retention=55, cagr=12),
    'series_c':dict(arr=500000, mom=6,  ltv_cac=4.0, runway=18, gross=65, mau=6,  retention=60, cagr=12),
}
DEFAULT_BM = BENCHMARKS['pre_a']


def _bm(startup):
    key = STAGE_ALIASES.get((startup.stage or '').strip().lower(), 'pre_a')
    return BENCHMARKS.get(key, DEFAULT_BM)


def _status(value, benchmark, higher_better=True, ok_ratio=0.7):
    """벤치마크 대비 good/ok/risk 판정. 데이터 없으면 na."""
    if value is None or benchmark in (None, 0):
        return 'na'
    ratio = value / benchmark
    if not higher_better:
        ratio = (benchmark / value) if value else 0
    if ratio >= 1.0:
        return 'good'
    if ratio >= ok_ratio:
        return 'ok'
    return 'risk'


def _m(label, value, display, benchmark, status, hint=''):
    return {'label': label, 'value': value, 'display': display,
            'benchmark': benchmark, 'status': status, 'hint': hint}


def _fin(startup):
    """DART 재무 시계열에서 최신연도 추출(없으면 None)."""
    data = getattr(startup, 'financials', None) or {}
    years = data.get('years') or {}
    if not years:
        return None
    latest = years[max(years.keys())]
    prev_key = sorted(years.keys())[-2] if len(years) >= 2 else None
    prev = years.get(prev_key) if prev_key else None
    return {'latest': latest, 'prev': prev}


def _financial_metrics(s, bm, fin):
    out = []
    arr = s.revenue or 0
    out.append(_m('ARR(연매출)', arr, f'{arr:,}만원', bm['arr'],
                  _status(arr, bm['arr']),
                  'DART 감사보고서 기준' if fin else '프로필 입력값'))
    if s.cac:
        ratio = round((s.ltv or 0) / s.cac, 1)
        out.append(_m('LTV/CAC', ratio, f'{ratio}x', bm['ltv_cac'],
                      _status(ratio, bm['ltv_cac']),
                      'LTV가 CAC의 3배 이상이면 단위경제 양호'))
    if fin and fin['prev'] and fin['prev'].get('revenue'):
        g = round((fin['latest']['revenue'] - fin['prev']['revenue']) / fin['prev']['revenue'] * 100)
        out.append(_m('매출 성장률(YoY)', g, f'{g}%', bm['mom'] * 4,
                      _status(g, bm['mom'] * 4), 'DART 2개년 매출 비교'))
    elif s.mom_growth:
        out.append(_m('매출 성장률(MoM)', s.mom_growth, f'{s.mom_growth}%', bm['mom'],
                      _status(s.mom_growth, bm['mom']), '전월 대비'))
    if fin and fin['latest'].get('operating_profit') is not None and fin['latest'].get('revenue'):
        opm = round(fin['latest']['operating_profit'] / fin['latest']['revenue'] * 100)
        out.append(_m('영업이익률', opm, f'{opm}%', 0, 'good' if opm >= 0 else 'risk',
                      'DART 감사보고서 기준'))
    if s.runway_months:
        out.append(_m('Runway', s.runway_months, f'{s.runway_months}개월', bm['runway'],
                      _status(s.runway_months, bm['runway']), '현 burn 기준 자금 소진까지'))
    if s.burn_rate:
        out.append(_m('월 Burn rate', s.burn_rate, f'{s.burn_rate:,}만원/월', None, 'na',
                      '월 현금 소진액'))
    return out


def _traction_metrics(s, bm):
    out = []
    if s.mau:
        out.append(_m('MAU', s.mau, f'{s.mau:,}', None, 'na', '월간 활성 사용자'))
    if s.retention_rate:
        out.append(_m('Retention', s.retention_rate, f'{s.retention_rate}%', bm['retention'],
                      _status(s.retention_rate, bm['retention']), '재방문/유지율'))
    if s.mom_growth:
        out.append(_m('MoM 성장률', s.mom_growth, f'{s.mom_growth}%', bm['mau'],
                      _status(s.mom_growth, bm['mau']), '전월 대비 성장'))
    return out


def _market_metrics(s, bm):
    out = []
    if s.market_size:
        out.append(_m('시장 규모(TAM)', s.market_size, f'{s.market_size:,}억원', None, 'na', '전체 시장 규모'))
    if s.market_growth:
        out.append(_m('시장 성장률(CAGR)', s.market_growth, f'{s.market_growth}%', bm['cagr'],
                      _status(s.market_growth, bm['cagr']), '연평균 성장률'))
    return out


def _team_metrics(s):
    out = []
    out.append(_m('팀 규모', s.team_size or 0, f'{s.team_size or 0}명', None, 'na', '전체 인원'))
    if s.founder_experience_years:
        out.append(_m('창업자 경력', s.founder_experience_years, f'{s.founder_experience_years}년',
                      5, _status(s.founder_experience_years, 5), '산업 경력 연차'))
    out.append(_m('이전 Exit', s.prior_exits or 0, f'{s.prior_exits or 0}회', None,
                  'good' if (s.prior_exits or 0) > 0 else 'na', '창업자 이전 회수 이력'))
    return out


def build_section_metrics(startup):
    bm = _bm(startup)
    fin = _fin(startup)
    return {
        '창업자·팀': _team_metrics(startup),
        '문제·시장': _market_metrics(startup, bm),
        '트랙션': _traction_metrics(startup, bm),
        '사업모델·재무': _financial_metrics(startup, bm, fin),
    }
