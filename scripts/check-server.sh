#!/usr/bin/env bash
# Проверка готовности VPS к деплою «Соседа». Запускать на сервере: bash scripts/check-server.sh

set -euo pipefail

ok=0
warn=0
fail=0

check() {
  local name="$1"
  local status="$2"
  local detail="${3:-}"
  if [[ "$status" == "ok" ]]; then
    echo "  [OK]   $name${detail:+ — $detail}"
    ok=$((ok + 1))
  elif [[ "$status" == "warn" ]]; then
    echo "  [WARN] $name${detail:+ — $detail}"
    warn=$((warn + 1))
  else
    echo "  [FAIL] $name${detail:+ — $detail}"
    fail=$((fail + 1))
  fi
}

echo "=== Сосед: проверка сервера ==="
echo "Host: $(hostname)  IP: $(hostname -I 2>/dev/null | awk '{print $1}')"
echo "OS:   $(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || uname -s)"
echo

echo "--- Пакеты ---"
command -v git >/dev/null && check git ok "$(git --version)" || check git fail "установите: apt install -y git"
command -v curl >/dev/null && check curl ok "$(curl --version | head -1)" || check curl fail "apt install -y curl"
command -v docker >/dev/null && check docker ok "$(docker --version)" || check docker fail "запустите scripts/server-setup.sh"
docker compose version >/dev/null 2>&1 && check "docker compose" ok "$(docker compose version)" || check "docker compose" fail "нужен Docker Compose v2"

echo "--- Ресурсы ---"
df -h / | tail -1 | awk '{print $4}' | grep -qE '[0-9]+G|[0-9]{2,}M' && check "disk free" ok "$(df -h / | tail -1 | awk '{print $4 " on " $1}')" || check "disk free" warn "$(df -h / | tail -1)"
if command -v free >/dev/null; then
  mem="$(free -h | awk '/^Mem:/{print "RAM " $2 " total, " $7 " available"}')"
  check memory ok "$mem"
else
  check memory warn "free недоступен"
fi

echo "--- Проект ---"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/sosed-bot}"
if [[ -d "$DEPLOY_DIR/.git" ]]; then
  check "repo $DEPLOY_DIR" ok "$(cd "$DEPLOY_DIR" && git rev-parse --short HEAD 2>/dev/null)"
else
  check "repo $DEPLOY_DIR" fail "клонируйте репозиторий (server-setup.sh)"
fi

if [[ -f "$DEPLOY_DIR/.env" ]]; then
  check ".env" ok "найден"
  grep -q 'replace_me' "$DEPLOY_DIR/.env" 2>/dev/null && check ".env filled" warn "есть replace_me — отредактируйте" || check ".env filled" ok
  grep -q '^TELEGRAM_BOT_TOKEN=.\+' "$DEPLOY_DIR/.env" && check "TELEGRAM_BOT_TOKEN" ok || check "TELEGRAM_BOT_TOKEN" fail
  grep -q '^OPENAI_API_KEY=.\+' "$DEPLOY_DIR/.env" && check "OPENAI_API_KEY" ok || check "OPENAI_API_KEY" fail
else
  check ".env" fail "скопируйте со старого VPS или cp .env.example .env"
fi

echo "--- Сеть → Telegram ---"
if curl -fsS --max-time 15 "https://api.telegram.org" >/dev/null 2>&1; then
  check "api.telegram.org" ok "доступен"
else
  check "api.telegram.org" fail "нет HTTPS до Telegram"
fi

if [[ -f "$DEPLOY_DIR/.env" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$DEPLOY_DIR/.env" && set +a
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  resp="$(curl -fsS --max-time 20 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" 2>/dev/null || true)"
    if echo "$resp" | grep -q '"ok":true'; then
      user="$(echo "$resp" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')"
      check "getMe" ok "@${user}"
    else
      check "getMe" fail "неверный токен или сеть"
    fi
  fi
fi

echo "--- Docker (если уже запущен) ---"
if [[ -d "$DEPLOY_DIR" ]] && command -v docker >/dev/null; then
  (cd "$DEPLOY_DIR" && docker compose ps 2>/dev/null) || true
fi

echo
echo "Итого: OK=$ok  WARN=$warn  FAIL=$fail"
[[ "$fail" -eq 0 ]] && exit 0 || exit 1
