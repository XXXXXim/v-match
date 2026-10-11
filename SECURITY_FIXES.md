# V-Match 보안 수정 내역 (IR/NDA · 인증 · 역할 · 설정)

리뷰의 "반드시 수정" 항목 중 **치명적 보안 결함 4개 버킷**을 수정했습니다.
모든 수정은 회귀 테스트로 검증했으며, 전체 스위트 24개가 통과합니다.

## 검증 방법
- `core/tests_security.py` (신규, 16개): 결함을 먼저 재현(수정 전 14개 실패)한 뒤 수정 후 전부 통과.
- 기존 테스트 8개: 인증 게이트 적용에 맞춰 픽스처 사용자를 `email_verified=True` 로 갱신, 통과 유지.
- 운영 모드 `manage.py check --deploy`: DEBUG·SECRET_KEY·SSL·쿠키·HSTS 경고 해소(선택적 HSTS preload만 잔존).

---

## 1. NDA 동의 전 IR 원본 노출 차단
**문제**: `StartupProfileSerializer`가 `fields='__all__'` + 중첩 `ir_decks[].file_url` 을 노출.
추천·검색·매칭상세·북마크·목록 응답이 `ir_deck`/`ir_deck_url` 만 제거하고 중첩 `ir_decks` 는 그대로
내보내, IR 업로드 전 이력의 원본 PDF URL이 매칭/NDA 이전에도 노출됨. 게다가 `/media/` 가 공개 제공됨.

**수정**:
- 직렬화기를 분리 (`core/serializers.py`):
  - `StartupPublicSerializer` — 공개 allowlist. IR 원본·민감 재무지표(`cac/ltv/burn_rate/runway_months/equity_structure`) 제외.
  - `StartupOwnerSerializer` — 본인 전용(전체 + 본인 IR 메타).
  - `IRDeckMetaSerializer` — `file_url` 을 **직렬화하지 않고** 게이트된 `download_url` 만 노출.
- 외부 노출 경로 전부 공개 직렬화기로 교체(`views.py`: 추천/검색/목록/북마크/매칭상세/매칭페이로드).
- 전용 IR 다운로드 API 추가: `GET /api/ir-decks/<id>/download/` — 소유자 또는 (매칭+양측 NDA) VC 에게만 스트리밍, 그 외 403.
- IR 파일을 공개 `MEDIA_ROOT` 밖 `PROTECTED_MEDIA_ROOT` 로 저장(`core/models.py`, 콜러블 스토리지).
- 매칭 페이로드의 IR 공개 조건을 `status=='accepted'` → **`both_nda_agreed`** 로 명확화.

> 결정 사항(확인 필요): NDA 승인 후 **전체 IR 이력**을 게이트 다운로드로 제공하도록 구현했습니다.
> "최신만 공개" 정책을 원하면 다운로드 권한 검사에서 최신 1건으로 좁히면 됩니다.

## 2. 이메일 인증 우회 차단
**문제**: 가입 즉시 토큰 발급 + 어떤 API도 `email_verified` 미검사 → 인증 화면 우회 시 전체 API 사용 가능.

**수정**:
- `accounts/permissions.py` `IsEmailVerified` 추가. 인증 절차용(`verify_email/resend_code/me/logout`)만 면제.
- DRF의 `@permission_classes([IsAuthenticated])` 가 전역 기본값을 **덮어쓰는** 특성 때문에,
  보호 대상 36개 뷰의 데코레이터를 `[IsAuthenticated, IsEmailVerified]` 로 일괄 적용.
- 인증코드에 만료(10분)·실패 횟수(5회)·재발송 간격(60초) 추가(`accounts/models.py` + 마이그레이션 0004).
- 가입 시 Django `validate_password` 호출로 약한 비밀번호 차단.
- 로그인/가입/인증코드 API 에 요청 제한(`AuthRateThrottle`, 10/min).

## 3. 역할(VC↔스타트업) 교차 생성 차단
**문제**: `_ensure_startup/_ensure_vc` 와 프로필 생성 API 가 역할 미검사 → VC가 스타트업 프로필을(역도) 생성 가능.

**수정**:
- `_ensure_startup/_ensure_vc` 가 역할 불일치 시 `PermissionDenied`(403).
- `startup_profile`/`vc_profile` 의 생성·수정 경로에 역할 가드 추가.

> 확인 필요: 한 계정이 두 역할을 동시에 가지는 케이스는 차단했습니다(단일 역할 가정).

## 4. 운영 설정 분리 및 보안 헤더
**문제**: `SECRET_KEY` 하드코딩, `DEBUG=True`, `ALLOWED_HOSTS=['*']`.

**수정**(`config/settings.py`):
- `DJANGO_SECRET_KEY`(운영 미설정 시 기동 중단)·`DJANGO_DEBUG`(기본 false)·`DJANGO_ALLOWED_HOSTS` 환경변수화.
- 비-DEBUG 시 SSL 리다이렉트·secure 쿠키·HSTS·nosniff·`X-Frame-Options: DENY`.
- `.env.example` 갱신(신규 변수 문서화). 로컬 `.env` 는 `DJANGO_DEBUG=true`.

---

## 프론트엔드 연동 변경(최소)
- `MatchesView.vue`: IR 다운로드를 공개 `ir_deck_url` → 게이트 `ir_decks[].download_url` 의
  **인증 blob 다운로드**로 변경(토큰 헤더 필요).
- `api/index.js`: 이메일 미인증 403 응답 시 인증 화면으로 유도.

## 이번 범위에서 제외(후속 권장)
다음은 별도 버킷이라 손대지 않았습니다: 파일 MIME/크기 검증, AI 재생성 GET→POST 분리,
페이지네이션·N+1, 그리고 리뷰의 UI/UX 항목(전화번호·`my_briefing` 노출 제거, 커피챗/추천 흐름 통합,
프로필 완료 조건 재정의, 접근성/반응형 등).
