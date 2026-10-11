# V-Match 개발 변경 이력

> 7일 스프린트 동안의 버전별 변경 기록입니다. 최신 실행 방법은 [README](../README.md)를 참고하세요.

## v1 — 로그인/로그아웃 이슈 수정
- 증상: 회원가입 → 로그인 → 로그아웃 → **재로그인 시 401**("토큰이 유효하지 않습니다").
- 원인: 로그아웃 후 헤더에 남은 옛 토큰 때문에, DRF가 `AllowAny`를 적용하기 전에 토큰 인증에서
  먼저 401을 냈다.
- 조치: 로그인·회원가입 뷰에 `@authentication_classes([])`를 적용해 토큰 인증을 타지 않도록 함.
  프론트 로그아웃은 백엔드 `/accounts/logout/`를 호출해 서버 토큰을 실제로 삭제(세션 종료)하도록 보완.

## v2 — ERD 정규화 (관통 프로젝트 반영)

명세에 맞춰 데이터 모델을 정규화했습니다. 상세 설계는 [`docs/ERD.md`](ERD.md) 참고.

추가/변경된 엔티티: `VCPreference`(VCProfile 1:1), `PitchDeck`/`IRDeck`(StartupProfile 1:N),
`PortfolioDocument`(VCProfile 1:N), `Recommendation`(점수 영속화·비노출),
`AIReport`(Match 1:1, 결정론적 fit_score + LLM summary). `Like`/`Match` 는 `UniqueConstraint`
로 중복 방지.

### 실행 방법
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_vcs          # 데모 VC 10건
python manage.py seed_startups     # 데모 스타트업 40건
python manage.py runserver
#  (선택) export ANTHROPIC_API_KEY=...  → AI 요약 LLM 사용. 미설정 시 템플릿 폴백.

# Frontend
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

### 추가 API
- `GET/POST /api/vc-profile/portfolio/` — VC 포트폴리오 자료(1:N)
- `GET /api/matches/<id>/ai-report/` — 매칭 AI 리포트(FIT 점수+요약)

---

## v3 변경 — PDF 등록 + GPT AI 리포트 (핵심)

프로필 등록 방식을 **PDF 업로드 전용**으로 전환했습니다(구조화 입력 폼 제거).

- 홈: 로그인 후 **"프로필 등록하기"** 버튼 1개만 노출.
- 스타트업: **피치덱 + IR덱 PDF** 업로드 → 등록 완료(폼 없음).
- VC: **포트폴리오 PDF** 업로드 → 등록 완료(폼 없음).
- 추천 리스트: **점수 비노출**(카드 + 좋아요만). 점수는 내부 정렬용으로만 사용.
- **AI 분석 리포트(핵심)**: 매칭 성사 후 GPT가 업로드된 PDF를 분석해 `fit_score`+`summary` 생성.

### ⚙️ GPT API 키 설정 (필수 — 핵심 기능)
`backend/.env` 파일에 OpenAI 키를 넣으세요. (없으면 템플릿 폴백으로 동작)
```
OPENAI_API_KEY=sk-...        # 여기에 키
OPENAI_MODEL=gpt-4o-mini
```
리포트 생성 로직: `backend/core/ai_report.py` (PDF 텍스트 추출 → GPT 분석 → JSON 점수/요약).

### 추가/변경 API
- `GET /api/profile-status/` — 프로필 등록 완료 여부(PDF 등록 현황)
- `POST /api/startup-profile/pitch-deck/`, `/ir-deck/` — PDF 업로드(없으면 프로필 자동 생성)
- `POST /api/vc-profile/portfolio/` — 포트폴리오 PDF 업로드(없으면 프로필 자동 생성)
- `GET /api/matches/<id>/ai-report/` — GPT AI 리포트(FIT 점수 + 요약)

> 참고: PDF만으로 등록하므로 룰 기반 점수 엔진은 구조화 데이터가 없어 동작하지 않습니다.
> FIT 점수는 GPT가 PDF를 읽고 산출합니다(시드 데이터는 PDF가 없어 폴백 처리).

---

## v4 정정 — AI 리포트는 '실데이터 기반' (덱은 신규 가입자용)

- **AI 분석 리포트의 본질**: DB에 모델링된 실제 스타트업·VC 데이터(산업/단계/지역/투자금/
  팀·트랙션·시장·재무 + VC 선호조건)를 근거로 두 곳의 FIT 을 분석한다.
  - 실데이터가 있는 경우(시드/기존): `fit_score` 는 실데이터 기반 결정론 점수(재현성),
    `summary` 는 GPT 가 그 데이터를 근거로 작성.
  - 신규 가입자처럼 DB에 정형 데이터가 없는 경우: 업로드한 덱(PDF)을 GPT 가 읽고 판단.
  - 분기 로직: `backend/core/ai_report.py` (구조화 우선 → 없으면 덱).
- **VC 추천 리스트에 VC 링크 표시**: `VCProfile.website` 추가, 추천 카드에 홈페이지 링크 노출.

---

## v5 — AI 리포트 LLM 호출을 SSAFY GMS 게이트웨이로 연결

AI 분석 리포트는 SSAFY GMS 게이트웨이를 통해 OpenAI Responses API 를 호출합니다.
동작은 아래 curl 과 동일합니다.
```bash
curl "https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GMS_KEY" \
  -d '{"model": "gpt-5.4-pro", "input": "..."}'
```

### API 키 넣는 곳 (= API 키 루트)
`backend/.env` 의 **`GMS_KEY`** 에 발급받은 키를 넣으세요.
```
GMS_KEY=발급받은키
GMS_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1
GMS_MODEL=gpt-5.4-pro
```
- 키가 있으면: 매칭 성사 시 리포트의 `summary` 를 GMS(LLM)가 생성. (구조화 데이터 쌍은
  `fit_score` 는 결정론 점수를 유지, 신규 가입자/덱 기반은 LLM이 점수도 산출)
- 키가 없으면: 템플릿 폴백으로 동작(데모 안 깨짐).
- 호출 코드: `backend/core/ai_report.py` (`_llm_generate` → `{GMS_BASE_URL}/responses`).
- 별도 SDK 불필요(표준 라이브러리 urllib 사용). `openai` 패키지는 의존성에서 제거됨.

---

## v6 — 좋아요 응답 즉시화 + 실제 VC 데이터 11곳

- **버그 수정**: 매칭이 성사되는 좋아요(주로 스타트업→VC, 두 번째 좋아요)에서 AI 리포트를
  동기 생성하느라 응답이 지연/멈추던 문제 수정. 좋아요·매칭은 즉시 처리하고, **AI 리포트는
  매칭 상세를 열 때 생성**(지연 생성). GMS 키가 설정돼 있어도 좋아요가 막히지 않는다.
- **실제 VC 11곳**: `backend/core/data/vc_data.json` → `python manage.py seed_real_vcs`
  로 적재(`link`→website, 선호조건→VCPreference 매핑). `--reset` 으로 미연결 VC 초기화 후 재적재 가능.
- **와일드카드**: 선호 산업 `All`(전 산업), 선호 지역 `전국`(전 지역)을 매칭 엔진이 만점 처리.
  VC 선호 지역 선택지에 `전국` 추가.

실데이터 시드 순서: `python manage.py seed_real_vcs && python manage.py seed_startups`

---

## v7 — AI 리포트 LLM을 표준 OpenAI(Chat Completions)로

`backend/.env` 의 **`OPENAI_API_KEY`** 에 키를 넣으면 표준 OpenAI API
(`https://api.openai.com/v1/chat/completions`)로 AI 리포트를 생성합니다.
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```
우선순위: `OPENAI_API_KEY` 있으면 OpenAI 사용 → 없고 `GMS_KEY` 있으면 GMS → 둘 다 없으면 폴백.
호출 코드: `backend/core/ai_report.py` (`_llm_generate`, kind='chat').

---

## v8 — 실데이터(VC 48 / 스타트업 JSON) + 한글 산업 노출

- **실제 VC 48곳**: `core/data/vc_data.json` → `python manage.py seed_real_vcs`
- **실제 스타트업**: `core/data/startup_data.json` 에 채워 넣고 → `python manage.py seed_real_startups`
  (loaddata 형식: model/pk/fields. '여기에 …' 같은 템플릿/빈 이름 행은 자동 스킵)
- **한글/비표준 산업 노출**: 산업이 영문 표준 목록(SaaS·Fintech…)에 없거나 비어 있어도
  VC '스타트업 찾기' 결과에 항상 노출되도록 수정(예: '프롭테크', '전국').
  → 'All' 산업·'전국' 지역 VC와는 와일드카드로 매칭됨.

실데이터 시드: `python manage.py seed_real_vcs && python manage.py seed_real_startups`

---

## v9 — 회원 플로우/UI 정비 + 이메일 인증

**공통**
- 회원가입 시 **이메일 필수 + 이메일 인증**(6자리 코드). 기본은 콘솔 백엔드(runserver 콘솔에 코드 출력),
  DEBUG 모드에선 인증 화면에 코드 표시. `.env` 에 EMAIL_HOST_USER/PASSWORD 넣으면 실제 SMTP 발송.
  미인증 사용자는 라우터 가드로 인증 화면으로 유도.
- 상단바 **'분석' 제거**. 홈은 프로필 등록 완료 시 '프로필 등록하기' 대신 메인 목록 버튼 표시.

**스타트업**
- VC 추천 리스트: **'AI 추천 이유' 제거**, '매칭 상세 분석' → **'자세한 정보 확인하기'(VC 상세 페이지)**.
  VC 카드 클릭 시에도 상세 페이지로 이동.
- **알림 클릭 이동**: 좋아요 알림 → VC 상세, 매칭/커피챗 알림 → 매칭 페이지.
- 마이페이지 **'관심 스타트업'은 VC 전용**(스타트업에선 숨김).

**VC**
- 프로필 등록 안내문구·버튼 문구 정리('저장', '프로필 자료 등록').
- 선호조건: **투자 단계·투자범위(억) 제거**, **희망 투자금 범위(원)** + **선호 창업자 학력** 추가.
- '스타트업 찾기' → 선호도 조사 페이지 없이 **저장된 선호조건으로 바로 결과**.

---

## v10 — AI 리포트를 전문 VC 실사 리포트 형식으로

VC 투자실사 템플릿(섹션 배점·하드게이트·권고 밴드)의 핵심을 추려 AI 리포트를 고도화.
- **7개 섹션 0~5점 평가**: 창업자·팀 / 문제·시장 / 제품·해자 / 트랙션 / 사업모델·재무 / 법무·리스크 / VC 적합성
- **강점·우려·하드게이트(딜킬러) 점검**: 정직성·IP·개인정보·캡테이블·고객집중도·단위경제 (pass/check/risk)
- **권고 밴드**: 85+ 적극 / 75+ 조건부 / 65+ 관찰 / 그 외 신중 (FIT 점수 기준)
- 헤드라인 **FIT 점수는 그대로 결정론(재현성)**, 섹션·서술은 GPT가 생성. 키 없으면 결정론 골격 폴백.
- 저장: `AIReport.report_json`. 화면: 매칭 상세에 섹션 막대·강점/우려·하드게이트 렌더.

---

## v11 — 라이브 매칭 데모 계정 (seed_demo)

실제 카탈로그의 VC 1곳 + 스타트업 1곳에 로그인 계정을 부여(이메일 인증 완료). 좋아요는 깔지
않아 발표 때 두 계정이 직접 서로 좋아요를 눌러 '진짜 쌍방 매칭'을 시연한다.

```bash
python manage.py seed_real_vcs && python manage.py seed_real_startups
python manage.py seed_demo            # 기본: VC=매쉬업벤처스, 스타트업=리빌더AI
# python manage.py seed_demo --vc "VC명" --startup "스타트업명" --password pw --reset
```
기본 계정: demo_vc / demo_startup (비밀번호 demo1234).
라이브 흐름: A브라우저(demo_startup)에서 VC 좋아요 → B브라우저(demo_vc)에서 알림 확인 →
스타트업 좋아요 → 매칭 → AI 실사 리포트. (대량 좋아요 시드 없음 → 매칭의 쌍방성 보존)

---

## v12 — FIT 점수 재설계(실데이터 반영) + AI 리포트 정밀화

문제: 우량 스타트업(키즈노트: 매출 165억·특허 236건·시장 1위)이 17점으로 나옴 — 점수가
빈 숫자 필드(MAU 등)만 보고 실데이터(매출·후속투자·특허·해외)를 안 썼기 때문.

- **FIT = 투자조건 적합(40) + 스타트업 역량(60)**. 역량은 매출·후속투자·특허·해외진출·고객·
  단계 등 실데이터로 산정. (recommend.py 전면 개정)
- **산업 분류 브릿지**: 한글 세분류/설명에서 키워드로 표준 카테고리 추론 → VC 선호와 매칭.
- **실데이터 신호 추출**: seed_real_startups 가 특허·후속투자·해외·고객을 StartupProfile.signals 에 적재.
- **AI 리포트에 실데이터 공급**: facts 에 매출·특허·후속투자·고객·성과 포함, 0인 소비자 지표는 비강조.
  B2B/딥테크는 매출·고객사·특허로 평가하도록 지침 보강.
- **seed_demo 자동 VC 선택**: 스타트업에 FIT 최고인 VC를 자동 매칭(예: 키즈노트→FIT 90).

결과: 키즈노트 17 → 90점(적극 투자 검토), 7개 섹션 모두 합리적 점수.
적용: `python manage.py migrate` (signals 필드 추가) 후 seed 재실행.

---

## v13 — 실데이터 교체 (VC 104 + 스타트업 25, 더미 제거)

- VC: 업로드 vc_data.json(106) → JSON 문법 오류 1건(빅뱅엔젤스 배열 미닫힘) 복구 +
  단계 표기 'Series-A'→'Series A' 통일 + 완전 중복 2건 제거 → **고유 104개**.
- 스타트업: 업로드 25개로 교체. **내장 더미(리빌더AI 등 6곳) 전면 제거** — seed_real_startups 는
  이제 startup_data.json 만 적재.
- recommend.py: 'Series C' 단계 인식, 지역 매칭을 부분일치(서울↔서울 강남구) + '기타' 와일드카드로 보강.
- seed_demo 기본 스타트업 = 키즈노트, 최적 VC 자동선택(젠엑시스, FIT 95).
적용: migrate → seed_real_vcs → seed_real_startups → seed_demo --reset

---

## v14 — 랜딩 페이지 + 카드 요약 + 금액 단위 정리 + FIT에서 투자금액 제외

1. **추천 카드 간결화**: 긴 설명 대신 핵심 요약(summary) 표시. 규칙기반 요약 자동 생성 +
   `python manage.py summarize_startups`(키 있으면 GPT 투자자 관점 2~3문장).
2. **프로필 상세에서 '피치덱 보기' 제거**.
3. **AI FIT 기준에서 투자금액(check) 제외** — VC별 투자범위 유무가 제각각이고 fit 판단 기준이
   아니라서. 가중치 재배분(산업 20·단계 12·지역 8 = 40, 역량 60).
4. **첫 진입 랜딩 페이지 추가**: 서비스 소개 hero + '시작하기' → '처음/회원' 선택 화면.
5. **금액 단위 정규화**: 입력이 원(800000000=8억) 또는 억(8) 어느 쪽이든 자동 판별해 만원으로
   저장, 화면은 억 단위로 통일 표시.

---

## v15 — 실데이터 교체 v2 (VC 20 + 스타트업 20, 초기 딥테크) + 단계 정규화 + 역량 재조정

- 데이터: 기존 VC 104·스타트업 25 폐기 → 신규 VC 20 + 스타트업 20(TIPS 초기 딥테크, 매출 0·특허 보유).
- **단계 정규화**: 자유 텍스트('엔젤투자·시제품 제작', '시리즈 A·시장출시')를 표준 코드로 변환.
  STAGE_ORDER 에 Pre-Seed/Growth 추가.
- **VC bio 보강**: investment_thesis(target·focus_sectors)를 bio 에 결합해 AI 리포트 맥락 강화.
- **역량 가중치 재조정**: 초기·딥테크 공정 평가 — IP 16·트랙션 18·팀 8·매출 8·후속 4·성숙 6(=60).
  매출 없는 초기 기업도 특허·고객·해외·제품으로 정당하게 평가.
- 결과: 탑테이블 FIT 76(조건부 투자 검토) 등 현실적 변별. seed_demo 기본=탑테이블.
