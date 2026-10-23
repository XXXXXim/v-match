import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# .env 를 가능한 한 일찍 로드(설정값들이 환경변수에 의존하므로).
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env', override=True)
    load_dotenv(override=False)
except Exception:
    pass


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# DEBUG 는 기본 False(운영 안전). 로컬 개발은 .env 에 DJANGO_DEBUG=true 로 켠다.
DEBUG = _env_bool('DJANGO_DEBUG', False)

# SECRET_KEY 는 환경변수 필수. 미설정 시 DEBUG 에서만 임시 키 허용, 운영에서는 기동 중단.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-prod'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY 환경변수가 설정되어야 합니다(운영).')

# ALLOWED_HOSTS 는 콤마 구분 환경변수. 기본은 로컬만 허용.
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get(
        'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    # local apps
    'accounts',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # 배포 환경(예: Vercel)에서는 쓰기 가능한 경로를 환경 변수로 지정한다.
        'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
    }
}

# DATABASE_URL 이 있으면 Postgres 를 쓴다(예: Vercel + Neon). 없으면 위의 SQLite 그대로.
# 서버리스는 요청마다 인스턴스가 바뀔 수 있어, 모든 인스턴스가 같은 DB 를 봐야 로그인·좋아요가 유지된다.
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=0,            # 서버리스: 요청이 끝나면 연결을 닫는다
        conn_health_checks=True,
    )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        # 이메일 인증을 마친 사용자만 보호 API 사용(미인증 우회 차단).
        'accounts.permissions.IsEmailVerified',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'auth': '10/min',       # 로그인·회원가입·인증코드 확인/재발송
        'ai': '6/min',          # 외부 AI 호출(재생성)
        'anon': '30/min',
        'user': '240/min',
    },
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# ----- 공개 데모 모드 -----
# 서버리스 데모는 인스턴스마다 DB 사본을 따로 가지므로, 데모 계정 토큰은 시드 DB에 미리 넣어 두고 지우지 않는다.
VMATCH_DEMO_MODE = _env_bool('VMATCH_DEMO_MODE', False)
VMATCH_DEMO_USERNAMES = ('demo_vc', 'demo_startup')

# ----- V-Match AI 설명 레이어 -----
# (.env 는 파일 상단에서 이미 로드함)
# AI 분석 리포트(핵심): 표준 OpenAI(Chat Completions). 키 없으면 템플릿 폴백.
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# (보조·선택) Anthropic 기반 인라인 설명 레이어. 키 없으면 자동 폴백(미사용).
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
VMATCH_LLM_MODEL = os.environ.get('VMATCH_LLM_MODEL', 'claude-haiku-4-5-20251001')

# ----- 업로드 파일(IR Deck 등) -----
MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', BASE_DIR / 'media')

# IR 원본은 공개 /media/ 가 아닌 비공개 경로에 저장하고, 전용 다운로드 API로만 제공.
PROTECTED_MEDIA_ROOT = os.environ.get('DJANGO_PROTECTED_MEDIA_ROOT', BASE_DIR / 'protected_media')

# ----- 운영 보안 헤더(DEBUG 가 아닐 때만) -----
if not DEBUG:
    SECURE_SSL_REDIRECT = _env_bool('DJANGO_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    X_FRAME_OPTIONS = 'DENY'


# ===== 이메일(인증코드 발송) =====
# 기본은 콘솔 백엔드: 인증코드가 runserver 콘솔에 출력됩니다(SMTP 없이 데모 가능).
# 실제 메일 발송을 원하면 .env 에 EMAIL_HOST_USER / EMAIL_HOST_PASSWORD(앱 비밀번호) 설정.
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'no-reply@v-match.local'
