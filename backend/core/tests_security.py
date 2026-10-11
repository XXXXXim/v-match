"""
보안 회귀 테스트.

리뷰에서 '반드시 수정'으로 지목된 결함을 재현/검증한다.
  1) NDA 동의 전 IR 원본(file url) 노출
  2) 이메일 미인증 사용자의 보호 API 접근
  3) 반대 역할 프로필 자동 생성
  4) IR 다운로드 권한(소유자/매칭+양측 NDA) 검사
"""
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import IRDeck, Match, StartupProfile, VCProfile

User = get_user_model()

# 가장 작은 유효 PDF (헤더만 있어도 .pdf 업로드 통과)
PDF_BYTES = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def make_user(username, role, *, verified=True, password='Str0ng-pass-12!'):
    u = User.objects.create_user(
        username=username, password=password,
        email=f'{username}@ex.com', role=role,
    )
    u.email_verified = verified
    u.save(update_fields=['email_verified'])
    return u


def auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def body_text(resp):
    return json.dumps(resp.json(), ensure_ascii=False)


class IRExposureTests(TestCase):
    """NDA 동의 전에는 IR 원본 파일 URL이 어떤 응답에도 나오면 안 된다."""

    def setUp(self):
        self.su_user = make_user('founder', 'startup')
        self.startup = StartupProfile.objects.create(
            user=self.su_user, name='딥테크', industry='AI/ML',
            stage='Seed', region='서울')
        # IR 덱 이력 2건(과거 이력 포함) 업로드
        for i in range(2):
            IRDeck.objects.create(
                startup=self.startup,
                file=SimpleUploadedFile(f'ir_v{i}.pdf', PDF_BYTES,
                                        content_type='application/pdf'))
        self.startup.ir_deck = self.startup.ir_decks.first().file
        self.startup.save(update_fields=['ir_deck'])

        self.vc_user = make_user('investor', 'vc')
        self.vc = VCProfile.objects.create(user=self.vc_user, firm_name='알파캐피탈')

    def _assert_no_ir_url(self, resp, where):
        self.assertEqual(resp.status_code, 200, where)
        self.assertNotIn('/media/ir_decks/', body_text(resp),
                         f'{where}: IR 원본 URL이 노출됨')
        self.assertNotIn('ir_v0.pdf', body_text(resp),
                         f'{where}: IR 파일명이 노출됨')

    def test_recommendations_hide_ir(self):
        self._assert_no_ir_url(auth(self.vc_user).get('/api/recommendations/'),
                               'recommendations')

    def test_startup_search_hide_ir(self):
        self._assert_no_ir_url(auth(self.vc_user).get('/api/startup-search/'),
                               'startup-search')

    def test_startup_list_hide_ir(self):
        self._assert_no_ir_url(auth(self.vc_user).get('/api/startups/'),
                               'startups')

    def test_match_detail_pre_nda_hide_ir(self):
        Match.objects.create(vc=self.vc, startup=self.startup, status='matched')
        self._assert_no_ir_url(
            auth(self.vc_user).get(f'/api/match-detail/startup/{self.startup.id}/'),
            'match-detail')


class IRDownloadGateTests(TestCase):
    """전용 IR 다운로드는 소유자 또는 (매칭+양측 NDA) VC 에게만 허용."""

    def setUp(self):
        self.su_user = make_user('founder2', 'startup')
        self.startup = StartupProfile.objects.create(
            user=self.su_user, name='로보틱스', industry='AI/ML',
            stage='A', region='서울')
        self.deck = IRDeck.objects.create(
            startup=self.startup,
            file=SimpleUploadedFile('secret.pdf', PDF_BYTES,
                                    content_type='application/pdf'))
        self.vc_user = make_user('investor2', 'vc')
        self.vc = VCProfile.objects.create(user=self.vc_user, firm_name='베타벤처스')

    def url(self):
        return f'/api/ir-decks/{self.deck.id}/download/'

    def test_anonymous_blocked(self):
        self.assertIn(APIClient().get(self.url()).status_code, (401, 403))

    def test_unrelated_vc_blocked(self):
        self.assertEqual(auth(self.vc_user).get(self.url()).status_code, 403)

    def test_matched_without_nda_blocked(self):
        Match.objects.create(vc=self.vc, startup=self.startup, status='matched')
        self.assertEqual(auth(self.vc_user).get(self.url()).status_code, 403)

    def test_matched_with_both_nda_allowed(self):
        now = timezone.now()
        Match.objects.create(vc=self.vc, startup=self.startup, status='accepted',
                             vc_nda_agreed_at=now, startup_nda_agreed_at=now)
        self.assertEqual(auth(self.vc_user).get(self.url()).status_code, 200)

    def test_owner_allowed(self):
        self.assertEqual(auth(self.su_user).get(self.url()).status_code, 200)


class EmailVerificationTests(TestCase):
    def test_unverified_blocked_on_protected_api(self):
        u = make_user('newbie', 'vc', verified=False)
        resp = auth(u).get('/api/recommendations/')
        self.assertEqual(resp.status_code, 403)

    def test_verified_allowed(self):
        u = make_user('verified_vc', 'vc', verified=True)
        VCProfile.objects.create(user=u, firm_name='감마')
        resp = auth(u).get('/api/recommendations/')
        self.assertEqual(resp.status_code, 200)


class RoleEnforcementTests(TestCase):
    def test_vc_cannot_create_startup_profile(self):
        u = make_user('vc_only', 'vc')
        resp = auth(u).post('/api/startup-profile/',
                            {'name': '가짜', 'industry': 'AI/ML',
                             'stage': 'Seed', 'region': '서울'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(StartupProfile.objects.filter(user=u).exists())

    def test_vc_cannot_autocreate_startup_via_pitch_upload(self):
        u = make_user('vc_only2', 'vc')
        resp = auth(u).post(
            '/api/startup-profile/pitch-deck/',
            {'pitch_deck': SimpleUploadedFile('p.pdf', PDF_BYTES,
                                              content_type='application/pdf')},
            format='multipart')
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(StartupProfile.objects.filter(user=u).exists())

    def test_startup_cannot_create_vc_profile(self):
        u = make_user('su_only', 'startup')
        resp = auth(u).post('/api/vc-profile/',
                            {'firm_name': '가짜캐피탈'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(VCProfile.objects.filter(user=u).exists())


class SignupSecurityTests(TestCase):
    @override_settings(DEBUG=False)
    def test_weak_password_rejected(self):
        c = APIClient()
        resp = c.post('/api/accounts/signup/',
                      {'username': 'weakguy', 'password': '123',
                       'email': 'weak@ex.com', 'role': 'vc',
                       'name': '위크', 'phone': '010-0000-0000'}, format='json')
        self.assertEqual(resp.status_code, 400)

    @override_settings(DEBUG=False)
    def test_signup_response_has_no_dev_code_in_prod(self):
        c = APIClient()
        resp = c.post('/api/accounts/signup/',
                      {'username': 'prodguy', 'password': 'Str0ng-pass-12!',
                       'email': 'prod@ex.com', 'role': 'vc',
                       'name': '프로드', 'phone': '010-0000-0000'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertNotIn('dev_code', resp.json())
