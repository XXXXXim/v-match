from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from config.demo_views import demo_health, reset_demo

urlpatterns = [
    path('admin/', admin.site.urls),
    # 공개 데모 매일 초기화(데모 모드 + CRON_SECRET 이 있을 때만 동작, 아니면 404)
    path('api/demo/reset/', reset_demo),
    path('api/demo/health/', demo_health),
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
