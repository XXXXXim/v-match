#!/usr/bin/env bash
# Vercel 빌드 단계: 프론트 빌드 + (Postgres 를 쓰면) DB 준비를 여기서 한 번만 한다.
# 방문자 요청 때 마이그레이션을 하면 첫 요청이 수십 초 걸리거나 시간 제한에 걸려 멈출 수 있어서다.
set -euo pipefail

(cd frontend && npm run build)

if [ -n "${DATABASE_URL:-}${POSTGRES_URL:-}" ]; then
  echo "[db] Postgres 감지 → 마이그레이션 + 데모 데이터 준비"
  PY=$(command -v python3.12 || command -v python3)
  "$PY" --version
  "$PY" -m pip install --quiet --disable-pip-version-check --target /tmp/vm-build-deps -r requirements.txt
  PYTHONPATH=/tmp/vm-build-deps "$PY" backend/manage.py demo_db ensure
else
  echo "[db] DATABASE_URL 없음 → 시드 SQLite 사용(빌드 단계 DB 준비 생략)"
fi
