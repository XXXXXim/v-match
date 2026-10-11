import re

from rest_framework.decorators import (
    api_view, permission_classes, authentication_classes, throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail

from .models import User
from .serializers import UserSerializer
from .throttling import AuthRateThrottle

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _send_code(user):
    """인증코드 발급 + 이메일 발송(실패해도 무시). DEBUG 면 코드 값을 반환."""
    code = user.issue_email_code()
    try:
        send_mail(
            'V-Match 이메일 인증코드',
            f'인증코드: {code}\n\nV-Match 회원가입을 완료하려면 이 코드를 입력하세요.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except Exception:
        pass
    return code


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def check_username(request):
    """아이디 중복확인. available=True 면 사용 가능."""
    username = (request.query_params.get('username') or '').strip()
    if not username:
        return Response({'available': False, 'error': '아이디를 입력해주세요.'}, status=400)
    if len(username) < 4:
        return Response({'available': False, 'error': '아이디는 4자 이상이어야 합니다.'}, status=400)
    exists = User.objects.filter(username=username).exists()
    if exists:
        return Response({'available': False, 'error': '이미 있는 아이디입니다.'})
    return Response({'available': True, 'message': '사용 가능한 아이디입니다.'})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def signup(request):
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    password_confirm = request.data.get('password_confirm') or ''
    email = (request.data.get('email') or '').strip()
    role = request.data.get('role', 'vc')
    name = (request.data.get('name') or '').strip()
    phone = (request.data.get('phone') or '').strip()

    if not name:
        return Response({'error': '이름은 필수입니다.'}, status=400)
    if not phone:
        return Response({'error': '연락처는 필수입니다.'}, status=400)
    if not username or not password:
        return Response({'error': '아이디와 비밀번호는 필수입니다.'}, status=400)
    if password_confirm and password != password_confirm:
        return Response({'error': '비밀번호가 일치하지 않습니다.'}, status=400)
    if not email:
        return Response({'error': '이메일은 필수입니다.'}, status=400)
    if not EMAIL_RE.match(email):
        return Response({'error': '올바른 이메일 형식이 아닙니다.'}, status=400)
    if role not in ('vc', 'startup'):
        return Response({'error': '역할(role)이 올바르지 않습니다.'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': '이미 있는 아이디입니다.'}, status=400)

    # Django 비밀번호 검증기로 약한 비밀번호 차단.
    try:
        validate_password(password)
    except DjangoValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=400)

    user = User.objects.create_user(
        username=username, password=password, email=email,
        role=role, name=name, phone=phone,
    )
    code = _send_code(user)
    token = Token.objects.create(user=user)
    body = {'token': token.key, 'user': UserSerializer(user).data}
    if settings.DEBUG:                       # 데모 편의: 콘솔 대신 화면에서 바로 확인
        body['dev_code'] = code
    return Response(body, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AuthRateThrottle])
def verify_email(request):
    """인증코드 확인 → email_verified=True (만료/시도제한 적용)."""
    code = (request.data.get('code') or '').strip()
    user = request.user
    if user.email_verified:
        return Response({'user': UserSerializer(user).data})
    ok, err = user.check_email_code(code)
    if not ok:
        return Response({'error': err}, status=400)
    return Response({'user': UserSerializer(user).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AuthRateThrottle])
def resend_code(request):
    """인증코드 재발송(최소 간격 제한)."""
    if not request.user.can_resend_code():
        return Response({'error': '잠시 후 다시 시도해주세요.'}, status=429)
    code = _send_code(request.user)
    body = {'message': '인증코드를 다시 보냈습니다.'}
    if settings.DEBUG:
        body['dev_code'] = code
    return Response(body)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'error': '아이디 또는 비밀번호가 올바르지 않습니다.'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'message': '로그아웃 되었습니다.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)
