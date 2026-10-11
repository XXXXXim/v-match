"""
AI 분석 리포트 — V-Match 의 핵심 기능.

본질: DB에 모델링된 '실제 스타트업·VC 데이터'(산업/단계/지역/투자금/팀·트랙션·
시장·재무 + VC 선호조건)를 근거로 두 곳이 얼마나 FIT 한지 AI가 분석한다.

- 기존 데이터(시드/실데이터)가 있는 경우 → 구조화 데이터로 FIT 분석(주 경로).
  · fit_score 는 실데이터 기반 결정론 점수(recommend+evaluate)로 산출(재현성).
  · summary 는 LLM 이 그 데이터를 근거로 작성.
- 신규 가입자처럼 DB에 정형 데이터가 아직 없는 경우 → 업로드한 덱(PDF)을 LLM이 읽고 판단.

LLM 호출: 표준 OpenAI Chat Completions API.
  POST https://api.openai.com/v1/chat/completions
  headers: Authorization: Bearer {OPENAI_API_KEY}
  body: {"model": OPENAI_MODEL, "messages": [...]}
키 설정: backend/.env 의 OPENAI_API_KEY. 없으면 템플릿 폴백(데모 안 깨짐).
"""
import json
import ssl
import urllib.request
import urllib.error

from django.conf import settings

from .recommend import calculate_recommendation, _fmt_man
from .evaluate import evaluate
from .metrics import build_section_metrics, _fin

OPENAI_BASE = 'https://api.openai.com/v1'

# macOS 등에서 시스템 루트 인증서를 못 찾는 SSL 검증 실패를 막기 위해
# certifi 의 최신 CA 번들로 SSL 컨텍스트를 구성한다(없으면 기본값).
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()


# ============================================================
#  LLM 호출 — 표준 OpenAI Chat Completions
# ============================================================
def _api_key():
    return (getattr(settings, 'OPENAI_API_KEY', '') or '').strip()


def _model():
    return getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini') or 'gpt-4o-mini'


def has_llm():
    """OpenAI 키가 설정되어 있는지(폴백 리포트 자동 재생성 판단에 사용)."""
    return bool(_api_key())


def _post_openai(payload, timeout):
    """OpenAI Chat Completions 호출. 성공 시 dict, 실패 시 예외(HTTPError 포함)."""
    req = urllib.request.Request(
        f'{OPENAI_BASE}/chat/completions',
        data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json',
                 'Authorization': f'Bearer {_api_key()}'},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _llm_generate(instructions, input_text, json_mode=False, timeout=60, max_tokens=800):
    """LLM 호출. 성공 시 (텍스트, 'openai'), 키 없거나 실패 시 (None, None)."""
    if not _api_key():
        return None, None
    payload = {
        'model': _model(),
        'messages': [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': input_text},
        ],
        'temperature': 0.4,
        'max_tokens': max_tokens,
    }
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
    try:
        data = _post_openai(payload, timeout)
        text = (data['choices'][0]['message']['content'] or '').strip()
        return (text, 'openai') if text else (None, None)
    except Exception:
        return None, None


def llm_test():
    """
    진단용 실호출. (ok: bool, label: str, detail: str) 반환.
    실패 시 OpenAI가 내려준 실제 에러(상태코드+본문)를 그대로 담아 원인 파악을 돕는다.
    """
    if not _api_key():
        return False, '키 없음', 'OPENAI_API_KEY 가 비어 있습니다.'
    payload = {'model': _model(),
               'messages': [{'role': 'user', 'content': '연결 테스트. "정상"이라고만 답하세요.'}],
               'max_tokens': 5}
    try:
        data = _post_openai(payload, timeout=20)
        return True, 'OK', (data['choices'][0]['message']['content'] or '').strip()
    except urllib.error.HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', 'ignore')
        except Exception:
            pass
        return False, f'HTTP {e.code}', body[:500]
    except Exception as e:
        return False, type(e).__name__, str(e)[:300]


# ============================================================
#  데이터 유무 판정 / 덱 텍스트 추출
# ============================================================
def _startup_has_data(s):
    return bool((s.industry or '').strip() and (s.stage or '').strip())


def _vc_has_data(vc):
    return bool(vc.preferred_industries or vc.preferred_stages or vc.preferred_regions)


def _extract_pdf_text(filefield, max_chars=6000):
    if not filefield:
        return ''
    try:
        from pypdf import PdfReader
        filefield.open('rb')
        reader = PdfReader(filefield)
        return '\n'.join((p.extract_text() or '') for p in reader.pages)[:max_chars]
    except Exception:
        return ''
    finally:
        try:
            filefield.close()
        except Exception:
            pass


def collect_documents(vc, startup):
    pitch = _extract_pdf_text(startup.pitch_deck)
    ir = _extract_pdf_text(startup.ir_deck)
    portfolio = ''
    doc = vc.portfolio_documents.first()
    if doc:
        portfolio = _extract_pdf_text(doc.file)
    return pitch, ir, portfolio


# ============================================================
#  프롬프트 / facts
# ============================================================
def _structured_facts(vc, startup, score, sub, reasons, ev):
    dims = ev['dimensions']
    sig = startup.signals or {}
    lines = [
        f'[VC: {vc.firm_name}]',
        f'- 선호 산업: {", ".join(vc.preferred_industries) or "없음"}',
        f'- 선호 단계: {", ".join(vc.preferred_stages) or "없음"}',
        f'- 선호 지역: {", ".join(vc.preferred_regions) or "없음"}',
        f'- 투자 범위: {_fmt_man(vc.min_investment)} ~ {_fmt_man(vc.max_investment)}',
        f'- 중점 평가: {", ".join(vc.eval_emphasis) if vc.eval_emphasis else "없음"}',
        f'- 소개: {vc.bio or "없음"}',
        '',
        f'[스타트업: {startup.name}]',
        f'- 산업/단계/지역: {startup.industry} / {startup.stage} / {startup.region}',
        f'- 희망 투자금: {_fmt_man(startup.funding_needed)} · 팀 {startup.team_size}명 · 설립 {startup.founded_year}',
    ]
    # 실데이터 신호(있는 것만 — 0인 지표는 굳이 강조하지 않는다)
    if startup.revenue:
        lines.append(f'- 연매출: {_fmt_man(startup.revenue)}')
    if sig.get('follow_on_funding'):
        lines.append(f'- 후속투자 유치: {_fmt_man(sig["follow_on_funding"])}')
    if sig.get('patents'):
        lines.append(f'- 지식재산권/특허: 약 {sig["patents"]}건')
    if sig.get('has_overseas'):
        lines.append('- 해외 진출: 있음')
    if sig.get('key_customers'):
        lines.append(f'- 주요 고객: {", ".join(sig["key_customers"])}')
    if sig.get('key_markets'):
        lines.append(f'- 주요 시장: {", ".join(sig["key_markets"])}')
    if startup.differentiation:
        lines.append(f'- 차별점: {startup.differentiation}')
    lines += [
        f'- 소개: {startup.description or "없음"}',
        '',
        '[결정론적 FIT 점수(실데이터 기반)]',
        f'- 종합 적합도: {score}/100',
        f'- 투자조건: 산업 {sub.get("industry")}/20, 단계 {sub.get("stage")}/12, 지역 {sub.get("region")}/8',
        f'- 역량: 특허 {sub.get("ip")}/16, 트랙션 {sub.get("traction")}/18, 팀 {sub.get("team")}/8, '
        f'매출 {sub.get("revenue")}/8, 후속투자 {sub.get("funding_raised")}/4, 성숙도 {sub.get("maturity")}/6',
        f'- 차원 평가: 팀 {dims["team"]} · 트랙션 {dims["traction"]} · 시장 {dims["market"]} · 재무 {dims["financials"]}',
        f'- 근거: {"; ".join(reasons)}',
    ]
    return '\n'.join(lines)


INSTR_PRO = (
    '너는 한국 VC 투자심사역(IC)을 보조하는 실사 분석 어시스턴트다. 주어진 정보(실데이터 또는 '
    '업로드된 덱 텍스트)를 근거로, 아래 VC 투자실사 기준에 따라 전문 분석 리포트를 작성한다. '
    '없는 사실은 지어내지 말고, 정보가 부족한 항목은 comment 에 "정보 부족"이라고 명시하라(감점 요인).\n'
    '단, 매출·후속투자·특허·주요 고객·해외 진출·주요 성과 등 제공된 실데이터가 있으면 이를 핵심 근거로 '
    '적극 반영하라. B2B·딥테크·하드웨어 기업에 MAU·retention 같은 소비자 지표가 없다는 이유만으로 '
    '과도하게 감점하지 말고, 매출/고객사/특허/수주 등 해당 업종에 맞는 트랙션 증거로 평가하라.\n\n'
    '평가 섹션(각 0~5점 앵커: 0=부재/반증, 3=기준충족·투자논의 가능, 5=업계상위·강한 우위):\n'
    '1) 창업자·팀 — 산업경험, founder-market fit, 실행력, 정직성·투명성\n'
    '2) 문제·시장 — 문제 심각도, TAM·why now, 시장 성장성, 경쟁 강도\n'
    '3) 제품·해자 — MVP 완성도, 차별화 깊이, 전환비용/네트워크 효과\n'
    '4) 트랙션 — 사용자·매출 성장, retention, pilot→paid 전환\n'
    '5) 사업모델·재무 — 수익모델, gross margin, LTV/CAC, runway\n'
    '6) 법무·리스크 — IP 귀속, 개인정보·규제, 치명적 단일 의존\n'
    '7) VC 적합성 — 이 VC의 선호 산업/단계/지역/투자금과의 정합성\n\n'
    '하드게이트(딜킬러) 6종 각각 상태를 판정: "창업자 정직성", "IP 귀속", "개인정보·보안", '
    '"캡테이블", "고객 집중도", "단위경제 지속성". status 는 pass(문제없음)/check(확인필요)/risk(위험). '
    '근거가 없으면 check.\n\n'
    '반드시 아래 JSON 만 출력하라(코드블록·설명·다른 텍스트 절대 금지):\n'
    '{"fit_score": <0~100 정수>, "summary": "<2~4문장 executive summary>", '
    '"sections": [{"name":"창업자·팀","score":<0~5>,"comment":"<1~2문장>"}, ...7개 섹션 모두], '
    '"strengths": ["<강점 2~3개>"], "concerns": ["<우려/리스크 2~3개>"], '
    '"hard_gates": [{"item":"창업자 정직성","status":"pass|check|risk"}, ...6개]}'
)

SECTION_NAMES = ['창업자·팀', '문제·시장', '제품·해자', '트랙션',
                 '사업모델·재무', '법무·리스크', 'VC 적합성']
HARD_GATES = ['창업자 정직성', 'IP 귀속', '개인정보·보안', '캡테이블', '고객 집중도', '단위경제 지속성']


def _band(score):
    """권고 밴드(PDF 기준: 85+/75~84/65~74/64-)."""
    if score >= 85:
        return '적극 투자 검토'
    if score >= 75:
        return '조건부 투자 검토'
    if score >= 65:
        return '관찰·소액 옵션 검토'
    return '신중 검토(추가 확인 필요)'


# ============================================================
#  폴백
# ============================================================
def _fallback_structured(vc, startup, score, reasons, ev):
    dims = ev['dim_report']
    strong = [d['label'] for d in dims if d['level'] == '강점']
    weak = [d['label'] for d in dims if d['level'] == '약점']
    parts = [f'{startup.name} ↔ {vc.firm_name}의 종합 적합도는 {score}점입니다.']
    if reasons:
        parts.append('적합 근거: ' + ' / '.join(reasons) + '.')
    if strong:
        parts.append('강점 영역: ' + ', '.join(strong) + '.')
    if weak:
        parts.append('보완 영역: ' + ', '.join(weak) + '.')
    parts.append('(OPENAI_API_KEY 설정 시 GPT가 실데이터 기반 상세 실사 리포트를 생성합니다.)')
    return ' '.join(parts)


def _fallback_report_json(vc, startup, score, summary, ev=None):
    """LLM 없이도 보여줄 전문 리포트 골격(결정론 데이터 기반)."""
    # 섹션 점수: 차원 데이터가 있으면 매핑, 없으면 정보부족(0)
    dim = (ev or {}).get('dimensions', {})
    sig = getattr(startup, 'signals', None) or {}
    def s5(v):  # 0~100 → 0~5
        return max(0, min(round((v or 0) / 20), 5))
    patents = sig.get('patents', 0) or 0
    has_diff = bool((startup.differentiation or '').strip())
    # 제품·해자: 차별점 텍스트 + 특허(IP 해자)
    moat = 0
    if has_diff:
        moat += 2
    moat += min(patents // 30, 2)        # 특허 많을수록 해자 +
    moat = min(moat + (1 if startup.revenue else 0), 5)
    # 법무·리스크: 특허(IP 정리) + 단계 성숙도 기반 중립치
    mat = {'Series C+': 3, 'Series C': 3, 'Series B': 3, 'Series A': 2, 'Pre-A': 2, 'Seed': 1}.get(startup.stage, 2)
    legal = min(mat + (1 if patents else 0), 4)
    sec_score = {
        '창업자·팀': s5(dim.get('team')),
        '문제·시장': s5(dim.get('market')),
        '제품·해자': moat,
        '트랙션': s5(dim.get('traction')),
        '사업모델·재무': s5(dim.get('financials')),
        '법무·리스크': legal,
        'VC 적합성': max(0, min(round(score / 20), 5)),
    }
    sec_metrics = build_section_metrics(startup)
    sections = [{'name': n, 'score': sec_score.get(n, 0),
                 'comment': '실데이터 기반 자동 평가(키 설정 시 GPT가 상세 분석).',
                 'metrics': sec_metrics.get(n, [])}
                for n in SECTION_NAMES]
    return {
        'fit_score': score,
        'recommendation': _band(score),
        'summary': summary,
        'sections': sections,
        'strengths': [],
        'concerns': ['정형 데이터가 제한적이라 일부 항목은 확인이 필요합니다.'],
        'hard_gates': [{'item': g, 'status': 'check'} for g in HARD_GATES],
        'source_note': 'OPENAI_API_KEY 설정 시 GPT가 7개 섹션을 정밀 평가합니다.',
    }


def _fallback_decks(vc, startup, pitch, ir, portfolio):
    have = [n for n, t in (('피치덱', pitch), ('IR덱', ir), ('VC 포트폴리오', portfolio)) if t]
    docs = ', '.join(have) if have else '업로드된 문서 없음'
    score = min(40 + 15 * len(have), 90)
    summary = (
        f'{startup.name} ↔ {vc.firm_name} 매칭 분석(신규 대상, 덱 기반). 분석 문서: {docs}.\n'
        f'OPENAI_API_KEY 미설정 상태라 템플릿 요약을 표시합니다. backend/.env 에 키를 넣으면 '
        f'GPT가 덱 내용을 읽고 FIT 점수와 7개 섹션 실사 리포트를 생성합니다.'
    )
    rj = _fallback_report_json(vc, startup, score, summary)
    return score, summary, 'fallback', rj


def _normalize_report(data, fit_score, locked_section_scores=None, startup=None):
    """
    LLM JSON 을 안전하게 정규화한다.

    locked_section_scores 가 있으면 섹션별 배점은 LLM 출력을 절대 사용하지 않는다.
    LLM 은 코멘트/강점/우려만 작성하고 점수는 결정론 엔진이 소유한다.
    """
    sections = []
    by_name = {}
    for s in (data.get('sections') or []):
        nm = (s.get('name') or '').strip()
        by_name[nm] = s
    sec_metrics = build_section_metrics(startup) if startup is not None else {}
    for nm in SECTION_NAMES:
        s = by_name.get(nm, {})
        if locked_section_scores is not None and nm in locked_section_scores:
            sc = locked_section_scores[nm]
        else:
            try:
                sc = max(0, min(int(round(float(s.get('score', 0)))), 5))
            except (TypeError, ValueError):
                sc = 0
        sections.append({'name': nm, 'score': sc,
                         'comment': (s.get('comment') or '정보 부족').strip(),
                         'metrics': sec_metrics.get(nm, [])})
    gates_in = {(g.get('item') or '').strip(): (g.get('status') or 'check')
                for g in (data.get('hard_gates') or [])}
    hard_gates = [{'item': g, 'status': gates_in.get(g, 'check')
                   if gates_in.get(g) in ('pass', 'check', 'risk') else 'check'}
                  for g in HARD_GATES]
    return {
        'fit_score': fit_score,
        'recommendation': _band(fit_score),
        'summary': (data.get('summary') or '').strip(),
        'sections': sections,
        'strengths': [str(x).strip() for x in (data.get('strengths') or []) if str(x).strip()][:4],
        'concerns': [str(x).strip() for x in (data.get('concerns') or []) if str(x).strip()][:4],
        'hard_gates': hard_gates,
    }


def _parse_json_block(text):
    """LLM 출력에서 JSON 추출(코드블록 제거 포함)."""
    t = text.strip()
    if t.startswith('```'):
        t = t.strip('`')
        t = t[t.find('{'):]
    start, end = t.find('{'), t.rfind('}')
    if start != -1 and end != -1:
        t = t[start:end + 1]
    return json.loads(t)


# ============================================================
#  엔트리포인트
# ============================================================
def _generate_base(vc, startup):
    """(fit_score, summary, source, report_json) — 기존 7섹션 리포트."""
    both_have_data = _startup_has_data(startup) and _vc_has_data(vc)

    if both_have_data:
        # 주 경로: 실데이터로 FIT 분석. 점수=결정론(재현성), 실사 리포트=LLM.
        score, sub, reasons = calculate_recommendation(vc, startup)
        ev = evaluate(vc, startup, score)
        facts = _structured_facts(vc, startup, score, sub, reasons, ev)
        pitch, ir, _ = collect_documents(vc, startup)
        if pitch or ir:
            facts += f'\n\n[참고: 스타트업 업로드 덱 발췌]\n{(pitch or ir)[:2000]}'
        facts += (f'\n\n[중요] FIT 적합도 점수는 {score}(결정론적 계산값)로 고정한다. '
                  f'fit_score 에 반드시 {score} 를 넣어라.')
        text, source = _llm_generate(INSTR_PRO, facts, json_mode=True)
        if text:
            try:
                data = _parse_json_block(text)
                # 총점뿐 아니라 7개 섹션 배점도 결정론 값으로 고정한다.
                baseline = _fallback_report_json(vc, startup, score, '', ev)
                locked_scores = {s['name']: s['score'] for s in baseline['sections']}
                rj = _normalize_report(data, score, locked_scores, startup=startup)
                summary = rj['summary'] or _fallback_structured(vc, startup, score, reasons, ev)
                rj['summary'] = summary
                return score, summary, source, rj
            except Exception:
                pass
        summary = _fallback_structured(vc, startup, score, reasons, ev)
        return score, summary, 'fallback', _fallback_report_json(vc, startup, score, summary, ev)

    # 신규 대상: 정형 데이터 부족 → 덱 기반 LLM 판단
    pitch, ir, portfolio = collect_documents(vc, startup)
    user = (
        f'[VC: {vc.firm_name}]\n선호 산업: {", ".join(vc.preferred_industries) or "없음"}\n'
        f'소개: {vc.bio or "없음"}\n포트폴리오:\n{portfolio or "(없음)"}\n\n'
        f'[스타트업: {startup.name}]\n피치덱:\n{pitch or "(없음)"}\n\nIR:\n{ir or "(없음)"}'
    )
    text, source = _llm_generate(INSTR_PRO, user, json_mode=True)
    if text:
        try:
            data = _parse_json_block(text)
            score = max(0, min(int(data.get('fit_score', 0)), 100))
            rj = _normalize_report(data, score, startup=startup)
            if rj['summary']:
                return score, rj['summary'], source, rj
        except Exception:
            pass
    return _fallback_decks(vc, startup, pitch, ir, portfolio)


# ============================================================
#  15섹션 IB급 투자 분석 리포트 (full_report)
# ============================================================
INSTR_FULL = (
    '너는 한국 최상위 VC 심사역이자 증권사 리서치 애널리스트다. 제공된 스타트업 정보, 재무, '
    '산업 데이터를 종합해 VC 투자심의위원회에 제출 가능한 수준의 투자 분석 리포트를 작성한다. '
    '단순 요약을 절대 하지 말고, 모든 분석은 투자자 관점에서 데이터 기반으로 수행하라. '
    '추정과 사실을 구분하고, 각 항목마다 근거와 투자의사결정 영향을 설명하라. '
    '제공된 정량값(재무·시장규모·FIT 점수)은 그대로 인용하고 임의로 바꾸지 마라. '
    '정보가 없으면 해당 필드에 "정보 부족"이라 쓰되 지어내지 마라.\n'
    '경쟁사(competitors)는 반드시 3개 이상 제시하고, Exit 시나리오는 IPO·M&A·전략적 인수 3종을 '
    '모두 점수화하라. 근거가 부족하면 추정임을 명시하되 항목 자체를 비우지 마라.\n\n'
    '반드시 아래 JSON 스키마만 출력하라(코드블록·설명 금지). 모든 점수는 정수.\n'
    '{'
    '"executive_summary":{"one_liner":"기업 한줄 정의","investment_points":["핵심 투자포인트 3개"],'
    '"key_risks":["주요 리스크 3개"],"opinion":"최종 투자의견 요약 2~3문장"},'
    '"market":{"trends":["시장 트렌드 2~3개"],"regulations":["규제 이슈 1~2개"],'
    '"drivers":["성장 동력 2~3개"],"comment":"시장 규모·성장성 평가 2~3문장"},'
    '"problem_solving":{"severity":<0~100>,"pain_point":<0~100>,"market_need":<0~100>,'
    '"solution_fit":<0~100>,"comment":"문제해결력 평가 근거"},'
    '"product":{"differentiation":"제품 차별성","barriers":["기술 진입장벽 항목"],'
    '"imitation_risk":"낮음|보통|높음","comment":"경쟁력 평가"},'
    '"competitors":[{"name":"경쟁사명","market_share":"점유율","tech":"기술력","funding":"투자유치",'
    '"differentiator":"차별점"}],'  # 반드시 3개 이상
    '"team":{"founder_fit":"창업자-시장 적합성","completeness":{"dev":<0~100>,"biz":<0~100>,'
    '"sales":<0~100>,"ops":<0~100>},"comment":"팀 평가"},'
    '"business_model":{"revenue_structure":"수익구조","acquisition":"고객확보 전략",'
    '"unit_economics":"CAC/LTV/Payback 추정 또는 정보부족","comment":"BM 평가"},'
    '"risks":[{"type":"사업|기술|시장|규제|경쟁","probability":"낮음|보통|높음",'
    '"impact":"낮음|보통|높음","desc":"리스크 설명"}],'  # 5종
    '"exit":{"scenarios":[{"type":"IPO","score":<0~100>,"desc":"근거"},{"type":"M&A","score":<0~100>,"desc":"근거"},{"type":"전략적 인수","score":<0~100>,"desc":"근거"}],'
    '"comment":"Exit 가능성 종합"},'
    '"vc_fit":{"seed":<0~100>,"series_a":<0~100>,"growth":<0~100>,'
    '"recommended":"추천 VC 유형"},'
    '"attractiveness":{"market":<0~100>,"product":<0~100>,"team":<0~100>,"growth":<0~100>,'
    '"profitability":<0~100>,"scalability":<0~100>,"exit":<0~100>},'
    '"analyst_comment":{"pros":["찬성 의견 2~3개"],"cons":["반대 의견 2~3개"],'
    '"due_diligence":["추가 실사 필요사항 2~3개"]},'
    '"final":{"target_valuation":"목표 기업가치 추정","recommended_amount":"권장 투자금액",'
    '"conclusion":"최종 결론 한 문단"}'
    '}'
)

RATING_BANDS = [(80, 'Strong Buy'), (65, 'Buy'), (50, 'Neutral'), (35, 'Caution'), (0, 'Reject')]


def _rating(score):
    for cut, label in RATING_BANDS:
        if score >= cut:
            return label
    return 'Reject'


def _market_sizing(startup):
    """TAM/SAM/SOM 결정론 추정. market_size(억원)를 TAM으로 보고 단계적 축소."""
    tam = startup.market_size or 0
    if not tam:
        return None
    sam = round(tam * 0.30)        # 타깃 세그먼트 추정 30%
    som = round(sam * 0.10)        # 초기 침투 가능 10%
    return {
        'tam': {'value': tam, 'display': f'{tam:,}억원', 'basis': '산업 전체 시장(추정)'},
        'sam': {'value': sam, 'display': f'{sam:,}억원', 'basis': 'TAM의 30% — 타깃 세그먼트(추정)'},
        'som': {'value': som, 'display': f'{som:,}억원', 'basis': 'SAM의 10% — 초기 침투 가능(추정)'},
        'cagr': startup.market_growth or None,
    }


def _financial_block(startup):
    """9. 재무 분석 — DART/제공 데이터 결정론."""
    fin = _fin(startup)
    debt_ratio = None
    capital_impair = None
    if fin and fin['latest'].get('liabilities') and fin['latest'].get('assets'):
        eq = fin['latest']['assets'] - fin['latest']['liabilities']
        debt_ratio = round(fin['latest']['liabilities'] / eq * 100) if eq else None
        capital_impair = eq < 0
    latest = fin['latest'] if fin else {}
    return {
        'revenue': startup.revenue or (latest.get('revenue')),
        'operating_income': latest.get('operating_profit'),
        'net_income': latest.get('net_income'),
        'burn_rate': startup.burn_rate or None,
        'runway_months': startup.runway_months or None,
        'debt_ratio': debt_ratio,
        'capital_impairment': capital_impair,
        'source': (startup.financials or {}).get('source') if startup.financials else None,
    }


def _company_overview(startup):
    return {
        'name': startup.name, 'founded': startup.founded_year,
        'industry': startup.industry, 'stage': startup.stage,
        'business_model': startup.differentiation or startup.description or '정보 부족',
    }


def _fallback_full_report(vc, startup, score):
    """LLM 없이도 보여줄 15섹션 골격(정량은 채우고 정성은 안내)."""
    NA = '정보 부족 — OPENAI_API_KEY 설정 시 GPT가 분석합니다.'
    return {
        'rating': _rating(score),
        'fit_score': score,
        'executive_summary': {'one_liner': startup.summary or NA,
                              'investment_points': [], 'key_risks': [], 'opinion': NA},
        'company_overview': _company_overview(startup),
        'market': {'sizing': _market_sizing(startup), 'trends': [], 'regulations': [],
                   'drivers': [], 'comment': NA},
        'problem_solving': {'scores': {}, 'total': None, 'comment': NA},
        'product': {'differentiation': startup.differentiation or NA, 'barriers': [],
                    'imitation_risk': '정보 부족', 'comment': NA},
        'competitors': [],
        'team': {'founder_fit': NA, 'completeness': {}, 'comment': NA},
        'business_model': {'revenue_structure': NA, 'acquisition': NA,
                           'unit_economics': NA, 'comment': NA},
        'financials': _financial_block(startup),
        'attractiveness': {'scores': {}, 'total': None},
        'risks': [],
        'exit': {'scenarios': [], 'comment': NA},
        'vc_fit': {},
        'analyst_comment': {'pros': [], 'cons': [], 'due_diligence': []},
        'final': {'target_valuation': NA, 'recommended_amount': NA, 'conclusion': NA},
        'source': 'fallback',
    }


def _build_full_report(vc, startup, score):
    """15섹션 IB 리포트. 정량은 결정론 주입, 정성은 LLM. 키 없으면 골격."""
    sizing = _market_sizing(startup)
    financials = _financial_block(startup)

    # LLM 컨텍스트: 정량 데이터를 풍부하게 제공
    facts = [f'[기업] {startup.name} · {startup.industry} · {startup.stage} · 설립 {startup.founded_year}']
    facts.append(f'[VC] {vc.firm_name} — 선호: {", ".join(vc.preferred_industries) or "-"} / '
                 f'{", ".join(vc.preferred_stages) or "-"}')
    facts.append(f'[FIT] 결정론 적합도 {score}/100 → 등급 {_rating(score)}')
    if sizing:
        facts.append(f'[시장] TAM {sizing["tam"]["display"]} / SAM {sizing["sam"]["display"]} / '
                     f'SOM {sizing["som"]["display"]} / CAGR {sizing.get("cagr")}%')
    if financials.get('revenue'):
        facts.append(f'[재무] 매출 {financials["revenue"]:,}만원 · '
                     f'영업이익 {financials.get("operating_income")} · '
                     f'Runway {financials.get("runway_months")}개월')
    if startup.differentiation:
        facts.append(f'[차별점] {startup.differentiation}')
    if startup.signals:
        facts.append(f'[신호] {startup.signals}')
    if startup.description:
        facts.append(f'[소개] {startup.description}')

    text, source = _llm_generate(INSTR_FULL, '\n'.join(facts), json_mode=True,
                                 max_tokens=6000, timeout=90)
    if not text:
        return _fallback_full_report(vc, startup, score)
    try:
        data = _parse_json_block(text)
    except Exception:
        return _fallback_full_report(vc, startup, score)

    # 정량 결정론 값 주입(LLM 출력 위에 덮어쓰기 — 숫자 신뢰성 확보)
    data['rating'] = _rating(score)
    data['fit_score'] = score
    data['company_overview'] = _company_overview(startup)
    data.setdefault('market', {})['sizing'] = sizing
    data['financials'] = financials
    # problem_solving / attractiveness 총점 자동 계산
    ps = data.get('problem_solving', {})
    pvals = [ps.get(k) for k in ('severity', 'pain_point', 'market_need', 'solution_fit')
             if isinstance(ps.get(k), (int, float))]
    if pvals:
        ps['scores'] = {k: ps.get(k) for k in ('severity', 'pain_point', 'market_need', 'solution_fit')}
        ps['total'] = round(sum(pvals) / len(pvals))
        data['problem_solving'] = ps
    att = data.get('attractiveness', {})
    avals = [v for v in att.values() if isinstance(v, (int, float))]
    if avals:
        data['attractiveness'] = {'scores': att, 'total': round(sum(avals) / len(avals))}
    data['source'] = source
    return data


# ============================================================
#  엔트리포인트 (wrapper): 기존 7섹션 + 15섹션 full_report
# ============================================================
def generate_ai_report(vc, startup):
    """(fit_score, summary, source, report_json) 반환. report_json['full_report']에 15섹션 IB 리포트."""
    score, summary, source, rj = _generate_base(vc, startup)
    try:
        rj['full_report'] = _build_full_report(vc, startup, score)
    except Exception:
        rj['full_report'] = _fallback_full_report(vc, startup, score)
    return score, summary, source, rj
