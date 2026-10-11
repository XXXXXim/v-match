from django.urls import path
from . import views

urlpatterns = [
    path('check-username/', views.check_username),
    path('signup/', views.signup),
    path('login/', views.login),
    path('logout/', views.logout),
    path('me/', views.me),
    path('verify-email/', views.verify_email),
    path('resend-code/', views.resend_code),
]
