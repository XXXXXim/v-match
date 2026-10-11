"""
라이브 매칭 데모용 계정 준비.

실제 카탈로그의 VC 1곳 + 스타트업 1곳에 '로그인 계정'을 붙인다(이메일 인증 완료).
좋아요는 미리 깔지 않는다 → 발표 때 두 계정이 직접 서로 좋아요를 눌러 진짜 매칭을 보여줌.

전제: seed_real_vcs, seed_real_startups 를 먼저 실행해 카탈로그가 있어야 한다.

사용:
  python manage.py seed_demo
  python manage.py seed_demo --vc "매쉬업벤처스" --startup "리빌더AI"
  python manage.py seed_demo --password mypw --reset
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from core.models import VCProfile, StartupProfile

VC_USERNAME = 'demo_vc'
STARTUP_USERNAME = 'demo_startup'


class Command(BaseCommand):
    help = '라이브 매칭 데모용으로 실제 VC/스타트업에 로그인 계정을 부여한다.'

    def add_arguments(self, parser):
        parser.add_argument('--vc', default='', help='데모 VC firm_name (생략 시 스타트업에 가장 잘 맞는 VC 자동 선택)')
        parser.add_argument('--startup', default='탑테이블', help='데모 스타트업으로 쓸 카탈로그 스타트업 name')
        parser.add_argument('--password', default='demo1234', help='두 데모 계정의 공통 비밀번호')
        parser.add_argument('--reset', action='store_true', help='기존 데모 계정 삭제 후 재생성')

    @transaction.atomic
    def handle(self, *args, **opts):
        from core.recommend import calculate_recommendation
        pw = opts['password']

        if opts['reset']:
            User.objects.filter(username__in=[VC_USERNAME, STARTUP_USERNAME]).delete()
            self.stdout.write('기존 데모 계정 삭제됨')

        sp = StartupProfile.objects.filter(name=opts['startup']).first()
        if not sp:
            self.stderr.write(self.style.ERROR(
                f'스타트업 "{opts["startup"]}" 를 찾을 수 없습니다. '
                f'startup_data.json 을 채우고 seed_real_startups 를 실행하세요.'))
            return

        if opts['vc']:
            vc = VCProfile.objects.filter(firm_name=opts['vc']).first()
            if not vc:
                self.stderr.write(self.style.ERROR(
                    f'VC "{opts["vc"]}" 를 찾을 수 없습니다. 먼저 seed_real_vcs 를 실행하세요.'))
                return
        else:
            # 스타트업에 가장 잘 맞는(FIT 최고) VC 자동 선택
            best, best_score = None, -1
            for cand in VCProfile.objects.all():
                try:
                    s, _, _ = calculate_recommendation(cand, sp)
                except Exception:
                    continue
                if s > best_score:
                    best, best_score = cand, s
            vc = best
            if not vc:
                self.stderr.write(self.style.ERROR('VC가 없습니다. 먼저 seed_real_vcs 를 실행하세요.'))
                return
            self.stdout.write(f'자동 선택된 데모 VC: {vc.firm_name} (FIT {best_score}점)')

        # --- 데모 VC 계정 ---
        vc_user, _ = User.objects.get_or_create(
            username=VC_USERNAME,
            defaults=dict(email='demo_vc@vmatch.demo', role='vc'),
        )
        vc_user.role = 'vc'
        vc_user.email = 'demo_vc@vmatch.demo'
        vc_user.email_verified = True            # 이메일 인증 완료 상태
        vc_user.set_password(pw)
        vc_user.save()
        # 혹시 이 VC가 다른 user에 연결돼 있으면 떼고 데모 user로 연결
        VCProfile.objects.filter(user=vc_user).exclude(id=vc.id).update(user=None)
        vc.user = vc_user
        vc.save(update_fields=['user'])

        # --- 데모 스타트업 계정 ---
        sp_user, _ = User.objects.get_or_create(
            username=STARTUP_USERNAME,
            defaults=dict(email='demo_startup@vmatch.demo', role='startup'),
        )
        sp_user.role = 'startup'
        sp_user.email = 'demo_startup@vmatch.demo'
        sp_user.email_verified = True
        sp_user.set_password(pw)
        sp_user.save()
        StartupProfile.objects.filter(user=sp_user).exclude(id=sp.id).update(user=None)
        sp.user = sp_user
        sp.save(update_fields=['user'])

        self.stdout.write(self.style.SUCCESS('\n✅ 라이브 데모 계정 준비 완료'))
        self.stdout.write('────────────────────────────────────────')
        self.stdout.write(f'  데모 VC      : {vc.firm_name}')
        self.stdout.write(f'    아이디     : {VC_USERNAME}')
        self.stdout.write(f'    비밀번호   : {pw}')
        self.stdout.write(f'  데모 스타트업: {sp.name} ({sp.industry}/{sp.stage})')
        self.stdout.write(f'    아이디     : {STARTUP_USERNAME}')
        self.stdout.write(f'    비밀번호   : {pw}')
        self.stdout.write('────────────────────────────────────────')
        self.stdout.write(self.style.WARNING('  좋아요는 깔지 않았습니다 — 발표 때 두 계정이 직접 눌러 매칭하세요.'))
        self.stdout.write('\n  [라이브 시연 순서]')
        self.stdout.write('  1) 브라우저A: demo_startup 로그인 → "VC 추천"에서 데모 VC 좋아요')
        self.stdout.write('  2) 브라우저B: demo_vc 로그인 → 알림 배지 확인 → "스타트업 찾기"에서')
        self.stdout.write(f'     {sp.name} 좋아요 → 매칭 성사 → AI 실사 리포트')
        self.stdout.write('  (순서는 반대로 해도 됩니다. 알림→맞좋아요가 실시간으로 보입니다.)\n')
