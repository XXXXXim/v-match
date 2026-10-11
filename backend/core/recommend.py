"""
룰 기반 FIT 점수 계산 (총점 100, 100% 결정론적).

설계(개정): FIT = 투자조건 적합도(40) + 스타트업 역량(60).
  - 투자조건 적합도: 이 VC의 thesis(산업/단계/지역/투자금)에 부합하는가
  - 스타트업 역량: 실데이터(매출·후속투자·특허·해외진출·고객·단계)로 본 투자 매력도
초기 시드의 빈 숫자 필드(MAU 등)에 의존하지 않고, 실제 존재하는 신호를 사용한다.
같은 입력이면 항상 같은 점수(재현성) → LLM 은 점수에 관여하지 않고 설명만 생성.
"""

# 투자조건(40) : 역량(60)  — 투자금액(check)은 FIT 기준에서 제외
W_THESIS = {'industry': 20, 'stage': 12, 'region': 8}
# 초기·딥테크도 공정하게 평가: 특허·트랙션·팀 비중↑, 매출/후속투자는 있으면 가점
W_STRENGTH = {'ip': 16, 'traction': 18, 'team': 8, 'revenue': 8, 'funding_raised': 4, 'maturity': 6}

STAGE_ORDER = ['Pre-Seed', 'Seed', 'Pre-A', 'Series A', 'Series B', 'Series C', 'Series C+', 'Growth']


def normalize_stage(text):
    """자유 텍스트 단계('엔젤투자 · 시제품 제작', 'Series A(Pre A)' 등)를 표준 코드로 변환."""
    t = (text or '').lower()
    if 'pre-seed' in t or '프리시드' in t or '프리 시드' in t:
        return 'Pre-Seed'
    if 'series b' in t or '시리즈 b' in t or '시리즈b' in t:
        return 'Series B'
    if 'series c' in t or '시리즈 c' in t or '시리즈c' in t:
        return 'Series C'
    if 'series a' in t or '시리즈 a' in t or '시리즈a' in t:
        return 'Series A'
    if 'pre-a' in t or 'pre a' in t or '프리a' in t or '프리 a' in t or 'poc' in t or '양산' in t:
        return 'Pre-A'
    if 'growth' in t or '그로스' in t:
        return 'Growth'
    if ('seed' in t or '시드' in t or '엔젤' in t or '시제품' in t
            or '제품 생산' in t or '제품생산' in t):
        return 'Seed'
    if '시장출시' in t or '시장 출시' in t or '시장검증' in t or '시장 검증' in t:
        return 'Series A'
    return text or 'Seed'

# 한글 세분류/설명 → 표준 카테고리 추론용 키워드
IND_KEYWORDS = {
    'AI/ML': ['AI', '인공지능', '머신러닝', '딥러닝', '데이터 분석', '알고리즘'],
    'Fintech': ['핀테크', '결제', '금융', '페이', '정산', '송금'],
    'Healthcare': ['헬스', '의료', '병원', '건강', '진단', '수면', '바이오'],
    'Bio': ['바이오', '제약', '생명', '신약', '진단'],
    'SaaS': ['소프트웨어', '솔루션', 'ERP', 'SaaS', '클라우드', '플랫폼', 'SW'],
    'E-commerce': ['커머스', '쇼핑', '판매', '리테일', '뷰티', '유통'],
    'EdTech': ['교육', '에듀', '학습', '러닝', '영유아', '학생', '교실'],
    'Hardware': ['소재', '반도체', '디스플레이', '카메라', '센서', '제조', '전자', '하드웨어', '계측'],
    'Content': ['콘텐츠', '미디어', 'SNS', '광고', '커뮤니티'],
    'Mobility': ['모빌리티', '자동차', '배터리', '전기차', 'ESS'],
}


def _fmt_man(man):
    man = int(man or 0)
    if man == 0:
        return '0원'
    eok, rem = divmod(man, 10000)
    if eok and rem:
        return f'{eok}억 {rem:,}만 원'
    if eok:
        return f'{eok}억 원'
    return f'{man:,}만 원'


def infer_categories(startup):
    """스타트업 산업+설명 텍스트에서 표준 카테고리 집합 추론."""
    text = f'{startup.industry} {startup.description or ""} {startup.differentiation or ""}'
    cats = set()
    for cat, kws in IND_KEYWORDS.items():
        if any(kw in text for kw in kws):
            cats.add(cat)
    return cats


def _industry_score(vc, startup):
    prefs = vc.preferred_industries or []
    if 'All' in prefs:
        return 1.0, '전 산업 선호(All)'
    if startup.industry in prefs:
        return 1.0, f'선호 산업({startup.industry}) 일치'
    cats = infer_categories(startup)
    hit = cats & set(prefs)
    if hit:
        return 1.0, f'산업 매칭: {", ".join(sorted(hit))}'
    if 'Other' in prefs:
        return 0.6, '기타(Other) 산업 선호에 부합'
    return 0.0, None


def _stage_score(startup_stage, preferred_stages):
    """정확=1.0, 인접=0.6, 2칸=0.3, 그 이상=0.15(완전 0은 아님)."""
    if not preferred_stages:
        return 0.5, None
    if startup_stage in preferred_stages:
        return 1.0, 'exact'
    if startup_stage not in STAGE_ORDER:
        return 0.3, None
    s_idx = STAGE_ORDER.index(startup_stage)
    best = 0.15
    for ps in preferred_stages:
        if ps in STAGE_ORDER:
            dist = abs(STAGE_ORDER.index(ps) - s_idx)
            best = max(best, {1: 0.6, 2: 0.3}.get(dist, 0.15))
    return best, ('near' if best > 0.15 else None)


def _check_score(amount, lo, hi):
    """범위 안=1.0, 근접=부분, 멀면 0.2(완전 0은 아님 — 우량 스타트업 보호)."""
    if not amount:
        return 0.4, None          # 희망액 미기재 → 중립
    if lo <= amount <= hi:
        return 1.0, 'in_range'
    span = max(hi - lo, 1)
    gap = (lo - amount) if amount < lo else (amount - hi)
    if gap < span * 0.5:
        return round(1.0 - gap / (span * 0.5) * 0.6, 3), 'near'
    return 0.2, None


def _tier(v, thresholds):
    """thresholds: [(임계값, 점수비율)] 내림차순. 충족하는 첫 비율 반환."""
    for t, r in thresholds:
        if v >= t:
            return r
    return 0.0


def _strength(startup):
    """실데이터 기반 역량(0~1 비율) + 근거. 초기·딥테크도 공정하게."""
    sig = startup.signals or {}
    reasons = []
    # IP/특허
    pat = _tier(sig.get('patents', 0) or 0, [(20, 1.0), (10, 0.85), (5, 0.65), (1, 0.4)])
    if sig.get('patents'):
        reasons.append(f'지식재산권 {sig["patents"]}건')
    # 트랙션/실행: 주요고객 + 해외 + 성과 + 제품
    nc = len(sig.get('key_customers') or [])
    tr = min(nc, 5) / 5 * 0.35
    if sig.get('has_overseas'):
        tr += 0.25
        reasons.append('해외 진출')
    tr += min(sig.get('achievement_count', 0) or 0, 5) / 5 * 0.25
    tr += min(sig.get('products_count', 0) or 0, 4) / 4 * 0.15
    tr = min(tr, 1.0)
    if nc:
        reasons.append(f'주요 고객 {nc}곳')
    # 팀: 팀규모 + 창업자 경력
    team = (min((startup.team_size or 0) / 20, 1.0) * 0.7
            + min((startup.founder_experience_years or 0) / 10, 1.0) * 0.3)
    # 매출(있으면 가점)
    rev = _tier(startup.revenue or 0, [(1000000, 1.0), (100000, 0.8), (10000, 0.55), (1, 0.3)])
    if startup.revenue:
        reasons.append(f'연매출 {_fmt_man(startup.revenue)}')
    # 후속투자(있으면 가점)
    fo = _tier(sig.get('follow_on_funding', 0) or 0,
               [(300000, 1.0), (100000, 0.7), (30000, 0.5), (1, 0.3)])
    if sig.get('follow_on_funding'):
        reasons.append(f'후속투자 {_fmt_man(sig["follow_on_funding"])} 유치')
    # 단계 성숙도(보조)
    mat = {'Growth': 1.0, 'Series C+': 1.0, 'Series C': 0.95, 'Series B': 0.85,
           'Series A': 0.7, 'Pre-A': 0.5, 'Seed': 0.4, 'Pre-Seed': 0.3}.get(startup.stage, 0.4)
    return {'ip': pat, 'traction': tr, 'team': team,
            'revenue': rev, 'funding_raised': fo, 'maturity': mat}, reasons


def calculate_recommendation(vc_profile, startup):
    """(total:int, sub:dict, reasons:list[str]) 반환."""
    sub = {}
    reasons = []

    # ── 투자조건 적합도 (40) ──
    r, msg = _industry_score(vc_profile, startup)
    sub['industry'] = round(W_THESIS['industry'] * r, 1)
    if msg:
        reasons.append(msg)

    r, kind = _stage_score(startup.stage, vc_profile.preferred_stages)
    sub['stage'] = round(W_THESIS['stage'] * r, 1)
    if kind == 'exact':
        reasons.append(f'선호 단계({startup.stage}) 일치')
    elif kind == 'near':
        reasons.append(f'단계({startup.stage})가 선호 단계와 인접')

    regions = vc_profile.preferred_regions or []
    s_region = startup.region or ''
    if ('전국' in regions) or ('기타' in regions) or not regions:
        sub['region'] = W_THESIS['region']
        reasons.append('지역 제약 없음(전국/기타)')
    elif any(r and (r in s_region or s_region in r) for r in regions):
        sub['region'] = W_THESIS['region']
        reasons.append(f'선호 지역({s_region}) 일치')
    else:
        sub['region'] = 0

    # ── 스타트업 역량 (60) ──
    strength, s_reasons = _strength(startup)
    for k, w in W_STRENGTH.items():
        sub[k] = round(w * strength[k], 1)
    reasons.extend(s_reasons)

    total = round(sum(sub.values()))
    if not reasons:
        reasons.append('일치하는 조건이 없습니다.')
    return total, sub, reasons
