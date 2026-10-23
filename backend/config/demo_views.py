"""공개 데모 전용 엔드포인트 — 매일 데모 데이터를 처음 상태로 되돌린다.

Vercel Cron 이 하루 한 번 GET 으로 부르고, 요청 헤더에 `Authorization: Bearer <CRON_SECRET>` 를 붙여 준다.
데모 모드가 아니거나 비밀값이 맞지 않으면 아무 일도 하지 않는다.
"""
import hmac
import os

from django.core.management import call_command
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def reset_demo(request):
    from django.conf import settings

    secret = os.environ.get('CRON_SECRET', '')
    if not (settings.VMATCH_DEMO_MODE and secret):
        raise Http404
    sent = request.headers.get('Authorization', '')
    if not hmac.compare_digest(sent, f'Bearer {secret}'):
        return JsonResponse({'error': 'unauthorized'}, status=401)
    call_command('demo_db', 'reset', verbosity=0)
    return JsonResponse({'reset': True})
