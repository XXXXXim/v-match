from rest_framework.permissions import BasePermission

# 인증 절차상 '인증 전'에도 접근해야 하는 엔드포인트(뷰 함수명 기준).
# 이 목록의 뷰는 email_verified 검사를 건너뛴다.
VERIFY_EXEMPT_VIEWS = {
    'verify_email', 'resend_code', 'me', 'logout',
}


class IsEmailVerified(BasePermission):
    """
    로그인은 됐지만 이메일 인증을 마치지 않은 사용자가 보호 API 를 호출하는 것을 막는다.
    (signup/login 은 AllowAny 라 이 권한이 적용되지 않는다.)
    """
    message = '이메일 인증을 먼저 완료해주세요.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            # 인증 자체가 없으면 IsAuthenticated 가 처리하도록 통과시킨다.
            return True
        # 인증 절차용 엔드포인트는 면제.
        view_name = getattr(view, '__name__', '')
        if view_name in VERIFY_EXEMPT_VIEWS:
            return True
        # 스태프/슈퍼유저는 면제(운영/관리 편의).
        if user.is_staff or user.is_superuser:
            return True
        return bool(getattr(user, 'email_verified', False))
