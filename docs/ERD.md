# V-Match ERD 설계 문서 (v2)

스타트업 ↔ VC 매칭 플랫폼의 데이터 모델. Django ORM 기준으로 설계했으며
`OneToOneField / ForeignKey / ManyToManyField(through)` 와
`UniqueConstraint / unique_together` 로 무결성을 보장한다.

핵심 설계 원칙
- **적합도 점수는 결정론적이다.** 룰 기반(`recommend.py`) + 단계·역량 가중(`evaluate.py`)
  으로 `fit_score` 를 계산하고, **LLM 은 자연어 요약(summary)만** 생성한다. 같은 입력이면
  항상 같은 점수가 나와야 VC가 신뢰할 수 있기 때문이다(`AIReport.fit_score` 는 LLM 산출물이 아님).
- **점수는 매칭 전까지 숨긴다.** 추천 리스트는 카드 + 좋아요만 노출하고,
  `Recommendation.score` 는 내부 점수로 저장만 한다. **FIT 점수는 매칭 성사 후
  `AIReport` 를 통해 최초로 공개**된다.

---

## 1. 엔티티 상세 (PK / FK / 속성 / 제약)

### User  (`accounts.User`, `AbstractUser` 확장)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| username | Char | unique | 아이디 |
| password | Char | NOT NULL | 비밀번호(해시) |
| email | Email | | 이메일 |
| role | Char(10) | choices(`vc`/`startup`) | 사용자 유형 |
| phone | Char(30) | blank | 연락처 |
| date_joined | DateTime | auto | 가입일 |

관계: `StartupProfile` 1:1, `VCProfile` 1:1.

### VCProfile
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| user_id | OneToOne→User | **FK**, null 허용 | 시드 VC는 계정 없이 생성 가능 |
| firm_name | Char(100) | | 투자사명 |
| bio | Text | blank | 소개 |
| vc_summary | Text | blank | 투자철학 AI 요약 |
| eval_emphasis | JSON | default `[]` | 중시 평가차원(team/traction/…) |
| created_at / updated_at | DateTime | auto | |

관계: `User` 1:1 · `VCPreference` 1:1 · `PortfolioDocument` 1:N.
선호조건(preferred_*, min/max_investment)은 **VCPreference 로 분리**하고,
`VCProfile` 에는 읽기 호환용 프록시 프로퍼티로 노출한다.

### VCPreference  (VCProfile 1:1)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| vc_id | OneToOne→VCProfile | **FK**, unique | |
| preferred_industries | JSON | default `[]` | 선호 산업 |
| preferred_stages | JSON | default `[]` | 선호 투자단계 |
| preferred_regions | JSON | default `[]` | 선호 지역 |
| min_investment | BigInt | 만원 단위 | 투자 규모 하한 |
| max_investment | BigInt | 만원 단위 | 투자 규모 상한 |

### StartupProfile
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| user_id | OneToOne→User | **FK**, null 허용 | |
| name / industry / stage / region | Char | | 기본 정보 |
| funding_needed | BigInt | 만원 단위 | 희망 투자금 |
| team_size, revenue, founded_year, … | Int/Big | | 평가용 정량 지표 |
| pitch_deck / ir_deck | File | null | **최신(대표) 덱 포인터**(1:N 비정규화 캐시) |
| ir_summary / ir_summary_status / ir_summary_public | Text/Char/Bool | | IR 요약·검수·공개 |

관계: `User` 1:1 · `PitchDeck` 1:N · `IRDeck` 1:N.

### PitchDeck  (StartupProfile 1:N)
| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BigAuto | **PK** |
| startup_id | FK→StartupProfile | **FK** |
| file | File(`pitch_decks/`) | NOT NULL |
| uploaded_at | DateTime | auto |

### IRDeck  (StartupProfile 1:N)
| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BigAuto | **PK** |
| startup_id | FK→StartupProfile | **FK** |
| file | File(`ir_decks/`) | NOT NULL |
| uploaded_at | DateTime | auto |

### PortfolioDocument  (VCProfile 1:N)
| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BigAuto | **PK** |
| vc_id | FK→VCProfile | **FK** |
| file | File(`portfolios/`) | NOT NULL |
| title | Char(120) | blank |
| uploaded_at | DateTime | auto |

### Recommendation  (StartupProfile × VCProfile)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| vc_id | FK→VCProfile | **FK** | |
| startup_id | FK→StartupProfile | **FK** | |
| score | Int | | **내부 점수(화면 비노출)** |
| created_at / updated_at | DateTime | auto | 추천일자 |
| | | **UniqueConstraint(vc, startup)** | 쌍당 1행 |

### Like  (스타트업↔VC 좋아요, 중간 모델)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| vc_id | FK→VCProfile | **FK** | |
| startup_id | FK→StartupProfile | **FK** | |
| by | Char(10) | choices(`vc`/`startup`) | 좋아요 방향 |
| created_at | DateTime | auto | |
| | | **UniqueConstraint(vc, startup, by)** | 중복 좋아요 방지 |

> 명세의 `from_startup/from_vc/to_startup/to_vc` 는 **2개 FK + 방향 플래그(by)** 로
> 정규화하여 표현한다(항상 null 인 FK 2개를 두지 않는 정석 형태). 모델에 `from_vc /
> from_startup / to_vc / to_startup` **파생 프로퍼티**를 제공해 동일한 의미로 접근 가능하다.
> 양쪽 `by`(vc·startup)가 모두 존재하면 매칭 성사.

### Match  (상호 좋아요 성사)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| vc_id | FK→VCProfile | **FK** | |
| startup_id | FK→StartupProfile | **FK** | |
| status | Char(12) | choices | matched/requested/accepted/declined |
| matched_at | DateTime | default now | 매칭 성사 시각 |
| (Post-Match 확장) | | | NDA 동의시각·미팅 브리핑·심층분석 캐시 |
| | | **UniqueConstraint(vc, startup)** | 쌍당 1매칭 |

### AIReport  (Match 1:1)
| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | BigAuto | **PK** | |
| match_id | OneToOne→Match | **FK**, unique | |
| fit_score | Int | | **결정론적 FIT 점수(0~100)** |
| summary | Text | | LLM 자연어 분석 |
| source | Char(20) | `llm`/`fallback` | 생성 출처 |
| created_at | DateTime | auto | |

> 보조 엔티티(확장): `Bookmark`(찜), `MatchResult`(추천 리스트 인라인 AI설명 캐시),
> `Notification`(인앱 알림). 명세 필수 엔티티는 아니며 UX 보강용이다.

---

## 2. 관계 요약

| 관계 | 종류 | 구현 |
|---|---|---|
| User ↔ StartupProfile | 1:1 | OneToOneField |
| User ↔ VCProfile | 1:1 | OneToOneField |
| VCProfile ↔ VCPreference | 1:1 | OneToOneField |
| VCProfile ↔ PortfolioDocument | 1:N | ForeignKey |
| StartupProfile ↔ PitchDeck | 1:N | ForeignKey |
| StartupProfile ↔ IRDeck | 1:N | ForeignKey |
| StartupProfile ↔ VCProfile (추천) | N:M | through=`Recommendation` |
| StartupProfile ↔ VCProfile (좋아요) | N:M | through=`Like` |
| StartupProfile ↔ VCProfile (매칭) | N:M | through=`Match` |
| Match ↔ AIReport | 1:1 | OneToOneField |

---

## 3. ASCII ERD

```
                         ┌──────────────────┐
                         │       User       │
                         │ id(PK) username  │
                         │ email role phone │
                         └───┬──────────┬───┘
                       1:1   │          │  1:1
              ┌──────────────┘          └──────────────┐
              ▼                                         ▼
   ┌────────────────────┐                    ┌────────────────────┐
   │   StartupProfile   │                    │      VCProfile      │
   │ id(PK) user_id(FK) │                    │ id(PK) user_id(FK)  │
   │ name industry …    │                    │ firm_name bio …     │
   └──┬───────┬──────┬──┘                    └──┬────────┬─────┬───┘
  1:N │   1:N │      │                      1:1 │    1:N │     │ 1:N
      ▼       ▼      │                          ▼        ▼     │
 ┌─────────┐┌────────┐│                  ┌──────────────┐┌──────────────────┐
 │PitchDeck││ IRDeck ││                  │ VCPreference ││ PortfolioDocument│
 │ file    ││ file   ││                  │ industries   ││ file title       │
 └─────────┘└────────┘│                  │ stages …     │└──────────────────┘
                      │                  └──────────────┘
        Startup × VC  │  (N:M through 모델 3종)
      ┌───────────────┴──────────────────────────────┐
      ▼                    ▼                          ▼
┌──────────────┐   ┌──────────────┐          ┌──────────────────┐
│Recommendation│   │     Like     │          │      Match       │
│ score(숨김)  │   │ by(vc|startup)│ ──상호──▶ │ status matched_at│
│ UQ(vc,start) │   │ UQ(vc,st,by) │   좋아요   │ UQ(vc,startup)   │
└──────────────┘   └──────────────┘          └────────┬─────────┘
                                                  1:1  │
                                                       ▼
                                              ┌──────────────────┐
                                              │     AIReport     │
                                              │ fit_score summary│
                                              └──────────────────┘
```

---

## 4. Django 모델 클래스 (요지)

```python
# accounts/models.py
class User(AbstractUser):
    role = models.CharField(max_length=10, choices=(('vc','VC'),('startup','Startup')))
    phone = models.CharField(max_length=30, blank=True)

# core/models.py (핵심 발췌)
class VCProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='vc_profile', null=True, blank=True)
    firm_name = models.CharField(max_length=100)
    eval_emphasis = models.JSONField(default=list)
    # 선호조건은 VCPreference(1:1)에 위임 → 프록시 프로퍼티로 호환 노출
    @property
    def preferred_industries(self):
        p = self._pref(); return p.preferred_industries if p else []

class VCPreference(models.Model):                       # VCProfile 1:1
    vc = models.OneToOneField(VCProfile, on_delete=models.CASCADE, related_name='preference')
    preferred_industries = models.JSONField(default=list)
    preferred_stages = models.JSONField(default=list)
    preferred_regions = models.JSONField(default=list)
    min_investment = models.BigIntegerField(default=0)
    max_investment = models.BigIntegerField(default=0)

class PitchDeck(models.Model):                          # StartupProfile 1:N
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='pitch_decks')
    file = models.FileField(upload_to='pitch_decks/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class IRDeck(models.Model):                             # StartupProfile 1:N
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='ir_decks')
    file = models.FileField(upload_to='ir_decks/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class PortfolioDocument(models.Model):                  # VCProfile 1:N
    vc = models.ForeignKey(VCProfile, on_delete=models.CASCADE, related_name='portfolio_documents')
    file = models.FileField(upload_to='portfolios/')

class Recommendation(models.Model):                     # Startup × VC
    vc = models.ForeignKey(VCProfile, on_delete=models.CASCADE, related_name='recommendations')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='recommendations')
    score = models.IntegerField(default=0)              # 내부 점수(비노출)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['vc','startup'], name='uniq_recommendation_pair')]

class Like(models.Model):                               # through 모델
    vc = models.ForeignKey(VCProfile, on_delete=models.CASCADE, related_name='likes')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='likes')
    by = models.CharField(max_length=10, choices=(('vc','VC→Startup'),('startup','Startup→VC')))
    class Meta:
        constraints = [models.UniqueConstraint(fields=['vc','startup','by'], name='uniq_like_pair_direction')]

class Match(models.Model):                              # 상호 좋아요
    vc = models.ForeignKey(VCProfile, on_delete=models.CASCADE, related_name='matches')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='matches')
    status = models.CharField(max_length=12, default='matched')
    matched_at = models.DateTimeField(default=timezone.now)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['vc','startup'], name='uniq_match_pair')]

class AIReport(models.Model):                           # Match 1:1
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='ai_report')
    fit_score = models.IntegerField(default=0)          # 결정론적 점수
    summary = models.TextField(blank=True)              # LLM 요약
```

---

## 5. 기능 수정 및 흐름

**가입·로그인**: `User.role` 로 분기. 스타트업은 프로필 등록 →(PitchDeck/IRDeck 업로드)→
VC 추천, VC는 프로필 + `VCPreference` 입력 → 스타트업 추천으로 이동.

**프로필·자료**: 피치덱/IR덱 업로드 시 `StartupProfile.pitch_deck/ir_deck`(대표 포인터)
갱신과 동시에 **`PitchDeck`/`IRDeck` 1:N 행**을 생성(이력 보존). VC 포트폴리오는
`PortfolioDocument` 로 다건 업로드.

**추천 리스트**: `recommend.py`+`evaluate.py` 로 결정론적 점수를 계산해
**`Recommendation.score` 에 저장(`update_or_create`)** 하되, 카드 응답에는 점수를 노출하지
않고 좋아요 버튼만 제공한다.

**좋아요·매칭**: `Like(by)` 로 방향 저장, 중복은 `UniqueConstraint` 로 차단. 반대 방향
`Like` 가 존재하면 `Match` 생성.

**AI 리포트**: `Match` 생성(또는 상세 최초 조회) 시 `ensure_ai_report()` 가
**결정론적 `fit_score`(evaluate overall) + LLM `summary`** 를 묶어 `AIReport`(1:1)로 1회 생성.
API 키가 없으면 템플릿 폴백(`source='fallback'`)이라 데모가 깨지지 않는다.
→ FIT 적합도 점수는 **매칭 이후 AIReport 를 통해 최초 공개**된다.

---

## 6. 명세 대비 설계 판단(의사결정 로그)

1. **fit_score 는 LLM 이 만들지 않는다.** 명세 문구상 "GPT로 점수 계산"으로 읽힐 수
   있으나, 재현성(같은 입력=같은 점수) 보장을 위해 점수는 룰 기반으로 계산하고 LLM 은
   `summary` 만 생성하도록 분리했다.
2. **IR Deck 접근통제 유지(확장).** 명세는 프로필 단계에서 IR덱 업로드를 요구한다(반영).
   추가로, IR 원본은 매칭+NDA 이후 VC 에게만 공개하는 기존 보호 로직을 유지했다.
3. **Like 정규화.** `from/to` 4-FK 대신 2-FK + `by` 플래그(+파생 프로퍼티)로 정규화.
4. **덱/선호조건 분리 + 호환.** 1:N(Deck)·1:1(Preference)로 정규화하되, 기존 프론트엔드
   API 계약은 직렬화기 평탄화/대표 포인터로 그대로 유지했다.
