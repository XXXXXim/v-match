from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """로그인/회원가입/인증코드 확인·재발송 — IP 기준 요청 제한('auth' rate)."""
    scope = 'auth'


class AIRateThrottle(UserRateThrottle):
    """외부 AI 호출(리포트 재생성 등) — 사용자 기준 제한('ai' rate)."""
    scope = 'ai'
