from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


def protected_storage():
    """IR 원본 등 비공개 파일용 저장소(공개 MEDIA_ROOT 밖). 콜러블이라 마이그레이션에 포함되지 않음."""
    return FileSystemStorage(location=str(settings.PROTECTED_MEDIA_ROOT))


# =========================================================
#  프로필 (User 1:1)
# =========================================================
class VCProfile(models.Model):
    """투자사(VC) 프로필. User 와 1:1. 선호 조건은 VCPreference(1:1) 로 분리."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vc_profile',
        null=True, blank=True,   # 시드 VC는 계정 없이도 생성 가능하게
    )
    firm_name = models.CharField(max_length=100)
    website = models.URLField(blank=True)            # VC 홈페이지/소개 링크
    bio = models.TextField(blank=True)
    vc_summary = models.TextField(blank=True)        # 투자분야·평균규모·철학 AI 요약
    eval_emphasis = models.JSONField(default=list)   # 중시 차원: team/traction/market/financials
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ----- 선호조건 프록시 (VCPreference 로 위임) ---------------------------
    # 기존 코드(recommend/evaluate/ai/views/seed)는 vc.preferred_industries 처럼
    # 평면 접근을 한다. 스키마는 1:1 로 정규화하되, 읽기 호환을 위해 프록시 제공.
    def _pref(self):
        try:
            return self.preference
        except VCPreference.DoesNotExist:
            return None

    @property
    def preferred_industries(self):
        p = self._pref(); return p.preferred_industries if p else []

    @property
    def preferred_stages(self):
        p = self._pref(); return p.preferred_stages if p else []

    @property
    def preferred_regions(self):
        p = self._pref(); return p.preferred_regions if p else []

    @property
    def preferred_education(self):
        p = self._pref(); return p.preferred_education if p else []

    @property
    def min_investment(self):
        p = self._pref(); return p.min_investment if p else 0

    @property
    def max_investment(self):
        p = self._pref(); return p.max_investment if p else 0

    def set_preference(self, **kwargs):
        """선호조건 upsert (VCPreference 생성/갱신). views/seed 의 쓰기 경로에서 사용."""
        pref, _ = VCPreference.objects.get_or_create(vc=self)
        for k, v in kwargs.items():
            if v is not None and hasattr(pref, k):
                setattr(pref, k, v)
        pref.save()
        return pref

    def __str__(self):
        return f'[VC] {self.firm_name}'


class VCPreference(models.Model):
    """VCProfile 와 1:1. 산업/지역/투자단계/투자규모 선호 정보."""
    vc = models.OneToOneField(
        VCProfile, on_delete=models.CASCADE, related_name='preference')
    preferred_industries = models.JSONField(default=list)
    preferred_stages = models.JSONField(default=list)
    preferred_regions = models.JSONField(default=list)
    preferred_education = models.JSONField(default=list)  # 선호 창업자 학력
    min_investment = models.BigIntegerField(default=0)  # 만원 단위
    max_investment = models.BigIntegerField(default=0)  # 만원 단위
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'선호조건({self.vc.firm_name})'


class StartupProfile(models.Model):
    """스타트업 프로필. User 와 1:1. PitchDeck/IRDeck 와 1:N."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='startup_profile',
        null=True, blank=True,   # 시드 데이터는 계정 없이도 생성 가능하게
    )
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=50)
    stage = models.CharField(max_length=50)
    region = models.CharField(max_length=50)
    funding_needed = models.BigIntegerField(default=0)  # 만원 단위
    team_size = models.IntegerField(default=1)
    revenue = models.BigIntegerField(default=0)  # 만원 단위
    founded_year = models.IntegerField(default=2024)
    description = models.TextField(blank=True)

    # ===== 확장 평가 항목 =====
    founder_experience_years = models.IntegerField(default=0)
    prior_exits = models.IntegerField(default=0)
    mau = models.IntegerField(default=0)
    retention_rate = models.IntegerField(default=0)
    mom_growth = models.IntegerField(default=0)
    market_size = models.IntegerField(default=0)
    market_growth = models.IntegerField(default=0)
    cac = models.IntegerField(default=0)
    ltv = models.IntegerField(default=0)
    burn_rate = models.IntegerField(default=0)
    runway_months = models.IntegerField(default=0)
    differentiation = models.TextField(blank=True)
    equity_structure = models.TextField(blank=True)
    legal_structure = models.CharField(max_length=50, blank=True)
    founder_motivation = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    team_culture = models.TextField(blank=True)
    founder_education = models.CharField(max_length=20, default='무관')

    # 실데이터에서 추출한 정량 신호(특허·후속투자·해외진출·고객 등) — FIT/리포트 산정에 사용
    signals = models.JSONField(null=True, blank=True)
    # DART 전자공시 재무 시계열: {'corp_code','source','years':{'2024':{revenue,operating_profit,...}}}
    financials = models.JSONField(null=True, blank=True)
    # 추천 카드용 간결 요약(핵심만). 비어 있으면 프론트가 description 일부로 대체.
    summary = models.TextField(blank=True)

    # 최신(대표) 덱 포인터 — 1:N(PitchDeck/IRDeck) 의 비정규화 캐시.
    # 프로필 카드/직렬화의 빠른 접근용. 정규화 원본은 pitch_decks / ir_decks 관계.
    pitch_deck = models.FileField(upload_to='pitch_decks/', null=True, blank=True)
    ir_deck = models.FileField(upload_to='ir_decks/', storage=protected_storage, null=True, blank=True)

    # IR 요약: AI 초안 → 창업자 검수/승인 → 공개여부 선택
    ir_summary = models.TextField(blank=True)
    ir_summary_status = models.CharField(max_length=10, default='none')  # none|draft|approved
    ir_summary_public = models.BooleanField(default=False)
    summary_view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'[Startup] {self.name}'


# =========================================================
#  업로드 자료 (프로필 1:N)
# =========================================================
class PitchDeck(models.Model):
    """StartupProfile 와 1:N. 피치덱 파일 이력."""
    startup = models.ForeignKey(
        StartupProfile, on_delete=models.CASCADE, related_name='pitch_decks')
    file = models.FileField(upload_to='pitch_decks/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'PitchDeck({self.startup.name}) #{self.id}'


class IRDeck(models.Model):
    """StartupProfile 와 1:N. IR Deck 파일 이력(매칭 후 VC에게만 원본 공개)."""
    startup = models.ForeignKey(
        StartupProfile, on_delete=models.CASCADE, related_name='ir_decks')
    file = models.FileField(upload_to='ir_decks/', storage=protected_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'IRDeck({self.startup.name}) #{self.id}'


class PortfolioDocument(models.Model):
    """VCProfile 와 1:N. 포트폴리오 자료."""
    vc = models.ForeignKey(
        VCProfile, on_delete=models.CASCADE, related_name='portfolio_documents')
    file = models.FileField(upload_to='portfolios/')
    title = models.CharField(max_length=120, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Portfolio({self.vc.firm_name}) #{self.id}'


# =========================================================
#  추천 / 좋아요 / 매칭
# =========================================================
class Recommendation(models.Model):
    """
    (StartupProfile, VCProfile) 추천 결과 저장.
    score 는 결정론적 룰 기반 '내부 점수'로 화면에는 노출하지 않는다(매칭 전 숨김).
    """
    vc = models.ForeignKey(
        VCProfile, on_delete=models.CASCADE, related_name='recommendations')
    startup = models.ForeignKey(
        StartupProfile, on_delete=models.CASCADE, related_name='recommendations')
    score = models.IntegerField(default=0)  # 내부 점수(비노출)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vc', 'startup'], name='uniq_recommendation_pair'),
        ]
        ordering = ['-score']

    def __str__(self):
        return f'추천 {self.vc.firm_name} ~ {self.startup.name} ({self.score})'


class Bookmark(models.Model):
    """(VCProfile ↔ StartupProfile) 쌍 기반 북마크. by 로 누가 저장했는지 구분."""
    BY = [('vc', 'VC가 스타트업 저장'), ('startup', '스타트업이 VC 저장')]
    vc = models.ForeignKey('VCProfile', on_delete=models.CASCADE, related_name='bookmarks')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='bookmarks')
    by = models.CharField(max_length=10, choices=BY, default='vc')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vc', 'startup', 'by')

    def __str__(self):
        return f'북마크[{self.by}] {self.vc.firm_name} ~ {self.startup.name}'


class Like(models.Model):
    """
    소개팅식 '좋아요'. (VCProfile ↔ StartupProfile) 쌍 + by(방향).
      - by='vc'      : VC → 스타트업
      - by='startup' : 스타트업 → VC
    양쪽 by 가 모두 존재하면 매칭 성사.

    명세의 from_startup/from_vc/to_startup/to_vc 는 (vc, startup, by) 2개 FK +
    방향 플래그로 정규화하여 표현한다(항상 null 인 FK 2개를 두지 않는 정석 형태).
    아래 프로퍼티로 from_/to_ 시맨틱을 그대로 제공한다.
    """
    BY = [('vc', 'VC→스타트업'), ('startup', '스타트업→VC')]
    vc = models.ForeignKey('VCProfile', on_delete=models.CASCADE, related_name='likes')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='likes')
    by = models.CharField(max_length=10, choices=BY, default='vc')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vc', 'startup', 'by'], name='uniq_like_pair_direction'),
        ]

    # from_/to_ 파생 접근자 (명세 호환)
    @property
    def from_vc(self):
        return self.vc if self.by == 'vc' else None

    @property
    def from_startup(self):
        return self.startup if self.by == 'startup' else None

    @property
    def to_startup(self):
        return self.startup if self.by == 'vc' else None

    @property
    def to_vc(self):
        return self.vc if self.by == 'startup' else None

    def __str__(self):
        return f'좋아요[{self.by}] {self.vc.firm_name} ~ {self.startup.name}'


class Match(models.Model):
    """
    상호 좋아요로 성사된 매칭. (StartupProfile, VCProfile, matched_at, status)
    + Post-Match 워크플로우(커피챗/NDA/브리핑) 확장 필드.
    AI 리포트(적합도 점수+요약)는 AIReport(1:1) 로 분리.
    """
    STATUS = [
        ('matched', '매칭됨'),
        ('requested', '미팅 요청'),
        ('accepted', '수락됨'),
        ('declined', '거절됨'),
    ]
    vc = models.ForeignKey('VCProfile', on_delete=models.CASCADE, related_name='matches')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='matches')
    status = models.CharField(max_length=12, choices=STATUS, default='matched')
    matched_at = models.DateTimeField(default=timezone.now)  # 매칭 성사 시각
    requested_by = models.CharField(max_length=10, blank=True)  # 'vc' | 'startup'

    # 원클릭 NDA 동의 시각(양측 동의 시 연락처/IR 원본 공개)
    vc_nda_agreed_at = models.DateTimeField(null=True, blank=True)
    startup_nda_agreed_at = models.DateTimeField(null=True, blank=True)

    # AI 미팅 준비 브리핑 캐시(수락 시 1회 생성)
    briefing_vc = models.TextField(blank=True)
    briefing_startup = models.TextField(blank=True)
    briefing_source = models.CharField(max_length=20, blank=True)

    # 매칭 후 AI 심층 분석(팀/제품차별화/시장/재무) 캐시
    deep_analysis = models.TextField(blank=True)
    deep_source = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['vc', 'startup'], name='uniq_match_pair'),
        ]
        ordering = ['-updated_at']

    @property
    def both_nda_agreed(self):
        return bool(self.vc_nda_agreed_at and self.startup_nda_agreed_at)

    def __str__(self):
        return f'매칭[{self.status}] {self.vc.firm_name} ~ {self.startup.name}'


class AIReport(models.Model):
    """
    Match 와 1:1. 매칭 성사 후 '최초로' 제공되는 FIT 적합도 점수 + AI 분석 요약.

    원칙(중요): fit_score 는 결정론적 룰 기반 점수(recommend+evaluate)로 채운다.
    LLM 은 summary(자연어 설명)만 생성한다 → 같은 입력이면 같은 점수(재현성).
    """
    match = models.OneToOneField(
        Match, on_delete=models.CASCADE, related_name='ai_report')
    fit_score = models.IntegerField(default=0)   # 결정론적 FIT 점수(0~100)
    summary = models.TextField(blank=True)       # LLM 자연어 분석(executive summary)
    report_json = models.JSONField(null=True, blank=True)  # 전문 실사 리포트(섹션·강점·우려·하드게이트)
    source = models.CharField(max_length=20, default='llm')  # 'llm' | 'fallback'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'AIReport(match#{self.match_id}) fit={self.fit_score}'


class MatchResult(models.Model):
    """(VCProfile, StartupProfile) 쌍 AI 설명 캐시(추천 리스트 인라인 설명용)."""
    vc = models.ForeignKey('VCProfile', on_delete=models.CASCADE, related_name='match_results')
    startup = models.ForeignKey(StartupProfile, on_delete=models.CASCADE, related_name='match_results')
    cache_key = models.CharField(max_length=64, db_index=True)
    ai_explanation = models.TextField()
    source = models.CharField(max_length=20, default='llm')  # 'llm' | 'fallback'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vc', 'startup')

    def __str__(self):
        return f'AI분석 {self.vc.firm_name} ~ {self.startup.name}'


class Notification(models.Model):
    """인앱 알림. 좋아요/매칭 성사 등 이벤트 발생 시 생성."""
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    link_startup = models.ForeignKey(
        StartupProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    link_vc = models.ForeignKey(
        'VCProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'알림 -> {self.recipient.username}: {self.message[:20]}'


class CoffeeChat(models.Model):
    """상호 매칭된 사용자끼리 주고받는 텍스트 기반 1:1 커피챗 제안."""
    STATUS_PENDING = 'PENDING'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, '대기 중'),
        (STATUS_ACCEPTED, '수락'),
        (STATUS_REJECTED, '거절'),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_coffeechats',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_coffeechats',
    )
    message = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    # 답장 + 미팅 일정(수락 시)
    reply_message = models.TextField(blank=True)
    MEETING_ONLINE = 'online'
    MEETING_OFFLINE = 'offline'
    meeting_type = models.CharField(max_length=10, blank=True)   # online | offline
    meeting_at = models.DateTimeField(null=True, blank=True)
    meeting_location = models.CharField(max_length=200, blank=True)  # 장소 또는 화상링크
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', '-created_at'], name='cc_sender_created_idx'),
            models.Index(fields=['receiver', '-created_at'], name='cc_receiver_created_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                condition=models.Q(status='PENDING'),
                name='uniq_pending_coffeechat_pair',
            ),
        ]

    def __str__(self):
        return f'커피챗 {self.sender.username} → {self.receiver.username} [{self.status}]'

    def is_locked(self):
        """연결된 매칭이 아직 '수락 완료(accepted)'가 아니면 채팅 잠금.
        커피챗 요청 → (상대가) 매칭에서 요청 수락 → 채팅 활성화 순서를 강제한다."""
        s, r = self.sender, self.receiver
        if s.role == 'vc' and r.role == 'startup':
            vc_uid, su_uid = s.id, r.id
        elif s.role == 'startup' and r.role == 'vc':
            vc_uid, su_uid = r.id, s.id
        else:
            return True
        return not Match.objects.filter(
            vc__user_id=vc_uid, startup__user_id=su_uid, status='accepted',
        ).exists()


class ChatMessage(models.Model):
    """커피챗 스레드 안의 1:1 채팅 메시지."""
    coffeechat = models.ForeignKey(
        CoffeeChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='chat_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.coffeechat_id}] {self.sender.username}: {self.text[:20]}'
