"""
DART 전자공시 OpenAPI 연동 — 단일회사 주요계정(재무제표)을 받아
StartupProfile.financials 에 저장한다.

사용:
  python manage.py fetch_dart --startup 5 --corp 00126380
  python manage.py fetch_dart --startup "데모페이" --corp "삼성전자" --year 2024

API 키: 환경변수 DART_API_KEY 또는 --key 로 전달.
키 발급: https://opendart.fss.or.kr → 인증키 신청/관리 (무료)
"""
import io
import json
import os
import zipfile
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from core.models import StartupProfile

CORP_CODE_URL = 'https://opendart.fss.or.kr/api/corpCode.xml'
FIN_URL = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'

# DART account_nm → 우리 키
ACCOUNT_MAP = {
    '매출액': 'revenue',
    '영업이익': 'operating_profit',
    '당기순이익': 'net_income',
    '자산총계': 'assets',
    '부채총계': 'liabilities',
}


def _won_to_man(s):
    """'1,234,567'(원) → 123(만원). 빈값/음수 처리."""
    if not s:
        return None
    s = str(s).replace(',', '').strip()
    neg = s.startswith('-')
    s = s.lstrip('-')
    if not s.isdigit():
        return None
    val = int(s) // 10000
    return -val if neg else val


class Command(BaseCommand):
    help = 'DART에서 재무제표를 받아 StartupProfile.financials에 저장'

    def add_arguments(self, parser):
        parser.add_argument('--startup', required=True, help='StartupProfile id 또는 name')
        parser.add_argument('--corp', required=True, help='DART corp_code(8자리) 또는 회사명')
        parser.add_argument('--year', type=int, default=None, help='사업연도(기본: 작년)')
        parser.add_argument('--key', default=None, help='DART API 키(없으면 환경변수 DART_API_KEY)')

    def handle(self, *args, **opt):
        key = opt['key'] or os.environ.get('DART_API_KEY')
        if not key:
            raise CommandError('DART API 키가 없습니다. --key 또는 환경변수 DART_API_KEY 설정')

        startup = self._find_startup(opt['startup'])

        corp = opt['corp'].strip()
        if corp.isdigit() and len(corp) == 8:
            corp_code = corp
        else:
            corp_code = self._lookup_corp_code(key, corp)
            self.stdout.write(f'회사명 "{corp}" → corp_code {corp_code}')

        year = opt['year'] or (datetime.date.today().year - 1)
        financials = self._fetch_financials(key, corp_code, year)
        if not financials['years']:
            raise CommandError('재무 데이터를 찾지 못했습니다. corp_code/연도를 확인하세요.')

        startup.financials = financials
        startup.save(update_fields=['financials'])
        self.stdout.write(self.style.SUCCESS(
            f'✓ {startup.name}: ' + ', '.join(sorted(financials['years'].keys())) + ' 재무 저장 완료'))
        for yr, vals in sorted(financials['years'].items()):
            self.stdout.write(f'  {yr}: ' + ', '.join(f'{k}={v}' for k, v in vals.items()))

    def _find_startup(self, ref):
        if ref.isdigit():
            try:
                return StartupProfile.objects.get(pk=int(ref))
            except StartupProfile.DoesNotExist:
                pass
        qs = StartupProfile.objects.filter(name=ref)
        if not qs.exists():
            raise CommandError(f'스타트업을 찾을 수 없습니다: {ref}')
        if qs.count() > 1:
            raise CommandError(f'동명 스타트업이 여럿입니다. id로 지정하세요: {ref}')
        return qs.first()

    def _get(self, url, params):
        full = url + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(full, headers={'User-Agent': 'V-Match/1.0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()

    def _lookup_corp_code(self, key, name):
        raw = self._get(CORP_CODE_URL, {'crtfc_key': key})
        zf = zipfile.ZipFile(io.BytesIO(raw))
        xml = zf.read('CORPCODE.xml').decode('utf-8')
        root = ET.fromstring(xml)
        exact, partial = None, None
        for item in root.iter('list'):
            corp_name = (item.findtext('corp_name') or '').strip()
            code = (item.findtext('corp_code') or '').strip()
            stock = (item.findtext('stock_code') or '').strip()
            if corp_name == name:
                if stock:           # 상장사 우선
                    return code
                exact = exact or code
            elif name in corp_name and partial is None:
                partial = code
        if exact:
            return exact
        if partial:
            return partial
        raise CommandError(f'DART에서 회사명을 찾지 못했습니다: {name}')

    def _fetch_financials(self, key, corp_code, year):
        out = {'corp_code': corp_code, 'source': 'DART', 'years': {}}
        params = {
            'crtfc_key': key, 'corp_code': corp_code,
            'bsns_year': str(year), 'reprt_code': '11011',   # 사업보고서(연간)
        }
        data = json.loads(self._get(FIN_URL, params))
        if data.get('status') != '000':
            raise CommandError(f'DART 응답 오류: {data.get("status")} {data.get("message")}')

        rows = data.get('list', [])
        thstrm, frmtrm = {}, {}
        # 연결(CFS) 먼저 채우고, 비면 개별(OFS)로 보충
        for prefer in ('CFS', 'OFS', ''):
            for row in rows:
                fs = (row.get('fs_div') or '').strip()
                if prefer and fs != prefer:
                    continue
                our = ACCOUNT_MAP.get((row.get('account_nm') or '').strip())
                if not our:
                    continue
                t = _won_to_man(row.get('thstrm_amount'))
                f = _won_to_man(row.get('frmtrm_amount'))
                if t is not None:
                    thstrm.setdefault(our, t)
                if f is not None:
                    frmtrm.setdefault(our, f)
        if thstrm:
            out['years'][str(year)] = thstrm
        if frmtrm:
            out['years'][str(year - 1)] = frmtrm
        return out
