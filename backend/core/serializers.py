from rest_framework import serializers
from .models import (
    VCProfile, VCPreference, StartupProfile, Bookmark,
    PitchDeck, IRDeck, PortfolioDocument, CoffeeChat,
)

# VCProfile 응답/입력에 평탄화해 노출하는 선호조건 필드(프론트 호환)
PREF_FIELDS = (
    'preferred_industries', 'preferred_stages', 'preferred_regions',
    'preferred_education', 'min_investment', 'max_investment',
)


class VCProfileSerializer(serializers.ModelSerializer):
    """
    선호조건은 VCPreference(1:1)에 저장되지만, 기존 API 계약을 유지하기 위해
    VCProfile 페이로드에 평탄화하여 읽고/쓴다.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    firm_name = serializers.CharField(max_length=100, required=False)
    preferred_industries = serializers.ListField(child=serializers.CharField(), required=False)
    preferred_stages = serializers.ListField(child=serializers.CharField(), required=False)
    preferred_regions = serializers.ListField(child=serializers.CharField(), required=False)
    preferred_education = serializers.ListField(child=serializers.CharField(), required=False)
    min_investment = serializers.IntegerField(required=False)
    max_investment = serializers.IntegerField(required=False)
    portfolio_documents = serializers.SerializerMethodField()

    class Meta:
        model = VCProfile
        fields = (
            'id', 'username', 'firm_name', 'website', 'bio', 'vc_summary', 'eval_emphasis',
            'preferred_industries', 'preferred_stages', 'preferred_regions',
            'preferred_education', 'min_investment', 'max_investment', 'portfolio_documents',
            'created_at', 'updated_at',
        )
        read_only_fields = ('user',)

    def get_portfolio_documents(self, obj):
        request = self.context.get('request')
        out = []
        for d in obj.portfolio_documents.all():
            url = request.build_absolute_uri(d.file.url) if request else d.file.url
            out.append({'id': d.id, 'title': d.title, 'url': url,
                        'uploaded_at': d.uploaded_at})
        return out

    def _split_pref(self, validated):
        return {k: validated.pop(k) for k in PREF_FIELDS if k in validated}

    def create(self, validated_data):
        pref = self._split_pref(validated_data)
        if not validated_data.get('firm_name'):
            u = validated_data.get('user')
            validated_data['firm_name'] = getattr(u, 'username', '') or 'VC'
        vc = VCProfile.objects.create(**validated_data)
        if pref:
            vc.set_preference(**pref)
        else:
            VCPreference.objects.get_or_create(vc=vc)
        return vc

    def update(self, instance, validated_data):
        pref = self._split_pref(validated_data)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if pref:
            instance.set_preference(**pref)
        return instance


class PitchDeckSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PitchDeck
        fields = ('id', 'file_url', 'uploaded_at')

    def get_file_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class IRDeckMetaSerializer(serializers.ModelSerializer):
    """
    IR 덱 '메타데이터'만 노출한다. 원본 파일 URL(file_url)은 절대 직렬화하지 않고,
    권한 검사를 수행하는 전용 다운로드 엔드포인트 경로만 제공한다.
    이 직렬화기는 소유자/‐(매칭+양측 NDA) 컨텍스트에서만 사용해야 한다.
    """
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = IRDeck
        fields = ('id', 'uploaded_at', 'download_url')

    def get_download_url(self, obj):
        request = self.context.get('request')
        path = f'/api/ir-decks/{obj.id}/download/'
        return request.build_absolute_uri(path) if request else path


# 매칭 전(공개) 컨텍스트에서 노출하면 안 되는 민감 필드.
_STARTUP_SENSITIVE = (
    'cac', 'ltv', 'burn_rate', 'runway_months', 'equity_structure',
)
# 공개 응답에 절대 포함하지 않는 IR 원본 관련 필드.
_STARTUP_IR_RAW = ('ir_deck', 'ir_deck_url', 'ir_decks')

# 공개(VC 탐색/추천/상세-NDA전) allowlist. IR 원본·민감 재무지표 제외.
_STARTUP_PUBLIC_FIELDS = (
    'id', 'username', 'name', 'industry', 'stage', 'region',
    'funding_needed', 'team_size', 'revenue', 'founded_year', 'description',
    'founder_experience_years', 'prior_exits', 'mau', 'retention_rate',
    'mom_growth', 'market_size', 'market_growth', 'differentiation',
    'legal_structure', 'founder_motivation', 'vision', 'team_culture',
    'founder_education', 'signals', 'summary',
    'pitch_deck_url', 'ir_summary', 'ir_summary_status', 'ir_summary_public',
    'created_at', 'updated_at',
)


class StartupPublicSerializer(serializers.ModelSerializer):
    """매칭 전/공개 노출용. IR 원본 URL 과 민감 재무지표를 포함하지 않는다(allowlist)."""
    username = serializers.CharField(source='user.username', read_only=True)
    pitch_deck_url = serializers.SerializerMethodField()

    class Meta:
        model = StartupProfile
        fields = _STARTUP_PUBLIC_FIELDS
        read_only_fields = fields

    def _abs(self, f):
        if not f:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(f.url) if request else f.url

    def get_pitch_deck_url(self, obj):
        return self._abs(obj.pitch_deck)


class StartupOwnerSerializer(serializers.ModelSerializer):
    """스타트업 본인 전용. 본인 자료(IR 메타·민감 재무지표 포함) 전체를 노출/입력한다."""
    username = serializers.CharField(source='user.username', read_only=True)
    pitch_deck_url = serializers.SerializerMethodField()
    pitch_decks = PitchDeckSerializer(many=True, read_only=True)
    ir_decks = IRDeckMetaSerializer(many=True, read_only=True)

    class Meta:
        model = StartupProfile
        # 본인은 전체 보되, 원본 FileField(ir_deck/pitch_deck)는 URL 메서드로만 노출.
        exclude = ('ir_deck', 'pitch_deck')
        read_only_fields = ('user',)

    def _abs(self, f):
        if not f:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(f.url) if request else f.url

    def get_pitch_deck_url(self, obj):
        return self._abs(obj.pitch_deck)


# 하위 호환 별칭(외부 import 안전망). 기본은 공개용으로 바인딩.
StartupProfileSerializer = StartupPublicSerializer


class BookmarkSerializer(serializers.ModelSerializer):
    startup_detail = StartupProfileSerializer(source='startup', read_only=True)

    class Meta:
        model = Bookmark
        fields = ('id', 'startup', 'startup_detail', 'created_at')
        read_only_fields = ('vc',)


class PortfolioDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioDocument
        fields = ('id', 'title', 'file_url', 'uploaded_at')

    def get_file_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class CoffeeChatSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.username', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    receiver_role = serializers.CharField(source='receiver.role', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    is_sender = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()        # 목록 한 줄 미리보기(최신 메시지)
    last_from_me = serializers.SerializerMethodField()    # 마지막 발화가 '나'인지 → 답장하기/채팅 열기 분기
    locked = serializers.SerializerMethodField()          # 매칭 수락 전이면 채팅 잠금

    class Meta:
        model = CoffeeChat
        fields = (
            'id', 'sender', 'sender_name', 'sender_role',
            'receiver', 'receiver_name', 'receiver_role',
            'message', 'status', 'status_label', 'is_sender', 'created_at',
            'reply_message', 'meeting_type', 'meeting_at', 'meeting_location',
            'responded_at', 'preview', 'last_from_me', 'locked',
        )
        read_only_fields = fields

    def get_locked(self, obj):
        return obj.is_locked()

    def get_is_sender(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.id == obj.sender_id)

    def _last_msg(self, obj):
        # 스레드의 가장 최근 채팅 메시지(없으면 None)
        return obj.messages.order_by('-created_at').first()

    def get_preview(self, obj):
        last = self._last_msg(obj)
        text = last.text if last else obj.message
        text = (text or '').strip().replace('\n', ' ')
        return text[:80] + ('…' if len(text) > 80 else '')

    def get_last_from_me(self, obj):
        request = self.context.get('request')
        if not request:
            return True
        last = self._last_msg(obj)
        # 채팅 메시지가 있으면 그 발신자 기준, 없으면 최초 제안자(sender) 기준
        author_id = last.sender_id if last else obj.sender_id
        return author_id == request.user.id
