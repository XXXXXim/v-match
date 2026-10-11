"""
AI 자연어 분석 생성 레이어 (양방향 공용).

원칙:
1. LLM은 점수를 만들지 않는다. recommend.py가 계산한 결정론적 점수를 입력으로만 받는다.
2. 모델은 주어진 데이터만 근거로 설명한다(없는 사실 지어내지 않음).
3. (VCProfile, StartupProfile) 한 쌍당 분석을 MatchResult 에 캐시한다.
4. API 키가 없거나 실패해도 템플릿으로 폴백 → 데모가 깨지지 않는다.
"""
import hashlib

from django.conf import settings

from .models import MatchResult


def build_cache_key(vc_profile, startup):
    raw = (
        f'{vc_profile.id}:{vc_profile.updated_at.timestamp()}:'
        f'{startup.id}:{startup.updated_at.timestamp()}'
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _fallback_explanation(vc_profile, startup, score, reasons):
    head = (f'{startup.name}와(과) {vc_profile.firm_name}의 매칭 적합도는 '
            f'약 {score}%입니다.')
    body = ' '.join(reasons) if reasons else '일치 항목이 없습니다.'
    return f'{head} {body}'


def _llm_explanation(vc_profile, startup, score, sub_scores, reasons):
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    facts = (
        f'[VC: {vc_profile.firm_name}]\n'
        f'- 선호 산업: {", ".join(vc_profile.preferred_industries) or "없음"}\n'
        f'- 선호 단계: {", ".join(vc_profile.preferred_stages) or "없음"}\n'
        f'- 선호 지역: {", ".join(vc_profile.preferred_regions) or "없음"}\n'
        f'- 투자 범위: {vc_profile.min_investment}~{vc_profile.max_investment}억\n\n'
        f'[스타트업: {startup.name}]\n'
        f'- 산업: {startup.industry} / 단계: {startup.stage} / 지역: {startup.region}\n'
        f'- 희망 투자금: {startup.funding_needed}억 / 팀: {startup.team_size}명 '
        f'/ 연매출: {startup.revenue}억 / 설립: {startup.founded_year}\n'
        f'- 소개: {startup.description or "없음"}\n\n'
        f'[결정론적 매칭 점수]\n'
        f'- 총점: {score}/100 (산업 {sub_scores.get("industry")}/40, '
        f'단계 {sub_scores.get("stage")}/25, 투자금 {sub_scores.get("funding")}/20, '
        f'지역 {sub_scores.get("region")}/15)\n'
        f'- 근거: {"; ".join(reasons)}'
    )
    system = (
        '너는 VC–스타트업 매칭 분석 어시스턴트다. 주어진 사실과 이미 계산된 점수만을 '
        '근거로, 이 VC와 스타트업이 왜 이 점수로 매칭되는지 한국어로 분석하라. '
        '형식: (1) 한 줄 총평 (2) 강점(점수 높은 항목) (3) 약점/유의점(점수 낮은 항목) '
        '(4) 양측 관점 한 줄씩(VC에게 / 스타트업에게). 규칙: 점수를 새로 만들지 말 것, '
        '주어지지 않은 수치를 지어내지 말 것, 실무적으로 간결하게.'
    )
    resp = client.messages.create(
        model=getattr(settings, 'VMATCH_LLM_MODEL', 'claude-haiku-4-5-20251001'),
        max_tokens=500, system=system,
        messages=[{'role': 'user', 'content': facts}],
    )
    return ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text').strip()


def get_or_create_explanation(vc_profile, startup, score, sub_scores, reasons):
    """
    (VCProfile, StartupProfile) 쌍 기준 캐시 우선. 양방향(VC뷰/스타트업뷰) 공용.
    반환: (ai_explanation:str, source:str, cached:bool)
    """
    key = build_cache_key(vc_profile, startup)
    existing = MatchResult.objects.filter(vc=vc_profile, startup=startup).first()
    if existing and existing.cache_key == key:
        return existing.ai_explanation, existing.source, True

    if getattr(settings, 'ANTHROPIC_API_KEY', ''):
        try:
            text = _llm_explanation(vc_profile, startup, score, sub_scores, reasons)
            source = 'llm'
        except Exception:
            text = _fallback_explanation(vc_profile, startup, score, reasons)
            source = 'fallback'
    else:
        text = _fallback_explanation(vc_profile, startup, score, reasons)
        source = 'fallback'

    MatchResult.objects.update_or_create(
        vc=vc_profile, startup=startup,
        defaults={'cache_key': key, 'ai_explanation': text, 'source': source},
    )
    return text, source, False


def _money_man(man):
    """만원 단위 정수를 '3억 5,000만 원' 형태의 사람이 읽기 좋은 문자열로 변환.
    DB의 투자금 필드는 모두 '만원' 단위로 저장되므로, 표시 단계에서만 억/만원으로 환산한다."""
    n = int(round(man or 0))
    if n <= 0:
        return '0원'
    eok, rem = divmod(n, 10000)           # 1억 = 10,000만원
    if eok and rem:
        return f'{eok}억 {rem:,}만 원'
    if eok:
        return f'{eok}억 원'
    return f'{n:,}만 원'


def _fallback_briefings(vc, startup, sub_scores):
    """LLM 없이 점수 기반으로 만드는 안전한 미팅 브리핑(정보 보강 + 금액 단위 정정 버전)."""
    label = {'industry': '산업', 'stage': '단계', 'funding': '투자금', 'region': '지역'}
    # 항목별 '강점으로 인정할 최소 점수' 임계치
    th = {'industry': 32, 'stage': 20, 'funding': 16, 'region': 15}
    strong = [k for k in ('industry', 'stage', 'funding', 'region')
              if sub_scores.get(k, 0) >= th[k]]
    weak = [k for k in ('industry', 'stage', 'funding', 'region')
            if sub_scores.get(k, 0) == 0]
    s_txt = ', '.join(label[k] for k in strong) or '뚜렷한 강점 항목 없음'
    w_txt = ', '.join(label[k] for k in weak) or '특이 약점 없음'

    # 만원 단위 → 억/만원 표기로 변환(기존엔 만원 값에 '억'을 붙여 0~300000억처럼 깨졌었음)
    ticket = f'{_money_man(vc.min_investment)} ~ {_money_man(vc.max_investment)}'
    need = _money_man(startup.funding_needed)

    # VC(심사역)에게: 이 팀을 어떻게 검증할지 — 사실 기반으로 구체화
    for_vc = (
        f'[{startup.name} 체크포인트] '
        f'분야 {startup.industry or "미입력"} · 단계 {startup.stage or "미입력"} · '
        f'지역 {startup.region or "미입력"} · 팀 {startup.team_size or 0}명. '
        f'선호 적합 항목: {s_txt} / 점검 필요: {w_txt}. '
        f'이 팀의 희망 투자금은 {need}이며, 본사 티켓({ticket}) 범위 안에 들어오는지와 '
        f'{w_txt} 항목의 간극을 어떤 계획으로 메울지 미팅에서 확인하세요.'
    )

    # 스타트업(창업자)에게: 이 VC를 어떻게 공략할지 — 행동 가능한 조언으로
    for_startup = (
        f'[{vc.firm_name} 공략 전략] '
        f'이 VC와 잘 맞는 부분({s_txt})을 먼저 부각하고, '
        f'차이가 있는 부분({w_txt})은 보완 계획과 함께 선제적으로 설명하세요. '
        f'이 VC의 투자 티켓은 {ticket}입니다. '
        f'희망 투자금 {need}을 이 범위에 맞춰 단계별 자금 사용 계획(런웨이·핵심 마일스톤)으로 제시하면 설득력이 올라갑니다.'
    )
    return for_vc, for_startup, 'fallback'


def generate_meeting_briefings(vc, startup, score, sub_scores):
    """수락된 매칭에 대해 양측 미팅 준비 브리핑 생성. (vc_brief, startup_brief, source)"""
    if not getattr(settings, 'ANTHROPIC_API_KEY', ''):
        return _fallback_briefings(vc, startup, sub_scores)
    try:
        import json
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        facts = (
            f'VC {vc.firm_name}: 선호산업 {vc.preferred_industries}, 선호단계 {vc.preferred_stages}, '
            f'선호지역 {vc.preferred_regions}, 투자범위 {_money_man(vc.min_investment)}~{_money_man(vc.max_investment)}, '
            f'소개 "{vc.bio}".\n'
            f'스타트업 {startup.name}: {startup.industry}/{startup.stage}/{startup.region}, '
            f'희망투자 {_money_man(startup.funding_needed)}, 팀 {startup.team_size}명, 매출 {_money_man(startup.revenue)}, '
            f'소개 "{startup.description}".\n'
            f'매칭 점수 {score}/100 (항목별 {sub_scores}).'
        )
        system = (
            '너는 VC–스타트업 미팅 준비 코치다. 위 정보만 근거로, 곧 미팅할 양측에게 줄 '
            '"족집게 브리핑"을 작성하라. 반드시 아래 JSON만 출력(설명·마크다운 금지): '
            '{"vc": "심사역에게 줄 브리핑: 이 팀의 강점/약점과 미팅에서 점검할 포인트, 1~2문장", '
            '"startup": "창업자에게 줄 브리핑: 이 VC 성향에 맞춘 어필 포인트와 예상 질문 1개, 1~2문장"}. '
            '없는 사실은 지어내지 말 것.'
        )
        resp = client.messages.create(
            model=getattr(settings, 'VMATCH_LLM_MODEL', 'claude-haiku-4-5-20251001'),
            max_tokens=500, system=system,
            messages=[{'role': 'user', 'content': facts}],
        )
        raw = ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text').strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        data = json.loads(raw)
        return data.get('vc', ''), data.get('startup', ''), 'llm'
    except Exception:
        return _fallback_briefings(vc, startup, sub_scores)


def generate_vc_summary(vc):
    """VC 프로필을 투자분야·평균 투자규모·투자철학 중심으로 요약. (text, source)"""
    inds = ', '.join(vc.preferred_industries) or '제한 없음'
    stages = ', '.join(vc.preferred_stages) or '제한 없음'
    regions = ', '.join(vc.preferred_regions) or '제한 없음'
    avg = (vc.min_investment + vc.max_investment) // 2
    if not getattr(settings, 'ANTHROPIC_API_KEY', ''):
        text = (f'{vc.firm_name}은(는) {inds} 분야의 {stages} 단계 스타트업에 주로 투자합니다. '
                f'투자 규모는 약 {vc.min_investment}~{vc.max_investment}억(평균 {avg}억), '
                f'선호 지역은 {regions}입니다. {vc.bio}')
        return text.strip(), 'fallback'
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        facts = (f'투자사: {vc.firm_name}\n선호 산업: {inds}\n선호 단계: {stages}\n'
                 f'선호 지역: {regions}\n투자 범위: {vc.min_investment}~{vc.max_investment}억\n'
                 f'소개/철학: {vc.bio}')
        system = ('너는 스타트업이 VC를 빠르게 파악하도록 돕는 어시스턴트다. 아래 VC 정보를 '
                  '투자 분야 / 평균 투자 규모 / 투자 철학 3가지 관점으로 한국어 2~3문장 요약하라. '
                  '주어지지 않은 사실은 지어내지 말 것. 요약문만 출력.')
        resp = client.messages.create(
            model=getattr(settings, 'VMATCH_LLM_MODEL', 'claude-haiku-4-5-20251001'),
            max_tokens=300, system=system,
            messages=[{'role': 'user', 'content': facts}],
        )
        return ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text').strip(), 'llm'
    except Exception:
        avg = (vc.min_investment + vc.max_investment) // 2
        return (f'{vc.firm_name}은(는) {inds} 분야 {stages} 단계에 평균 {avg}억 규모로 투자합니다.',
                'fallback')


def summarize_ir_deck(text):
    """
    IR Deck 추출 텍스트로 '요약 초안' 생성 (창업자 검수·승인 전 단계).
    4대 핵심 메시지(문제·해결책 / 팀 / 트랙션 / 자금 요청) + VC 중시 지표를 포함.
    키 없거나 실패 시 앞부분 발췌로 폴백.
    반환: (summary:str, source:str)
    """
    text = (text or '').strip()
    if not text:
        return '문서에서 텍스트를 추출하지 못했습니다. (스캔 PDF일 수 있음)', 'fallback'
    if not getattr(settings, 'ANTHROPIC_API_KEY', ''):
        return (f'[키 미설정 — 앞부분 발췌]\n{text[:600]}...', 'fallback')
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system = (
            '너는 VC 투자 심사역을 돕는 어시스턴트다. 아래 IR Deck 텍스트를 읽고 '
            '한국어 요약 초안을 작성하라. 반드시 다음 4대 핵심 메시지를 각각 한 단락으로 '
            '포함하라: (1) 문제·해결책 (2) 팀 (3) 트랙션 (4) 자금 요청. '
            '또한 VC가 중시하는 지표(매출/성장률/시장규모/유닛이코노믹스 등)가 문서에 '
            '있으면 함께 짚어라. 문서에 없는 수치는 지어내지 말 것. '
            '이 초안은 창업자가 검수·수정 후 승인하므로 사실 위주로 간결하게.'
        )
        resp = client.messages.create(
            model=getattr(settings, 'VMATCH_LLM_MODEL', 'claude-haiku-4-5-20251001'),
            max_tokens=700, system=system,
            messages=[{'role': 'user', 'content': text[:12000]}],
        )
        out = ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text')
        return out.strip(), 'llm'
    except Exception:
        return (f'[요약 생성 실패 — 앞부분 발췌]\n{text[:600]}...', 'fallback')


def _fallback_deep(startup, dims):
    def lv(v): return '강점' if v >= 70 else ('보통' if v >= 40 else '약점')
    lines = [
        f'■ 팀 역량 ({dims["team"]:.0f}/100, {lv(dims["team"])}): '
        f'창업자 경력 {startup.founder_experience_years}년, 엑싯 {startup.prior_exits}회, 팀 {startup.team_size}명.',
        f'■ 제품 차별화: {startup.differentiation or "입력된 차별화 정보 없음"}',
        f'■ 시장 ({dims["market"]:.0f}/100, {lv(dims["market"])}): '
        f'TAM {startup.market_size}억, 성장률 {startup.market_growth}%.',
        f'■ 트랙션 ({dims["traction"]:.0f}/100, {lv(dims["traction"])}): '
        f'매출 {startup.revenue}억, MAU {startup.mau}, 유지율 {startup.retention_rate}%, 월성장 {startup.mom_growth}%.',
        f'■ 재무 ({dims["financials"]:.0f}/100, {lv(dims["financials"])}): '
        f'LTV/CAC {round(startup.ltv/startup.cac,1) if startup.cac else "N/A"}, 런웨이 {startup.runway_months}개월.',
    ]
    return '\n'.join(lines), 'fallback'


def generate_deep_analysis(vc, startup, dims):
    """
    매칭 성사 후에만 호출. 피치덱/IR 요약 + 확장 지표로 다측면 심층 분석.
    반환: (text, source)
    """
    if not getattr(settings, 'ANTHROPIC_API_KEY', ''):
        return _fallback_deep(startup, dims)
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        facts = (
            f'[VC] {vc.firm_name} / 선호산업 {vc.preferred_industries} / 중시항목 {vc.eval_emphasis}\n'
            f'[스타트업] {startup.name} ({startup.industry}/{startup.stage}/{startup.region})\n'
            f'- 팀: 창업자경력 {startup.founder_experience_years}년, 엑싯 {startup.prior_exits}회, '
            f'팀 {startup.team_size}명, 팀문화 "{startup.team_culture}"\n'
            f'- 제품 차별화: {startup.differentiation}\n'
            f'- 트랙션: 매출 {startup.revenue}억, MAU {startup.mau}, 유지율 {startup.retention_rate}%, '
            f'월성장 {startup.mom_growth}%\n'
            f'- 시장: TAM {startup.market_size}억, 성장률 {startup.market_growth}%\n'
            f'- 재무: CAC {startup.cac}만, LTV {startup.ltv}만, burn {startup.burn_rate}만/월, '
            f'런웨이 {startup.runway_months}개월\n'
            f'- 비전: {startup.vision}\n'
            f'- IR 요약: {startup.ir_summary or "없음"}\n'
            f'- 역량 점수(참고): {dims}'
        )
        system = (
            '너는 VC 투자심사를 돕는 애널리스트다. 매칭이 성사된 두 주체에 대해, 주어진 데이터만 '
            '근거로 한국어 심층 분석을 작성하라. 4개 섹션으로: ■ 팀 역량 ■ 제품 차별화 ■ 시장 규모·성장성 '
            '■ 재무 건전성. 각 섹션은 사실 기반 2~3문장으로 강점과 리스크를 함께 짚어라. '
            '없는 수치는 지어내지 말 것. 투자 결정에 도움이 되도록 구체적으로.'
        )
        resp = client.messages.create(
            model=getattr(settings, 'VMATCH_LLM_MODEL', 'claude-haiku-4-5-20251001'),
            max_tokens=900, system=system,
            messages=[{'role': 'user', 'content': facts}],
        )
        out = ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text').strip()
        return out, 'llm'
    except Exception:
        return _fallback_deep(startup, dims)
