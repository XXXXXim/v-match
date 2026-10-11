import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

EMAIL_CODE_TTL_MIN = 10        # 인증코드 유효시간(분)
EMAIL_CODE_MAX_ATTEMPTS = 5    # 코드 오입력 허용 횟수
EMAIL_CODE_RESEND_SEC = 60     # 재발송 최소 간격(초)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('vc', 'VC'),
        ('startup', 'Startup'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='vc')
    name = models.CharField(max_length=50, blank=True)        # 이름
    phone = models.CharField(max_length=30, blank=True)       # 연락처

    # 이메일 인증
    email_verified = models.BooleanField(default=False)
    email_code = models.CharField(max_length=6, blank=True)
    email_code_expires_at = models.DateTimeField(null=True, blank=True)
    email_code_attempts = models.IntegerField(default=0)
    email_code_sent_at = models.DateTimeField(null=True, blank=True)

    def issue_email_code(self):
        """6자리 인증코드 발급 + 만료시각/시도횟수 초기화."""
        self.email_code = f'{random.randint(0, 999999):06d}'
        self.email_verified = False
        self.email_code_expires_at = timezone.now() + timezone.timedelta(
            minutes=EMAIL_CODE_TTL_MIN)
        self.email_code_attempts = 0
        self.email_code_sent_at = timezone.now()
        self.save(update_fields=[
            'email_code', 'email_verified', 'email_code_expires_at',
            'email_code_attempts', 'email_code_sent_at',
        ])
        return self.email_code

    def can_resend_code(self):
        """재발송 최소 간격을 지났는지."""
        if not self.email_code_sent_at:
            return True
        elapsed = (timezone.now() - self.email_code_sent_at).total_seconds()
        return elapsed >= EMAIL_CODE_RESEND_SEC

    def check_email_code(self, code):
        """
        인증코드 검증. (ok, error) 튜플 반환.
        만료/시도초과/불일치를 구분해 처리한다.
        """
        if not self.email_code or not self.email_code_expires_at:
            return False, '발급된 인증코드가 없습니다. 코드를 다시 요청하세요.'
        if timezone.now() > self.email_code_expires_at:
            return False, '인증코드가 만료되었습니다. 코드를 다시 요청하세요.'
        if self.email_code_attempts >= EMAIL_CODE_MAX_ATTEMPTS:
            return False, '인증 시도 횟수를 초과했습니다. 코드를 다시 요청하세요.'
        if (code or '').strip() != self.email_code:
            self.email_code_attempts += 1
            self.save(update_fields=['email_code_attempts'])
            return False, '인증코드가 올바르지 않습니다.'
        # 성공: 코드 폐기
        self.email_verified = True
        self.email_code = ''
        self.email_code_expires_at = None
        self.email_code_attempts = 0
        self.save(update_fields=[
            'email_verified', 'email_code', 'email_code_expires_at',
            'email_code_attempts',
        ])
        return True, None

    def __str__(self):
        return f'{self.username} ({self.role})'
