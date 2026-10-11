from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AIReport, CoffeeChat, Like, Match, StartupProfile, VCProfile
from .views import ensure_ai_report


class AIReportRegenerationTests(TestCase):
    def setUp(self):
        self.vc = VCProfile.objects.create(firm_name='테스트 VC')
        self.startup = StartupProfile.objects.create(
            name='테스트 스타트업', industry='AI', stage='Seed', region='서울')
        self.match = Match.objects.create(vc=self.vc, startup=self.startup)
        self.original_sections = [
            {'name': '창업자·팀', 'score': 4, 'comment': '기존 팀 평가'},
            {'name': 'VC 적합성', 'score': 3, 'comment': '기존 적합성 평가'},
        ]
        self.report = AIReport.objects.create(
            match=self.match,
            fit_score=77,
            summary='기존 요약',
            source='openai',
            report_json={
                'fit_score': 77,
                'recommendation': '조건부 투자 검토',
                'sections': self.original_sections,
            },
        )

    @patch('core.ai_report.generate_ai_report')
    def test_refresh_updates_language_but_locks_all_scores(self, generate):
        generate.return_value = (
            52,
            '새 요약',
            'openai',
            {
                'fit_score': 52,
                'recommendation': '신중 검토',
                'sections': [
                    {'name': '창업자·팀', 'score': 1, 'comment': '새 팀 코멘트'},
                    {'name': 'VC 적합성', 'score': 5, 'comment': '새 적합성 코멘트'},
                ],
                'strengths': ['새 강점'],
            },
        )

        refreshed = ensure_ai_report(self.match, force=True)

        self.assertEqual(refreshed.fit_score, 77)
        self.assertEqual(refreshed.summary, '새 요약')
        self.assertEqual(refreshed.report_json['fit_score'], 77)
        self.assertEqual(refreshed.report_json['recommendation'], '조건부 투자 검토')
        self.assertEqual(
            {s['name']: s['score'] for s in refreshed.report_json['sections']},
            {'창업자·팀': 4, 'VC 적합성': 3},
        )
        self.assertEqual(refreshed.report_json['sections'][0]['comment'], '새 팀 코멘트')

    @patch('core.ai_report.generate_ai_report', side_effect=RuntimeError('network'))
    def test_refresh_failure_keeps_existing_report(self, _generate):
        refreshed = ensure_ai_report(self.match, force=True)

        self.assertEqual(refreshed.pk, self.report.pk)
        self.assertEqual(refreshed.fit_score, 77)
        self.assertEqual(refreshed.summary, '기존 요약')
        self.assertEqual(refreshed.report_json['sections'], self.original_sections)


class CoffeeChatAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.vc_user = User.objects.create_user(
            username='vc-user', password='test-pass', role='vc', email_verified=True)
        self.startup_user = User.objects.create_user(
            username='startup-user', password='test-pass', role='startup', email_verified=True)
        self.other_user = User.objects.create_user(
            username='other-startup', password='test-pass', role='startup', email_verified=True)
        self.vc = VCProfile.objects.create(user=self.vc_user, firm_name='테스트 VC')
        self.startup = StartupProfile.objects.create(
            user=self.startup_user,
            name='테스트 스타트업', industry='AI', stage='Seed', region='서울')
        StartupProfile.objects.create(
            user=self.other_user,
            name='미매칭 스타트업', industry='SaaS', stage='Seed', region='서울')
        Match.objects.create(vc=self.vc, startup=self.startup)
        self.client = APIClient()

    def test_matched_user_can_send_and_list_text_coffeechat(self):
        self.client.force_authenticate(self.vc_user)
        response = self.client.post('/api/coffeechats/request/', {
            'receiver_id': self.startup_user.id,
            'message': '다음 주에 서비스 이야기를 나누고 싶습니다.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], CoffeeChat.STATUS_PENDING)
        self.assertTrue(response.data['is_sender'])

        self.client.force_authenticate(self.startup_user)
        listed = self.client.get('/api/coffeechats/my-requests/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertFalse(listed.data[0]['is_sender'])
        self.assertEqual(listed.data[0]['sender_name'], self.vc_user.username)

    def test_unmatched_user_cannot_receive_coffeechat(self):
        self.client.force_authenticate(self.vc_user)
        response = self.client.post('/api/coffeechats/request/', {
            'receiver_id': self.other_user.id,
            'message': '매칭되지 않은 사용자에게 보내는 메시지',
        }, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CoffeeChat.objects.exists())

    def test_duplicate_pending_request_is_blocked(self):
        CoffeeChat.objects.create(
            sender=self.vc_user,
            receiver=self.startup_user,
            message='첫 번째 제안',
        )
        self.client.force_authenticate(self.vc_user)
        response = self.client.post('/api/coffeechats/request/', {
            'receiver_id': self.startup_user.id,
            'message': '중복 제안',
        }, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(CoffeeChat.objects.count(), 1)


class MutualLikeMatchingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.vc_user = User.objects.create_user(username='matching-vc', role='vc', email_verified=True)
        self.startup_user = User.objects.create_user(username='matching-startup', role='startup', email_verified=True)
        self.vc = VCProfile.objects.create(user=self.vc_user, firm_name='매칭 VC')
        self.startup = StartupProfile.objects.create(
            user=self.startup_user,
            name='매칭 스타트업', industry='AI', stage='Seed', region='서울')
        self.client = APIClient()

    def test_second_mutual_like_creates_match_and_first_user_can_observe_it(self):
        self.client.force_authenticate(self.startup_user)
        first = self.client.post(f'/api/likes/vc/{self.vc.id}/toggle/')
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data['liked'])
        self.assertFalse(first.data['matched'])
        self.assertTrue(first.data['awaiting_mutual_like'])

        self.client.force_authenticate(self.vc_user)
        second = self.client.post(f'/api/likes/startup/{self.startup.id}/toggle/')
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data['matched'])
        self.assertIsNotNone(second.data['match_id'])
        self.assertEqual(Match.objects.filter(vc=self.vc, startup=self.startup).count(), 1)

        self.client.force_authenticate(self.startup_user)
        visible = self.client.get('/api/matches/')
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(len(visible.data), 1)
        self.assertEqual(visible.data[0]['id'], second.data['match_id'])

    def test_like_cannot_be_removed_after_match_is_created(self):
        Like.objects.create(vc=self.vc, startup=self.startup, by='vc')
        Like.objects.create(vc=self.vc, startup=self.startup, by='startup')
        match = Match.objects.create(vc=self.vc, startup=self.startup)

        self.client.force_authenticate(self.vc_user)
        response = self.client.post(f'/api/likes/startup/{self.startup.id}/toggle/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['liked'])
        self.assertTrue(response.data['matched'])
        self.assertEqual(response.data['match_id'], match.id)
        self.assertEqual(Like.objects.filter(vc=self.vc, startup=self.startup).count(), 2)

    def test_matches_list_repairs_preexisting_mutual_likes(self):
        Like.objects.create(vc=self.vc, startup=self.startup, by='vc')
        Like.objects.create(vc=self.vc, startup=self.startup, by='startup')
        self.assertFalse(Match.objects.filter(vc=self.vc, startup=self.startup).exists())

        self.client.force_authenticate(self.startup_user)
        response = self.client.get('/api/matches/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(Match.objects.filter(vc=self.vc, startup=self.startup).exists())
