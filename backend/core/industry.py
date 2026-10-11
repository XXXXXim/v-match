# -*- coding: utf-8 -*-
"""산업군(Industry Group) 분류 체계.

스타트업의 industry(한글 복합 텍스트: 예 "소프트웨어·리테일테크·AI 컴퓨터 에이전트")와
VC의 preferred_industries(영문 태그: 예 "AI/ML", "Bio/Healthcare")를
하나의 '산업군' 키로 통일해, 공통분모끼리 묶어준다.

- classify_startup(industry, *extra)  -> group_key  (스타트업 1개를 산업군으로 분류)
- vc_groups(preferred_industries)     -> set[group_key]  (VC 관심 태그를 산업군 집합으로)
- GROUP_LABEL[key]                    -> 한글 라벨
"""

# (key, 한글 라벨, [스타트업 industry 한글 키워드], [VC 영문 태그])
# 주의: 아래 '순서'가 곧 우선순위. 도메인 특화 그룹을 AI/SW 같은 범용 그룹보다 앞에 둬서
#       "자율주행(AI 기술)" 같은 복합 산업이 도메인(모빌리티)으로 묶이도록 한다.
_GROUPS = [
    ('bio', '바이오·헬스케어',
     ['바이오', '의료', '의약', '헬스케어', '헬스', '진단', '치료', '수술', '봉합',
      '생체신호', '바이오마커', '융합바이오', '수면', '인지기능', '인지측정', '치매',
      '제약', '임상', '약학', '엑소좀'],
     ['Bio/Healthcare', 'Healthcare', 'Medical', 'SilverTech']),

    ('energy', '에너지·환경',
     ['에너지', '환경', '신재생', '대기오염', '폐기물', '재활용', '탄소', 'ESS',
      '조명에너지', '2차전지', '배터리', '해양오염', 'VOCs'],
     ['Energy', 'ClimateTech', 'Eco/Energy', 'Secondary Battery']),

    ('mobility', '모빌리티·물류',
     ['드론', '자율비행', '자율주행', '모빌리티', '항공', '해양', '항만', '선박',
      '콜드체인', '물류', '운송', '화물', 'MRV'],
     ['Future Mobility', 'Aerospace', 'Mobility']),

    ('robot_mfg', '로봇·제조',
     ['로봇', '자동화기계', '자동화', '정밀생산', '생산기계', '요소부품', '제동', '완충'],
     ['Robotics']),

    ('materials', '소재·화학·반도체',
     ['화학', '나노소재', '고분자', '화장품', '바이오소재', '텍스타일',
      '정밀화학', '반도체', '디스플레이', '소재'],
     ['Materials/Components', 'Advanced Materials', 'Semiconductor', 'Display']),

    ('fintech', '핀테크·B2B SaaS',
     ['핀테크', '세무', '무역', '수출', '리스크', 'SaaS', '리테일', '부동산',
      '결제', '기업물류', '물류지원', '커머스'],
     ['FinTech', 'SaaS', 'Commerce', 'Platform', 'Service']),

    ('consumer', '콘텐츠·소비자',
     ['콘텐츠', '게임', '교육', '에듀', 'AR ', 'VR ', '스마트토이', '인플루언서',
      '마케팅', '외국인', '육아', '푸드테크', '식품', '주방', '돌봄', '스포츠'],
     ['Content', 'Gaming', 'Metaverse', 'VR/AR', 'Mobile', 'FoodTech', 'AgriFood',
      'Agriculture', 'Fisheries']),

    ('ai_data', 'AI·데이터',
     ['생성형', '멀티모달', 'Voice AI', '음성인식', 'STT', 'TTS', 'AI Agent', '에이전트',
      '챗봇', '데이터 플랫폼', '데이터웨어', '실시간 데이터', 'AI SDR', '재능 진단',
      '판독시스템', '인공지능', '컴퓨터 에이전트'],
     ['AI/ML', 'Big Data', 'Data', 'Data Platform', 'Digital Transformation']),
]

_OTHER = ('deeptech', '딥테크·기타',
          ['양자', 'quantum', 'ePROM', 'AIoT'],
          ['DeepTech', 'Other', 'Tech', 'ICT', 'Network', 'Quantum'])

# '전 산업'을 뜻하는 VC 태그(모든 산업군에 관심으로 처리)
_ALL_TAGS = {'All', '전체', '전 산업', '무관'}

GROUP_ORDER = [g[0] for g in _GROUPS] + [_OTHER[0]]
GROUP_LABEL = {g[0]: g[1] for g in _GROUPS}
GROUP_LABEL[_OTHER[0]] = _OTHER[1]


def classify_startup(industry, description='', *extra):
    """스타트업 1개를 산업군 key 로 분류.
    industry(짧고 핵심적)는 2배 가중, description(보조 신호)은 1배 가중해 점수가 가장 높은 그룹 선택."""
    ind = (str(industry or '')).lower()
    desc = ' '.join(str(x) for x in ([description] + list(extra)) if x).lower()
    best_key, best_score = None, 0
    for key, _label, kws, _tags in _GROUPS:
        score = 0
        for kw in kws:
            k = kw.lower()
            if k in ind:
                score += 2
            elif k in desc:
                score += 1
        if score > best_score:
            best_key, best_score = key, score
    if best_key:
        return best_key
    if any(kw.lower() in (ind + ' ' + desc) for kw in _OTHER[2]):
        return _OTHER[0]
    return _OTHER[0]


def vc_groups(preferred_industries):
    """VC 의 preferred_industries(영문 태그 리스트) → 관심 산업군 key 집합."""
    tags = preferred_industries or []
    tagset = {str(t).strip() for t in tags}
    if tagset & _ALL_TAGS:
        return set(GROUP_ORDER)              # '전 산업' → 모든 산업군
    groups = set()
    for key, _label, _kws, vtags in _GROUPS:
        if tagset & set(vtags):
            groups.add(key)
    if tagset & set(_OTHER[3]):
        groups.add(_OTHER[0])
    return groups


def group_label(key):
    return GROUP_LABEL.get(key, '기타')
