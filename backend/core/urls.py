from django.urls import path
from . import views

urlpatterns = [
    path('vc-profile/', views.vc_profile),
    path('startup-profile/', views.startup_profile),
    path('profile-status/', views.profile_status),
    path('startup-profile/ir-deck/', views.upload_ir_deck),
    path('ir-decks/<int:deck_id>/download/', views.ir_deck_download),
    path('startups/', views.startup_list),
    path('startup-profile/pitch-deck/', views.upload_pitch_deck),
    path('startup-profile/ir-summary/approve/', views.approve_ir_summary),
    path('vc-profile/summary/', views.generate_vc_summary_view),
    path('vc-profile/portfolio/', views.portfolio_documents),
    path('analytics/', views.analytics),

    # 추천
    path('recommendations/', views.recommendations),
    path('startup-search/', views.startup_search),
    path('vc-recommendations/', views.vc_recommendations),

    # AI 분석(인라인)
    path('recommendations/<int:startup_id>/explain/', views.explain_startup),
    path('vc-recommendations/<int:vc_id>/explain/', views.explain_vc),

    # 매칭 상세 리포트
    path('match-detail/startup/<int:startup_id>/', views.match_detail_startup),
    path('match-detail/vc/<int:vc_id>/', views.match_detail_vc),
    path('vc/<int:vc_id>/', views.vc_public_detail),

    # 북마크
    path('bookmarks/', views.bookmark_list),
    path('bookmarks/startup/<int:startup_id>/toggle/', views.bookmark_startup),
    path('bookmarks/vc/<int:vc_id>/toggle/', views.bookmark_vc),

    # 좋아요 / 매칭
    path('likes/startup/<int:startup_id>/toggle/', views.like_startup),
    path('likes/vc/<int:vc_id>/toggle/', views.like_vc),


    # Post-Match 워크플로우
    path('matches/', views.matches_list),
    path('matches/<int:match_id>/', views.match_get),
    path('matches/<int:match_id>/request/', views.match_request),
    path('matches/<int:match_id>/accept/', views.match_accept),
    path('matches/<int:match_id>/decline/', views.match_decline),
    path('matches/<int:match_id>/coffeechat/', views.match_coffeechat),
    path('matches/<int:match_id>/ai-report/', views.ai_report),

    # 커피챗(1:1 네트워킹)
    path('coffeechats/request/', views.coffeechat_request),
    path('coffeechats/my-requests/', views.coffeechat_my_requests),
    path('coffeechats/<int:pk>/respond/', views.coffeechat_respond),
    path('coffeechats/<int:pk>/messages/', views.coffeechat_messages),

    # 알림
    path('notifications/', views.notification_list),
    path('notifications/read/', views.mark_notifications_read),
]
