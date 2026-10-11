from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from django.db import models, transaction, IntegrityError
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    VCProfile, StartupProfile, Bookmark, Like, MatchResult, Notification, Match,
    Recommendation, AIReport, PitchDeck, IRDeck, PortfolioDocument,
    CoffeeChat, ChatMessage,
)
from .serializers import (
    VCProfileSerializer, StartupPublicSerializer, StartupOwnerSerializer,
    PortfolioDocumentSerializer, CoffeeChatSerializer,
)
# 외부에 노출되는 모든 목록/상세는 '공개' 직렬화기를 기본으로 사용한다.
StartupProfileSerializer = StartupPublicSerializer
from accounts.throttling import AIRateThrottle
from accounts.permissions import IsEmailVerified
from .recommend import calculate_recommendation
from .evaluate import evaluate
from .ai import get_or_create_explanation
from .industry import classify_startup, vc_groups, group_label

AXIS_MAX = {'industry': 40, 'stage': 25, 'funding': 20, 'region': 15}
AXIS_LABEL = {'industry': '산업', 'stage': '단계', 'funding': '투자금', 'region': '지역'}


def _abs(request, f):
    """파일 필드 → 절대 URL(없으면 None)."""
    if not f:
        return None
    return request.build_absolute_uri(f.url) if request else f.url


def _ir_download_url(request, deck_id):
    """IR 원본은 공개 URL 대신 권한 검사를 수행하는 다운로드 API 경로로만 노출."""
    path = f'/api/ir-decks/{deck_id}/download/'
    return request.build_absolute_uri(path) if request else path


def _can_access_ir(user, startup):
    """
    IR 원본 접근 권한:
      - 소유자(해당 스타트업 계정 본인), 또는
      - 그 스타트업과 매칭된 VC 이면서 양측 NDA 동의가 완료된 경우.
    """
    if startup.user_id and startup.user_id == user.id:
        return True
    if getattr(user, 'role', None) == 'vc':
        vc = VCProfile.objects.filter(user=user).first()
        if vc:
            m = Match.objects.filter(vc=vc, startup=startup).first()
            if m and m.both_nda_agreed:
                return True
    return False


def _get_vc(user):
    return VCProfile.objects.filter(user=user).first()


def _get_startup(user):
    return StartupProfile.objects.filter(user=user).first()


def _ensure_startup(user):
    """PDF 등록만으로 프로필을 생성하므로, 없으면 최소 프로필 자동 생성.

    역할이 'startup' 이 아닌 계정은 스타트업 프로필을 가질 수 없다(403).
    """
    if getattr(user, 'role', None) != 'startup':
        raise PermissionDenied('스타트업 계정만 사용할 수 있는 기능입니다.')
    sp = StartupProfile.objects.filter(user=user).first()
    if not sp:
        sp = StartupProfile.objects.create(user=user, name=user.username)
    return sp


def _ensure_vc(user):
    if getattr(user, 'role', None) != 'vc':
        raise PermissionDenied('VC 계정만 사용할 수 있는 기능입니다.')
    vc = VCProfile.objects.filter(user=user).first()
    if not vc:
        vc = VCProfile.objects.create(user=user, firm_name=user.username)
    return vc


def _startup_registered(sp):
    """스타트업 프로필이 '실제로 작성'되었는지 여부.

    가입 직후 자동 생성되는 최소 스텁(name 만 채워진 상태)은 미등록으로 보고,
    PDF(피치덱/IR덱)를 올렸거나 핵심 프로필 내용이 채워졌으면 등록 완료로 본다.
    → 신규 가입자에게만 '프로필 완성하기'가, 작성/데모 데이터에는 '추천 받기'가 뜨도록.
    """
    if not sp:
        return False
    if sp.pitch_decks.exists() or sp.ir_decks.exists():
        return True
    return any(str(v or '').strip() for v in (
        sp.industry, sp.stage, sp.description, sp.summary, sp.ir_summary,
    ))


def _vc_registered(vc):
    """VC 프로필이 '실제로 작성'되었는지 여부.

    포트폴리오를 올렸거나, 선호조건 또는 핵심 프로필 내용이 채워졌으면 등록 완료로 본다.
    (firm_name 만 있는 가입 직후 스텁은 미등록)
    """
    if not vc:
        return False
    if vc.portfolio_documents.exists():
        return True
    if vc._pref() is not None:
        return True
    if any(str(v or '').strip() for v in (vc.bio, vc.vc_summary, vc.website)):
        return True
    return bool(vc.eval_emphasis)


def _axis_report(sub_scores):
    rows = []
    for k, mx in AXIS_MAX.items():
        got = sub_scores.get(k, 0)
        ratio = got / mx if mx else 0
        level = '강점' if ratio >= 0.8 else ('보통' if ratio >= 0.4 else '약점')
        rows.append({'key': k, 'label': AXIS_LABEL[k], 'score': got, 'max': mx, 'level': level})
    return rows


def _vc_brief(vc):
    return {
        'id': vc.id, 'firm_name': vc.firm_name,
        'website': vc.website,
        'preferred_industries': vc.preferred_industries,
        'preferred_stages': vc.preferred_stages,
        'preferred_regions': vc.preferred_regions,
        'min_investment': vc.min_investment, 'max_investment': vc.max_investment,
        'bio': vc.bio, 'vc_summary': vc.vc_summary,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def vc_public_detail(request, vc_id):
    """단일 VC 상세 정보(스타트업이 VC 카드/알림 클릭 시 보는 페이지)."""
    vc = VCProfile.objects.filter(id=vc_id).first()
    if not vc:
        return Response({'error': 'VC를 찾을 수 없습니다.'}, status=404)
    d = _vc_brief(vc)
    sp = _get_startup(request.user)
    if sp:
        d['is_liked'] = Like.objects.filter(vc=vc, startup=sp, by='startup').exists()
        d['is_bookmarked'] = Bookmark.objects.filter(vc=vc, startup=sp, by='startup').exists()
        d['is_matched'] = Match.objects.filter(vc=vc, startup=sp).exists()
        if d['is_matched']:
            d['is_liked'] = True
    return Response(d)


def _notify(user, message, startup=None, vc=None):
    if user is None:
        return
    Notification.objects.create(recipient=user, message=message,
                                link_startup=startup, link_vc=vc)


def _save_recommendation(vc, startup, score):
    """결정론적 추천 점수를 Recommendation 에 영속화(내부 점수·비노출)."""
    Recommendation.objects.update_or_create(
        vc=vc, startup=startup, defaults={'score': int(score)})


def ensure_ai_report(match, request=None, force=False):
    """
    매칭 성사 후 AIReport 생성/반환.
    핵심: GPT(OpenAI)가 데이터/PDF를 분석해 fit_score + summary 생성. → core/ai_report.py
    - 이미 생성된 리포트가 있으면 캐시 반환.
    - 단, 폴백/에러로 저장됐는데 이제 LLM 키가 설정돼 있으면 자동 재생성(업그레이드).
    - force=True 면 무조건 재생성.
    """
    from .ai_report import generate_ai_report, has_llm
    existing = AIReport.objects.filter(match=match).first()
    if existing and not force:
        stale = existing.source in ('fallback', 'error') and has_llm()
        if not stale:
            return existing

    try:
        fit, summary, source, report_json = generate_ai_report(match.vc, match.startup)
    except Exception:
        # 재생성 실패가 이미 정상적으로 저장된 리포트를 파괴하면 안 된다.
        if existing:
            return existing
        fit, summary, source, report_json = 0, 'AI 리포트 생성에 일시적으로 실패했습니다. 잠시 후 다시 시도해주세요.', 'error', None

    if existing:
        old_json = existing.report_json if isinstance(existing.report_json, dict) else {}
        new_json = report_json if isinstance(report_json, dict) else {}

        # 최초 정상 리포트의 총점과 섹션 배점은 평가 스냅샷으로 간주해 잠근다.
        # 재생성은 자연어 설명만 개선하며 점수 체계에는 관여하지 않는다.
        if existing.source != 'error' and old_json:
            fit = existing.fit_score
            old_sections = {
                s.get('name'): s for s in old_json.get('sections', [])
                if isinstance(s, dict) and s.get('name')
            }
            merged_sections = []
            for section in new_json.get('sections', []):
                if not isinstance(section, dict):
                    continue
                merged = dict(section)
                locked = old_sections.get(section.get('name'))
                if locked is not None:
                    merged['score'] = locked.get('score', 0)
                merged_sections.append(merged)
            # 모델 응답에서 섹션이 누락돼도 기존 평가 기준은 사라지지 않는다.
            present = {s.get('name') for s in merged_sections}
            merged_sections.extend(dict(s) for name, s in old_sections.items() if name not in present)
            new_json['sections'] = merged_sections
            new_json['fit_score'] = fit
            new_json['recommendation'] = old_json.get('recommendation') or new_json.get('recommendation')

        # LLM/네트워크 실패 응답으로 기존 정상 내용을 덮어쓰지 않는다.
        if source == 'error' or not new_json:
            return existing

        existing.fit_score = fit
        existing.summary = summary
        existing.source = source
        existing.report_json = new_json
        existing.save(update_fields=['fit_score', 'summary', 'source', 'report_json'])
        return existing

    # 동시 요청에도 Match 당 하나의 리포트만 남긴다.
    with transaction.atomic():
        report, created = AIReport.objects.get_or_create(
            match=match,
            defaults={'fit_score': fit, 'summary': summary, 'source': source, 'report_json': report_json},
        )
    return report


# ---------------- VC 프로필 ----------------
@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def vc_profile(request):
    if request.method == 'GET':
        p = _get_vc(request.user)
        if not p:
            return Response({'detail': '등록된 VC 프로필이 없습니다.'}, status=404)
        return Response(VCProfileSerializer(p).data)
    # 생성/수정은 VC 계정만 가능.
    if request.user.role != 'vc':
        return Response({'error': 'VC 계정만 VC 프로필을 만들 수 있습니다.'}, status=403)
    if request.method == 'POST':
        if _get_vc(request.user):
            return Response({'error': '이미 VC 프로필이 존재합니다.'}, status=400)
        s = VCProfileSerializer(data=request.data)
        if s.is_valid():
            s.save(user=request.user)
            return Response(s.data, status=201)
        return Response(s.errors, status=400)
    p = _get_vc(request.user)
    if not p:
        # 포트폴리오 업로드 전에 선호도부터 저장하는 경우 → 생성(upsert)
        s = VCProfileSerializer(data=request.data)
        if s.is_valid():
            s.save(user=request.user)
            return Response(s.data, status=201)
        return Response(s.errors, status=400)
    s = VCProfileSerializer(p, data=request.data, partial=True)
    if s.is_valid():
        s.save()
        return Response(s.data)
    return Response(s.errors, status=400)


# ---------------- 스타트업 프로필 ----------------
@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def startup_profile(request):
    if request.method == 'GET':
        p = _get_startup(request.user)
        if not p:
            return Response({'detail': '등록된 스타트업 프로필이 없습니다.'}, status=404)
        return Response(StartupOwnerSerializer(p, context={'request': request}).data)
    # 생성/수정은 스타트업 계정만 가능.
    if request.user.role != 'startup':
        return Response({'error': '스타트업 계정만 스타트업 프로필을 만들 수 있습니다.'}, status=403)
    if request.method == 'POST':
        if _get_startup(request.user):
            return Response({'error': '이미 스타트업 프로필이 존재합니다.'}, status=400)
        s = StartupOwnerSerializer(data=request.data, context={'request': request})
        if s.is_valid():
            s.save(user=request.user)
            return Response(s.data, status=201)
        return Response(s.errors, status=400)
    p = _get_startup(request.user)
    if not p:
        return Response({'detail': '등록된 스타트업 프로필이 없습니다.'}, status=404)
    s = StartupOwnerSerializer(p, data=request.data, partial=True, context={'request': request})
    if s.is_valid():
        s.save()
        return Response(s.data)
    return Response(s.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def startup_list(request):
    qs = StartupProfile.objects.all().order_by('-created_at')
    return Response(StartupProfileSerializer(qs, many=True).data)


# ---------------- 추천: VC → 스타트업 ----------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def recommendations(request):
    vc = _get_vc(request.user)
    if not vc:
        return Response({'error': 'VC 프로필을 먼저 등록해주세요.'}, status=400)
    try:
        min_score = int(request.query_params.get('min_score', 0))
    except (TypeError, ValueError):
        min_score = 0
    bk = set(Bookmark.objects.filter(vc=vc, by='vc').values_list('startup_id', flat=True))
    lk = set(Like.objects.filter(vc=vc, by='vc').values_list('startup_id', flat=True))
    matched_ids = set(Match.objects.filter(vc=vc).values_list('startup_id', flat=True))
    ex = set(MatchResult.objects.filter(vc=vc).values_list('startup_id', flat=True))
    out = []
    for s in StartupProfile.objects.all():
        fit, sub, reasons = calculate_recommendation(vc, s)
        ev = evaluate(vc, s, fit)
        _save_recommendation(vc, s, ev['overall'])
        if ev['overall'] < min_score:
            continue
        d = StartupProfileSerializer(s, context={'request': request}).data
        d.pop('ir_deck', None)            # IR 원본 PDF는 매칭 전까지 잠금
        d.pop('ir_deck_url', None)
        d['ir_locked'] = True
        d['summary_shared'] = (s.ir_summary_status == 'approved' and s.ir_summary_public)
        if not d['summary_shared']:
            d['ir_summary'] = ''
        # 추천 리스트는 점수를 노출하지 않는다(카드 + 좋아요만). 점수는 내부 정렬용.
        d['_rank'] = ev['overall']
        d.update(is_bookmarked=s.id in bk, is_liked=s.id in lk or s.id in matched_ids,
                 is_matched=s.id in matched_ids,
                 has_ai_explanation=s.id in ex)
        out.append(d)
    out.sort(key=lambda x: (x['_rank'], x['id']), reverse=True)
    for d in out:
        d.pop('_rank', None)
    return Response(out)


# ---------------- 추천: 스타트업 → VC ----------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def vc_recommendations(request):
    startup = _get_startup(request.user)
    if not startup:
        return Response({'error': '스타트업 프로필을 먼저 등록해주세요.'}, status=400)
    try:
        min_score = int(request.query_params.get('min_score', 0))
    except (TypeError, ValueError):
        min_score = 0
    bk = set(Bookmark.objects.filter(startup=startup, by='startup').values_list('vc_id', flat=True))
    lk = set(Like.objects.filter(startup=startup, by='startup').values_list('vc_id', flat=True))
    matched_ids = set(Match.objects.filter(startup=startup).values_list('vc_id', flat=True))
    ex = set(MatchResult.objects.filter(startup=startup).values_list('vc_id', flat=True))
    # 내(스타트업) 산업군 — 이 산업군에 관심 있는 VC를 강조 표시
    my_group = classify_startup(startup.industry, startup.description)
    my_group_label = group_label(my_group)
    out = []
    for vc in VCProfile.objects.select_related('preference').all():
        fit, sub, reasons = calculate_recommendation(vc, startup)
        ev = evaluate(vc, startup, fit)
        _save_recommendation(vc, startup, ev['overall'])
        if ev['overall'] < min_score:
            continue
        d = _vc_brief(vc)
        # 추천 리스트는 점수를 노출하지 않는다(카드 + 좋아요만). 점수는 내부 정렬용.
        d['_rank'] = ev['overall']
        # 이 VC가 우리(스타트업) 산업군에 관심 있는지
        d['group_match'] = my_group in vc_groups(vc.preferred_industries)
        d['my_group_label'] = my_group_label
        d.update(is_bookmarked=vc.id in bk, is_liked=vc.id in lk or vc.id in matched_ids,
                 is_matched=vc.id in matched_ids,
                 has_ai_explanation=vc.id in ex)
        out.append(d)
    # 우리 산업군에 관심 있는 VC를 먼저, 그다음 적합도 순
    out.sort(key=lambda x: (x['group_match'], x['_rank'], x['id']), reverse=True)
    for d in out:
        d.pop('_rank', None)
    return Response(out)


# ---------------- AI 분석(인라인) ----------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def explain_startup(request, startup_id):
    vc = _get_vc(request.user)
    if not vc:
        return Response({'error': 'VC 프로필을 먼저 등록해주세요.'}, status=400)
    startup = StartupProfile.objects.filter(id=startup_id).first()
    if not startup:
        return Response({'error': '스타트업을 찾을 수 없습니다.'}, status=404)
    score, sub, reasons = calculate_recommendation(vc, startup)
    text, source, cached = get_or_create_explanation(vc, startup, score, sub, reasons)
    return Response({'ai_explanation': text, 'source': source, 'cached': cached})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def explain_vc(request, vc_id):
    startup = _get_startup(request.user)
    if not startup:
        return Response({'error': '스타트업 프로필을 먼저 등록해주세요.'}, status=400)
    vc = VCProfile.objects.filter(id=vc_id).first()
    if not vc:
        return Response({'error': 'VC를 찾을 수 없습니다.'}, status=404)
    score, sub, reasons = calculate_recommendation(vc, startup)
    text, source, cached = get_or_create_explanation(vc, startup, score, sub, reasons)
    return Response({'ai_explanation': text, 'source': source, 'cached': cached})


# ---------------- 매칭 상세 리포트 ----------------
def _startup_light(s, request=None):
    """매칭 전 노출용 기본 정보(민감 재무·지분 제외). IR 원본 비노출."""
    shared = (s.ir_summary_status == 'approved' and s.ir_summary_public)
    return {
        'id': s.id, 'name': s.name, 'industry': s.industry, 'stage': s.stage,
        'region': s.region, 'description': s.description,
        'funding_needed': s.funding_needed, 'team_size': s.team_size,
        'founded_year': s.founded_year,
        'revenue': s.revenue, 'mau': s.mau, 'retention_rate': s.retention_rate,
        'pitch_deck_url': _abs(request, s.pitch_deck),
        'ir_summary': s.ir_summary if shared else '',
    }


def _detail_payload(vc, startup, matched, request=None):
    payload = {
        'matched': matched,
        'vc': _vc_brief(vc),
        'startup': _startup_light(startup, request),
        'stage': startup.stage,
    }
    # 보는 사람(viewer) 기준 좋아요/북마크/매칭 상태 — 상세 하단의 '관심 보내기/저장' 버튼용.
    # VC가 스타트업을 보면 by='vc', 스타트업이 VC를 보면 by='startup' 방향으로 판단.
    payload['is_matched'] = matched
    payload['is_liked'] = matched
    payload['is_bookmarked'] = False
    if request:
        if request.user.id == vc.user_id:
            payload['is_liked'] = matched or Like.objects.filter(
                vc=vc, startup=startup, by='vc').exists()
            payload['is_bookmarked'] = Bookmark.objects.filter(
                vc=vc, startup=startup, by='vc').exists()
        elif startup.user_id and request.user.id == startup.user_id:
            payload['is_liked'] = matched or Like.objects.filter(
                vc=vc, startup=startup, by='startup').exists()
            payload['is_bookmarked'] = Bookmark.objects.filter(
                vc=vc, startup=startup, by='startup').exists()
    if not matched:
        # 매칭 전: 점수 없이 프로필만 노출. 적합도(FIT)는 매칭 후 AI 리포트에서만 제공.
        return payload

    # 매칭 후: AI 분석 리포트 (FIT 점수 + 요약) — 유일한 점수 노출 지점
    m = Match.objects.filter(vc=vc, startup=startup).first()
    report = ensure_ai_report(m, request) if m else None
    payload.update({
        # 매칭 후 제공되는 FIT 적합도 점수 + AI 요약(AIReport 1:1)
        'match_id': m.id if m else None,
        'ai_report': ({'fit_score': report.fit_score, 'summary': report.summary,
                       'source': report.source, 'created_at': report.created_at,
                       'report': report.report_json}
                      if report else None),
        'startup': StartupProfileSerializer(startup, context={'request': request}).data,
    })
    if request:
        counterpart = startup.user if request.user.id == vc.user_id else vc.user
        payload['counterpart_user_id'] = counterpart.id if counterpart else None
    # IR 원본은 '커피챗 수락(NDA)' 단계에서만 공개 → 상세에서는 잠금 유지
    payload['startup'].pop('ir_deck', None)
    payload['startup'].pop('ir_deck_url', None)
    return payload


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_detail_startup(request, startup_id):
    vc = _get_vc(request.user)
    if not vc:
        return Response({'error': 'VC 프로필을 먼저 등록해주세요.'}, status=400)
    startup = StartupProfile.objects.filter(id=startup_id).first()
    if not startup:
        return Response({'error': '스타트업을 찾을 수 없습니다.'}, status=404)
    if startup.ir_summary_status == 'approved' and startup.ir_summary_public:
        StartupProfile.objects.filter(id=startup.id).update(
            summary_view_count=models.F('summary_view_count') + 1)
    matched = Match.objects.filter(vc=vc, startup=startup).exists()
    return Response(_detail_payload(vc, startup, matched, request))


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_detail_vc(request, vc_id):
    startup = _get_startup(request.user)
    if not startup:
        return Response({'error': '스타트업 프로필을 먼저 등록해주세요.'}, status=400)
    vc = VCProfile.objects.filter(id=vc_id).first()
    if not vc:
        return Response({'error': 'VC를 찾을 수 없습니다.'}, status=404)
    matched = Match.objects.filter(vc=vc, startup=startup).exists()
    return Response(_detail_payload(vc, startup, matched, request))


# ---------------- 북마크 ----------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def bookmark_startup(request, startup_id):
    vc = _get_vc(request.user)
    if not vc:
        return Response({'error': 'VC 프로필을 먼저 등록해주세요.'}, status=400)
    startup = StartupProfile.objects.filter(id=startup_id).first()
    if not startup:
        return Response({'error': '스타트업을 찾을 수 없습니다.'}, status=404)
    obj = Bookmark.objects.filter(vc=vc, startup=startup, by='vc').first()
    if obj:
        obj.delete()
        return Response({'bookmarked': False})
    Bookmark.objects.create(vc=vc, startup=startup, by='vc')
    return Response({'bookmarked': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def bookmark_vc(request, vc_id):
    startup = _get_startup(request.user)
    if not startup:
        return Response({'error': '스타트업 프로필을 먼저 등록해주세요.'}, status=400)
    vc = VCProfile.objects.filter(id=vc_id).first()
    if not vc:
        return Response({'error': 'VC를 찾을 수 없습니다.'}, status=404)
    obj = Bookmark.objects.filter(vc=vc, startup=startup, by='startup').first()
    if obj:
        obj.delete()
        return Response({'bookmarked': False})
    Bookmark.objects.create(vc=vc, startup=startup, by='startup')
    return Response({'bookmarked': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def bookmark_list(request):
    vc = _get_vc(request.user)
    if vc:
        ids = Bookmark.objects.filter(vc=vc, by='vc').values_list('startup_id', flat=True)
        qs = StartupProfile.objects.filter(id__in=ids)
        return Response({'role': 'vc', 'results': StartupProfileSerializer(qs, many=True).data})
    startup = _get_startup(request.user)
    if startup:
        ids = Bookmark.objects.filter(startup=startup, by='startup').values_list('vc_id', flat=True)
        qs = VCProfile.objects.filter(id__in=ids)
        return Response({'role': 'startup', 'results': [_vc_brief(v) for v in qs]})
    return Response({'role': None, 'results': []})


# ---------------- 좋아요 / 매칭 ----------------
def _ensure_match_if_mutual(vc, startup):
    """양방향 좋아요가 이미 존재하면 누락된 Match를 복구해 반환한다."""
    directions = set(Like.objects.filter(
        vc=vc, startup=startup,
    ).values_list('by', flat=True))
    if {'vc', 'startup'}.issubset(directions):
        match, _ = Match.objects.get_or_create(vc=vc, startup=startup)
        return match
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def like_startup(request, startup_id):
    vc = _get_vc(request.user)
    if not vc:
        return Response({'error': 'VC 프로필을 먼저 등록해주세요.'}, status=400)
    startup = StartupProfile.objects.filter(id=startup_id).first()
    if not startup:
        return Response({'error': '스타트업을 찾을 수 없습니다.'}, status=404)
    existing_match = (Match.objects.filter(vc=vc, startup=startup).first()
                      or _ensure_match_if_mutual(vc, startup))
    if existing_match:
        return Response({
            'liked': True, 'matched': True,
            'match_id': existing_match.id, 'match_status': existing_match.status,
        })
    obj = Like.objects.filter(vc=vc, startup=startup, by='vc').first()
    if obj:
        obj.delete()
        return Response({'liked': False, 'matched': False})
    Like.objects.get_or_create(vc=vc, startup=startup, by='vc')
    _notify(startup.user, f'💜 {vc.firm_name}님이 회원님의 스타트업에 좋아요를 보냈습니다!',
            startup=startup, vc=vc)
    matched = Like.objects.filter(vc=vc, startup=startup, by='startup').exists()
    match = None
    if matched:
        match, created = Match.objects.get_or_create(vc=vc, startup=startup)
        # AI 리포트는 매칭 상세를 열 때 생성(좋아요 응답을 막지 않도록 동기 생성 제거)
        if created:
            _notify(startup.user, f'💕 매칭 성사! {vc.firm_name}와(과) 서로 좋아요했습니다.', startup, vc)
            _notify(vc.user, f'💕 매칭 성사! {startup.name}와(과) 서로 좋아요했습니다.', startup, vc)
    return Response({
        'liked': True,
        'matched': matched,
        'awaiting_mutual_like': not matched,
        'match_id': match.id if match else None,
        'match_status': match.status if match else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def like_vc(request, vc_id):
    startup = _get_startup(request.user)
    if not startup:
        return Response({'error': '스타트업 프로필을 먼저 등록해주세요.'}, status=400)
    vc = VCProfile.objects.filter(id=vc_id).first()
    if not vc:
        return Response({'error': 'VC를 찾을 수 없습니다.'}, status=404)
    existing_match = (Match.objects.filter(vc=vc, startup=startup).first()
                      or _ensure_match_if_mutual(vc, startup))
    if existing_match:
        return Response({
            'liked': True, 'matched': True,
            'match_id': existing_match.id, 'match_status': existing_match.status,
        })
    obj = Like.objects.filter(vc=vc, startup=startup, by='startup').first()
    if obj:
        obj.delete()
        return Response({'liked': False, 'matched': False})
    Like.objects.get_or_create(vc=vc, startup=startup, by='startup')
    _notify(vc.user, f'💜 {startup.name}님이 회원님(VC)에게 좋아요를 보냈습니다!', startup, vc)
    matched = Like.objects.filter(vc=vc, startup=startup, by='vc').exists()
    match = None
    if matched:
        match, created = Match.objects.get_or_create(vc=vc, startup=startup)
        # AI 리포트는 매칭 상세를 열 때 생성(좋아요 응답을 막지 않도록 동기 생성 제거)
        if created:
            _notify(vc.user, f'💕 매칭 성사! {startup.name}와(과) 서로 좋아요했습니다.', startup, vc)
            _notify(startup.user, f'💕 매칭 성사! {vc.firm_name}와(과) 서로 좋아요했습니다.', startup, vc)
    return Response({
        'liked': True,
        'matched': matched,
        'awaiting_mutual_like': not matched,
        'match_id': match.id if match else None,
        'match_status': match.status if match else None,
    })


# ---------------- IR Deck 업로드 + AI 요약 ----------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def upload_ir_deck(request):
    startup = _ensure_startup(request.user)
    f = request.FILES.get('ir_deck')
    if not f:
        return Response({'error': 'ir_deck 파일이 필요합니다.'}, status=400)
    if not f.name.lower().endswith('.pdf'):
        return Response({'error': 'PDF 파일만 업로드 가능합니다.'}, status=400)
    startup.ir_deck = f             # 대표(최신) 포인터
    with transaction.atomic():
        startup.save()
        deck = IRDeck.objects.create(startup=startup, file=f)  # 정규화 1:N 이력
    text = ''
    try:
        from pypdf import PdfReader
        startup.ir_deck.open('rb')
        reader = PdfReader(startup.ir_deck)
        text = '\n'.join((p.extract_text() or '') for p in reader.pages)
    except Exception:
        text = ''
    finally:
        try:
            startup.ir_deck.close()
        except Exception:
            pass
    from .ai import summarize_ir_deck
    summary, source = summarize_ir_deck(text)
    startup.ir_summary = summary
    startup.ir_summary_status = 'draft'   # 창업자 검수 전 초안
    startup.save()
    return Response({'ir_deck': _ir_download_url(request, deck.id),
                     'ir_deck_id': deck.id,
                     'ir_summary': summary, 'ir_summary_status': 'draft', 'source': source})


# ---------------- IR Deck 다운로드(권한 게이트) ----------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def ir_deck_download(request, deck_id):
    """
    IR 원본 PDF 다운로드. 공개 /media/ 대신 이 엔드포인트로만 제공한다.
    소유자 또는 (매칭+양측 NDA 동의) VC 에게만 파일을 스트리밍한다.
    """
    deck = IRDeck.objects.filter(id=deck_id).select_related('startup', 'startup__user').first()
    if not deck:
        raise Http404
    if not _can_access_ir(request.user, deck.startup):
        return Response({'error': 'IR 원본 접근 권한이 없습니다. (매칭 후 양측 NDA 동의 필요)'},
                        status=403)
    try:
        f = deck.file.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404
    resp = FileResponse(f, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="ir_deck_{deck.id}.pdf"'
    return resp


# ---------------- 알림 ----------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def notification_list(request):
    notis = Notification.objects.filter(recipient=request.user)
    data = []
    for n in notis:
        if '커피챗' in n.message:
            kind = 'coffeechat'
        elif '매칭' in n.message:
            kind = 'match'
        else:
            kind = 'like'
        data.append({
            'id': n.id, 'message': n.message, 'startup_id': n.link_startup_id,
            'vc_id': n.link_vc_id, 'is_read': n.is_read, 'created_at': n.created_at,
            'kind': kind,
        })
    return Response({'unread': sum(1 for d in data if not d['is_read']), 'results': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def mark_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({'ok': True})


# ==================== Post-Match: 매칭 워크플로우 ====================
def _my_role(user, match):
    if match.vc and match.vc.user_id == user.id:
        return 'vc'
    if match.startup and match.startup.user_id == user.id:
        return 'startup'
    return None


def _match_payload(match, user, request=None):
    role = _my_role(user, match)
    i_agreed = bool(match.vc_nda_agreed_at) if role == 'vc' else bool(match.startup_nda_agreed_at)
    data = {
        'id': match.id,
        'status': match.status,
        'requested_by': match.requested_by,
        'my_role': role,
        'vc': _vc_brief(match.vc),
        'startup': StartupProfileSerializer(match.startup, context={'request': request}).data,
        'nda': {
            'vc_agreed': bool(match.vc_nda_agreed_at),
            'startup_agreed': bool(match.startup_nda_agreed_at),
            'i_agreed': i_agreed,
        },
        'can_request': match.status == 'matched',
        'can_accept': match.status == 'requested' and match.requested_by != role,
        'waiting': match.status == 'requested' and match.requested_by == role,
        'unlocked': match.status == 'accepted',
    }
    # 잠금 해제(수락 완료) 시에만 민감 정보 공개
    if match.status == 'accepted':
        vu, su = match.vc.user, match.startup.user
        # 전화번호는 노출하지 않는다(이메일만 공개).
        data['contact'] = {
            'vc_email': getattr(vu, 'email', ''),
            'startup_email': getattr(su, 'email', ''),
        }
        data['my_briefing'] = match.briefing_vc if role == 'vc' else match.briefing_startup
    # 커피챗(1:1 대화/일정) 진입을 위한 상대 계정 id — 매칭 페이지에서 바로 채팅을 열 때 사용
    cp = match.startup.user if role == 'vc' else (match.vc.user if match.vc else None)
    data['counterpart_user_id'] = cp.id if cp else None
    # IR 원본은 '양측 NDA 동의' 시에만, 그것도 원본 URL 이 아닌 게이트된 다운로드 경로로 제공.
    if match.both_nda_agreed and role == 'vc':
        data['ir_decks'] = [
            {'id': d.id, 'uploaded_at': d.uploaded_at,
             'download_url': _ir_download_url(request, d.id)}
            for d in match.startup.ir_decks.all()
        ]
    # 블라인드 단계: 요약은 '승인+공개'된 경우에만 노출
    shared = (match.startup.ir_summary_status == 'approved' and match.startup.ir_summary_public)
    data['ir_summary'] = match.startup.ir_summary if (shared or match.status == 'accepted') else ''
    data['summary_shared'] = shared
    return data


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def matches_list(request):
    vc = _get_vc(request.user)
    startup = _get_startup(request.user)
    if vc:
        mutual_ids = Like.objects.filter(vc=vc).values('startup_id').annotate(
            directions=models.Count('by', distinct=True),
        ).filter(directions=2).values_list('startup_id', flat=True)
        for startup_obj in StartupProfile.objects.filter(id__in=mutual_ids):
            Match.objects.get_or_create(vc=vc, startup=startup_obj)
        qs = Match.objects.filter(vc=vc)
    elif startup:
        mutual_ids = Like.objects.filter(startup=startup).values('vc_id').annotate(
            directions=models.Count('by', distinct=True),
        ).filter(directions=2).values_list('vc_id', flat=True)
        for vc_obj in VCProfile.objects.filter(id__in=mutual_ids):
            Match.objects.get_or_create(vc=vc_obj, startup=startup)
        qs = Match.objects.filter(startup=startup)
    else:
        return Response([])
    return Response([_match_payload(m, request.user, request) for m in qs])


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_get(request, match_id):
    m = Match.objects.filter(id=match_id).first()
    if not m or _my_role(request.user, m) is None:
        return Response({'error': '매칭을 찾을 수 없습니다.'}, status=404)
    return Response(_match_payload(m, request.user, request))


def _set_nda(match, role):
    now = timezone.now()
    if role == 'vc':
        match.vc_nda_agreed_at = match.vc_nda_agreed_at or now
    else:
        match.startup_nda_agreed_at = match.startup_nda_agreed_at or now


def _ensure_match_coffeechat(match, requester):
    """매칭의 '커피챗 요청' 시 커피챗 탭에 노출될 CoffeeChat(PENDING) 1개를 보장한다.
    요청자(requester)를 sender, 상대를 receiver 로 둔다. 이미 있으면 재사용(중복 방지)."""
    vc_user = match.vc.user if match.vc else None
    su_user = match.startup.user if match.startup else None
    if not (vc_user and su_user):
        return None
    other = su_user if requester.id == vc_user.id else vc_user
    existing = CoffeeChat.objects.filter(
        Q(sender=requester, receiver=other) | Q(sender=other, receiver=requester)
    ).order_by('-created_at').first()
    if existing:
        return existing
    who = match.vc.firm_name if requester.id == vc_user.id else match.startup.name
    return CoffeeChat.objects.create(
        sender=requester, receiver=other,
        message=f'{who}님이 커피챗을 요청했습니다. 채팅 후 일정을 확정해보세요!',
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_request(request, match_id):
    """커피챗/미팅 요청 + NDA 동의. status → requested.
    동시에 커피챗 탭에 보일 CoffeeChat(보낸 제안/받은 제안)을 생성한다."""
    m = Match.objects.filter(id=match_id).first()
    role = _my_role(request.user, m) if m else None
    if not role:
        return Response({'error': '매칭을 찾을 수 없습니다.'}, status=404)
    if not request.data.get('nda_agreed'):
        return Response({'error': 'NDA 동의가 필요합니다.'}, status=400)
    if m.status not in ('matched',):
        return Response({'error': '이미 요청되었거나 진행된 매칭입니다.'}, status=400)
    m.status = 'requested'
    m.requested_by = role
    _set_nda(m, role)
    m.save()
    _ensure_match_coffeechat(m, request.user)   # 커피챗 탭 노출용 스레드 보장
    counterpart = m.startup.user if role == 'vc' else m.vc.user
    who = m.vc.firm_name if role == 'vc' else m.startup.name
    _notify(counterpart, f'{who}님이 커피챗을 요청했습니다. (NDA 동의 후 수락하면 연락처가 공개됩니다)',
            m.startup, m.vc)
    return Response(_match_payload(m, request.user, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_accept(request, match_id):
    """요청 수락 + NDA 동의. 양측 동의 시 status → accepted, 브리핑 생성."""
    m = Match.objects.filter(id=match_id).first()
    role = _my_role(request.user, m) if m else None
    if not role:
        return Response({'error': '매칭을 찾을 수 없습니다.'}, status=404)
    if m.status != 'requested' or m.requested_by == role:
        return Response({'error': '수락할 수 있는 상태가 아닙니다.'}, status=400)
    if not request.data.get('nda_agreed'):
        return Response({'error': 'NDA 동의가 필요합니다.'}, status=400)
    _set_nda(m, role)
    if m.both_nda_agreed:
        m.status = 'accepted'
        _ensure_match_coffeechat(m, request.user)   # 요청 단계 누락 대비 보장
        # AI 미팅 브리핑 1회 생성
        score, sub, _ = calculate_recommendation(m.vc, m.startup)
        from .ai import generate_meeting_briefings
        bv, bs, src = generate_meeting_briefings(m.vc, m.startup, score, sub)
        m.briefing_vc, m.briefing_startup, m.briefing_source = bv, bs, src
    m.save()
    counterpart = m.startup.user if role == 'vc' else m.vc.user
    _notify(counterpart, '커피챗 요청이 수락되었습니다! 연락처와 AI 미팅 브리핑이 공개되었습니다.',
            m.startup, m.vc)
    return Response(_match_payload(m, request.user, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_decline(request, match_id):
    m = Match.objects.filter(id=match_id).first()
    role = _my_role(request.user, m) if m else None
    if not role:
        return Response({'error': '매칭을 찾을 수 없습니다.'}, status=404)
    m.status = 'declined'
    m.save()
    return Response(_match_payload(m, request.user, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def match_coffeechat(request, match_id):
    """매칭 상대와의 커피챗 스레드를 찾거나(없으면 새로 생성) 그 id를 반환한다.
    매칭 페이지에서 '커피챗/채팅 열기' 한 번으로 1:1 대화·일정 기능에 진입하기 위한 단일 진입점.
    (기존엔 AI리포트 상세의 INTRO 버튼으로만 생성돼, 매칭만 한 사용자는 커피챗 목록이 비어 보였음)"""
    m = Match.objects.filter(id=match_id).first()
    role = _my_role(request.user, m) if m else None
    if not role:
        return Response({'error': '매칭을 찾을 수 없습니다.'}, status=404)
    counterpart = m.startup.user if role == 'vc' else (m.vc.user if m.vc else None)
    if not counterpart:
        return Response({'error': '상대 계정을 찾을 수 없습니다.'}, status=404)
    if counterpart.id == request.user.id:
        return Response({'error': '자기 자신과는 커피챗을 열 수 없습니다.'}, status=400)

    # 이미 어느 방향으로든 커피챗이 있으면 재사용해 중복 스레드를 막는다.
    existing = CoffeeChat.objects.filter(
        Q(sender=request.user, receiver=counterpart)
        | Q(sender=counterpart, receiver=request.user)
    ).order_by('-created_at').first()
    if existing:
        return Response({'coffeechat_id': existing.id, 'created': False})

    who = m.vc.firm_name if role == 'vc' else m.startup.name
    cc = CoffeeChat.objects.create(
        sender=request.user,
        receiver=counterpart,
        message=f'{who}님이 커피챗을 시작했습니다. 편하신 시간을 알려주세요!',
    )
    Notification.objects.create(
        recipient=counterpart,
        message=f'☕ {request.user.username}님이 커피챗을 시작했습니다.',
    )
    return Response({'coffeechat_id': cc.id, 'created': True}, status=201)


# ==================== 피치덱 / IR 요약 검수 / VC 요약 / 분석 ====================
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def upload_pitch_deck(request):
    """피치덱(필수·공개) PDF 업로드. 프로필이 없으면 PDF 등록과 동시에 생성."""
    startup = _ensure_startup(request.user)
    f = request.FILES.get('pitch_deck')
    if not f:
        return Response({'error': 'pitch_deck 파일이 필요합니다.'}, status=400)
    if not f.name.lower().endswith('.pdf'):
        return Response({'error': 'PDF 파일만 업로드 가능합니다.'}, status=400)
    startup.pitch_deck = f          # 대표(최신) 포인터
    startup.save()
    deck = PitchDeck.objects.create(startup=startup, file=f)  # 정규화 1:N 이력
    return Response({'pitch_deck': startup.pitch_deck.url,
                     'pitch_deck_id': deck.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def approve_ir_summary(request):
    """창업자가 IR 요약 초안을 검수 후 승인 + 공개여부 설정."""
    startup = _get_startup(request.user)
    if not startup:
        return Response({'error': '스타트업 프로필을 먼저 등록해주세요.'}, status=400)
    # 본문으로 수정된 요약을 함께 받을 수 있음(검수 반영)
    edited = request.data.get('ir_summary')
    if edited is not None:
        startup.ir_summary = edited
    startup.ir_summary_status = 'approved'
    if 'ir_summary_public' in request.data:
        startup.ir_summary_public = bool(request.data.get('ir_summary_public'))
    startup.save()
    return Response({'ir_summary': startup.ir_summary,
                     'ir_summary_status': startup.ir_summary_status,
                     'ir_summary_public': startup.ir_summary_public})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def generate_vc_summary_view(request):
    """VC 프로필을 AI로 요약 생성(검수용 초안). 이후 PUT 으로 수정 가능."""
    vc = _get_vc(request.user)
    if not vc:
        return Response({'error': 'VC 프로필을 먼저 등록해주세요.'}, status=400)
    from .ai import generate_vc_summary
    text, source = generate_vc_summary(vc)
    vc.vc_summary = text
    vc.save()
    return Response({'vc_summary': text, 'source': source})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def analytics(request):
    """요약 기능 효과 측정 대시보드: 열람률·매칭률 비교."""
    total = StartupProfile.objects.count()
    with_summary = StartupProfile.objects.filter(
        ir_summary_status='approved', ir_summary_public=True)
    n_with = with_summary.count()
    n_without = total - n_with

    # 매칭(상호 좋아요로 생성된 Match) 보유 스타트업 집계
    matched_ids = set(Match.objects.values_list('startup_id', flat=True))
    matched_with = sum(1 for s in with_summary if s.id in matched_ids)
    matched_without = sum(1 for s in StartupProfile.objects.exclude(
        id__in=with_summary.values_list('id', flat=True)) if s.id in matched_ids)

    def rate(n, d):
        return round(n / d * 100, 1) if d else 0.0

    total_views = sum(with_summary.values_list('summary_view_count', flat=True))
    accepted = Match.objects.filter(status='accepted').count()

    return Response({
        'startups_total': total,
        'with_public_summary': n_with,
        'without_public_summary': n_without,
        'summary_view_total': total_views,
        # 매칭률(매칭 보유 스타트업 비율) — 요약 공개 vs 비공개
        'match_rate_with_summary': rate(matched_with, n_with),
        'match_rate_without_summary': rate(matched_without, n_without),
        'matches_total': len(matched_ids),
        'meetings_accepted': accepted,
        'note': '요약 공개군의 매칭률이 비공개군보다 높으면 기능 강화, 낮으면 단계적 축소 판단.',
    })


# ==================== VC 스타트업 찾기(선호조건 검색) ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def startup_search(request):
    """
    VC가 입력한 선호 조건으로 스타트업 검색.
    점수: 산업 30 + 지역 20 + 투자금 범위 30 + 학력 20 = 100.
    산업은 1차 필터(선택 시 해당 산업만), 나머지는 가점.
    """
    vc = _get_vc(request.user)
    q = request.query_params

    def _list(name):
        raw = q.get(name) or ''
        return [x for x in (v.strip() for v in raw.split(',')) if x]

    industries = _list('industry')
    regions = _list('region')
    edus = _list('founder_education')

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0
    mn, mx = _int(q.get('min_investment')), _int(q.get('max_investment'))

    # 쿼리 파라미터가 없으면(= 선호도 조사 페이지를 거치지 않고 바로 진입)
    # VC가 프로필에 저장한 선호조건을 사용한다.
    if vc and not (industries or regions or edus or mn or mx):
        industries = vc.preferred_industries or []
        regions = vc.preferred_regions or []
        edus = vc.preferred_education or []
        mn, mx = vc.min_investment or 0, vc.max_investment or 0

    qs = StartupProfile.objects.all()
    # 'All'(전 산업) 선호면 산업 필터 없이 전체 노출
    if industries and 'All' not in industries:
        # 선택 산업과 일치 + 신규(빈 산업) + 비표준 산업(한글 등 실데이터)은 항상 노출
        STANDARD = {'SaaS', 'Fintech', 'Healthcare', 'AI/ML', 'E-commerce',
                    'EdTech', 'Bio', 'Gaming', 'Mobility', 'Other'}
        qs = qs.filter(
            Q(industry__in=industries) | Q(industry='') | Q(industry__isnull=True)
            | ~Q(industry__in=STANDARD)
        )

    lk = set(Like.objects.filter(vc=vc, by='vc').values_list('startup_id', flat=True)) if vc else set()
    bk = set(Bookmark.objects.filter(vc=vc, by='vc').values_list('startup_id', flat=True)) if vc else set()
    matched_ids = set(Match.objects.filter(vc=vc).values_list('startup_id', flat=True)) if vc else set()
    vc_groups_set = vc_groups(vc.preferred_industries) if vc else set()

    out = []
    for s in qs:
        is_new = not (s.industry or '').strip()  # 정형 데이터 없는 신규 등록 스타트업
        score = 0
        if industries and s.industry in industries:
            score += 30
        if regions and s.region in regions:
            score += 20
        if mx and (mn <= s.funding_needed <= mx):
            score += 30
        if (not edus) or ('무관' in edus) or (s.founder_education in edus):
            score += 20
        d = StartupProfileSerializer(s, context={'request': request}).data
        # 매칭 전: IR 원본·민감 재무지표 비노출 + 점수 비노출
        for f in ('ir_deck', 'ir_deck_url', 'cac', 'ltv', 'burn_rate', 'runway_months', 'equity_structure'):
            d.pop(f, None)
        d['is_new'] = is_new
        d['_rank'] = score
        d['is_liked'] = s.id in lk or s.id in matched_ids
        d['is_bookmarked'] = s.id in bk
        d['is_matched'] = s.id in matched_ids
        d['summary'] = s.summary or ''
        # 산업군 분류 + 이 VC의 관심 산업군 여부
        g = classify_startup(s.industry, s.description)
        d['industry_group'] = g
        d['industry_group_label'] = group_label(g)
        d['vc_interested'] = g in vc_groups_set
        out.append(d)
    # 관심 산업군 → 신규 → 적합도 순으로 정렬(관심 산업군 섹션이 위로 떠오름)
    out.sort(key=lambda x: (x['vc_interested'], x['is_new'], x['_rank'], x['id']), reverse=True)
    for d in out:
        d.pop('_rank', None)
    return Response(out)


# ==================== 포트폴리오 자료(VCProfile 1:N) ====================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def portfolio_documents(request):
    """VC 포트폴리오 자료 목록/업로드. 업로드 시 프로필이 없으면 생성."""
    if request.method == 'GET':
        vc = _get_vc(request.user)
        if not vc:
            return Response([])
        qs = vc.portfolio_documents.all()
        return Response(PortfolioDocumentSerializer(
            qs, many=True, context={'request': request}).data)
    vc = _ensure_vc(request.user)
    f = request.FILES.get('file')
    if not f:
        return Response({'error': 'file 파일이 필요합니다.'}, status=400)
    doc = PortfolioDocument.objects.create(
        vc=vc, file=f, title=request.data.get('title', ''))
    return Response(PortfolioDocumentSerializer(
        doc, context={'request': request}).data, status=201)


# ==================== AI 리포트(Match 1:1) ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
@throttle_classes([AIRateThrottle])
def ai_report(request, match_id):
    """매칭에 대한 AI 리포트(FIT 점수 + 요약). 없으면 최초 생성."""
    m = Match.objects.filter(id=match_id).first()
    if not m or _my_role(request.user, m) is None:
        return Response({'error': '매칭을 찾을 수 없습니다.'}, status=404)
    force = request.query_params.get('refresh') in ('1', 'true', 'yes')
    report = ensure_ai_report(m, request, force=force)
    return Response({
        'match_id': m.id,
        'fit_score': report.fit_score,
        'summary': report.summary,
        'source': report.source,
        'created_at': report.created_at,
        'report': report.report_json,
    })


# ==================== 커피챗(1:1 네트워킹) ====================
def _users_have_match(sender, receiver):
    """두 계정이 VC↔스타트업 상호 매칭 관계인지 확인한다."""
    if sender.role == 'vc' and receiver.role == 'startup':
        vc, startup = _get_vc(sender), _get_startup(receiver)
    elif sender.role == 'startup' and receiver.role == 'vc':
        vc, startup = _get_vc(receiver), _get_startup(sender)
    else:
        return False
    return bool(vc and startup and Match.objects.filter(vc=vc, startup=startup).exists())


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def coffeechat_request(request):
    """상호 매칭된 상대에게 텍스트 커피챗 제안을 보낸다."""
    receiver_id = request.data.get('receiver_id')
    message = str(request.data.get('message') or '').strip()
    if not receiver_id:
        return Response({'error': '받는 사람을 지정해주세요.'}, status=400)
    try:
        receiver_id = int(receiver_id)
    except (TypeError, ValueError):
        return Response({'error': '받는 사람 ID가 올바르지 않습니다.'}, status=400)
    if not message:
        return Response({'error': '제안 메시지를 입력해주세요.'}, status=400)
    if len(message) > 2000:
        return Response({'error': '메시지는 2,000자 이하로 입력해주세요.'}, status=400)

    User = get_user_model()
    receiver = User.objects.filter(id=receiver_id).first()
    if not receiver:
        return Response({'error': '받는 사용자를 찾을 수 없습니다.'}, status=404)
    if receiver.id == request.user.id:
        return Response({'error': '자기 자신에게는 커피챗을 제안할 수 없습니다.'}, status=400)
    if not _users_have_match(request.user, receiver):
        return Response({'error': '상호 매칭된 상대에게만 커피챗을 제안할 수 있습니다.'}, status=403)
    if CoffeeChat.objects.filter(
        sender=request.user,
        receiver=receiver,
        status=CoffeeChat.STATUS_PENDING,
    ).exists():
        return Response({'error': '이미 답변을 기다리는 커피챗 제안이 있습니다.'}, status=409)

    try:
        coffeechat = CoffeeChat.objects.create(
            sender=request.user,
            receiver=receiver,
            message=message,
        )
    except IntegrityError:
        return Response({'error': '이미 답변을 기다리는 커피챗 제안이 있습니다.'}, status=409)
    Notification.objects.create(
        recipient=receiver,
        message=f'☕ {request.user.username}님이 커피챗을 제안했습니다.',
    )
    return Response(
        CoffeeChatSerializer(coffeechat, context={'request': request}).data,
        status=201,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def coffeechat_my_requests(request):
    """내가 보내거나 받은 커피챗 제안을 최신순으로 반환한다."""
    coffeechats = CoffeeChat.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver').order_by('-created_at')
    return Response(CoffeeChatSerializer(
        coffeechats,
        many=True,
        context={'request': request},
    ).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def coffeechat_respond(request, pk):
    """미팅 일정 제안/확정/거절.
    - propose : 요청 받은 쪽(receiver)이 일정을 '제안'한다(확정 대기 = meeting_at 세팅 + PENDING 유지).
    - confirm : 요청 보낸 쪽(sender)이 제안된 일정을 '확정'한다(ACCEPTED).
    - reject  : 요청 보낸 쪽(sender)이 제안된 일정을 '거절'한다(일정 비우고 다시 조율).
    """
    cc = CoffeeChat.objects.filter(id=pk).first()
    if not cc:
        return Response({'error': '커피챗을 찾을 수 없습니다.'}, status=404)
    uid = request.user.id
    if uid not in (cc.sender_id, cc.receiver_id):
        return Response({'error': '이 대화의 참여자가 아닙니다.'}, status=403)
    if cc.is_locked():
        return Response({'error': '먼저 매칭에서 커피챗 요청을 수락해주세요.'}, status=403)

    action = request.data.get('action')

    # ---- 일정 제안: 요청 받은 쪽만 ----
    if action == 'propose':
        if uid != cc.receiver_id:
            return Response({'error': '일정 제안은 요청 받은 쪽만 할 수 있습니다.'}, status=403)
        mtype = request.data.get('meeting_type')
        if mtype not in ('online', 'offline'):
            return Response({'error': '온라인/오프라인을 선택해주세요.'}, status=400)
        raw_at = request.data.get('meeting_at')
        if not raw_at:
            return Response({'error': '미팅 날짜와 시간을 선택해주세요.'}, status=400)
        dt = parse_datetime(raw_at)
        if dt is None:
            return Response({'error': '날짜/시간 형식이 올바르지 않습니다.'}, status=400)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        cc.meeting_type = mtype
        cc.meeting_at = dt
        cc.meeting_location = str(request.data.get('meeting_location') or '').strip()
        cc.reply_message = str(request.data.get('reply_message') or '').strip()
        cc.status = CoffeeChat.STATUS_PENDING   # 제안됨, 확정 대기
        cc.responded_at = timezone.now()
        cc.save()
        when = timezone.localtime(dt).strftime('%Y-%m-%d %H:%M')
        label = '온라인' if mtype == 'online' else '오프라인'
        Notification.objects.create(
            recipient=cc.sender,
            message=f'📅 {request.user.username}님이 미팅 일정을 제안했습니다. ({label} · {when}) 수락/거절해주세요.',
        )
        return Response(CoffeeChatSerializer(cc, context={'request': request}).data)

    # ---- 제안 확정: 요청 보낸 쪽만 ----
    if action == 'confirm':
        if uid != cc.sender_id:
            return Response({'error': '제안된 일정은 요청한 쪽이 확정합니다.'}, status=403)
        if not cc.meeting_at:
            return Response({'error': '확정할 제안된 일정이 없습니다.'}, status=400)
        cc.status = CoffeeChat.STATUS_ACCEPTED
        cc.save()
        when = timezone.localtime(cc.meeting_at).strftime('%Y-%m-%d %H:%M')
        Notification.objects.create(
            recipient=cc.receiver,
            message=f'✅ {request.user.username}님이 미팅 일정을 확정했습니다! ({when})',
        )
        return Response(CoffeeChatSerializer(cc, context={'request': request}).data)

    # ---- 제안 거절: 요청 보낸 쪽만 (일정 초기화 → 다시 채팅으로 조율) ----
    if action == 'reject':
        if uid != cc.sender_id:
            return Response({'error': '제안된 일정은 요청한 쪽이 거절합니다.'}, status=403)
        if not cc.meeting_at:
            return Response({'error': '거절할 제안된 일정이 없습니다.'}, status=400)
        cc.meeting_type = ''
        cc.meeting_at = None
        cc.meeting_location = ''
        cc.status = CoffeeChat.STATUS_PENDING
        cc.save()
        Notification.objects.create(
            recipient=cc.receiver,
            message=f'🙅 {request.user.username}님이 제안한 일정을 거절했습니다. 채팅으로 다시 조율해주세요.',
        )
        return Response(CoffeeChatSerializer(cc, context={'request': request}).data)

    return Response({'error': 'action 은 propose / confirm / reject 중 하나여야 합니다.'}, status=400)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def coffeechat_messages(request, pk):
    """커피챗 스레드의 채팅 메시지 목록 조회 / 전송. 양측(sender·receiver)만 접근."""
    cc = CoffeeChat.objects.filter(id=pk).first()
    if not cc:
        return Response({'error': '커피챗을 찾을 수 없습니다.'}, status=404)
    uid = request.user.id
    if uid not in (cc.sender_id, cc.receiver_id):
        return Response({'error': '이 대화의 참여자가 아닙니다.'}, status=403)

    if request.method == 'POST':
        if cc.is_locked():
            return Response(
                {'error': '아직 수락되지 않은 커피챗입니다. 매칭에서 요청을 수락하면 채팅이 시작됩니다.'},
                status=403,
            )
        text = str(request.data.get('text') or '').strip()
        if not text:
            return Response({'error': '메시지를 입력해주세요.'}, status=400)
        msg = ChatMessage.objects.create(coffeechat=cc, sender=request.user, text=text)
        other_id = cc.receiver_id if uid == cc.sender_id else cc.sender_id
        Notification.objects.create(
            recipient_id=other_id,
            message=f'💬 {request.user.username}님이 메시지를 보냈습니다.',
        )
        return Response(_chat_msg(msg, request), status=201)

    msgs = cc.messages.select_related('sender').all()
    other = cc.receiver if uid == cc.sender_id else cc.sender
    return Response({
        'coffeechat': CoffeeChatSerializer(cc, context={'request': request}).data,
        'partner_name': other.username,
        'messages': [_chat_msg(m, request) for m in msgs],
    })


def _chat_msg(m, request):
    return {
        'id': m.id, 'text': m.text, 'sender': m.sender.username,
        'is_mine': m.sender_id == request.user.id, 'created_at': m.created_at,
    }


# ==================== 프로필 등록 상태(PDF 등록 완료 여부) ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def profile_status(request):
    """
    프로필 등록 완료 여부. 프론트 등록 화면이 어떤 PDF가 올라갔는지 표시하는 데 사용.
    - 스타트업: 피치덱 + IR덱 모두 등록 시 완료
    - VC: 포트폴리오 1건 이상 등록 시 완료
    """
    role = getattr(request.user, 'role', None)
    if role == 'startup':
        sp = _get_startup(request.user)
        return Response({
            'role': 'startup',
            'pitch_uploaded': bool(sp and sp.pitch_decks.exists()),
            'ir_uploaded': bool(sp and sp.ir_decks.exists()),
            'registered': _startup_registered(sp),
        })
    if role == 'vc':
        vc = _get_vc(request.user)
        docs = vc.portfolio_documents.count() if vc else 0
        return Response({
            'role': 'vc',
            'portfolio_count': docs,
            'registered': _vc_registered(vc),
        })
    return Response({'role': role, 'registered': False})
