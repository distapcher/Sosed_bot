#!/usr/bin/env bash
# Первичная установка на новый VPS (Ubuntu/Debian). Запускать НА СЕРВЕРЕ от root:
#   curl -fsSL https://raw.githubusercontent.com/distapcher/Sosed_bot/master/scripts/server-setup.sh | bash
# или после git clone:
#   bash scripts/server-setup.sh

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/sosed-bot}"
REPO_URL="${REPO_URL:-https://github.com/distapcher/Sosed_bot.git}"
BRANCH="${BRANCH:-master}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Запустите от root: sudo bash $0" >&2
  exit 1
fi

echo "== 1/4 Системные пакеты =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git gnupg

echo "== 2/4 Docker =="
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable docker >/dev/null 2>&1 || true
systemctl start docker >/dev/null 2>&1 || true
docker --version
docker compose version

echo "== 3/4 Клонирование репозитория =="
mkdir -p "$(dirname "$DEPLOY_DIR")"
if [[ -d "$DEPLOY_DIR/.git" ]]; then
  cd "$DEPLOY_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
  cd "$DEPLOY_DIR"
fi
echo "Код: $(git rev-parse --short HEAD) @ $DEPLOY_DIR"

echo "== 4/4 .env =="
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ""
  echo "Создан .env из примера. Обязательно отредактируйте:"
  echo "  nano $DEPLOY_DIR/.env"
  echo ""
  echo "Или скопируйте со старого сервера (с Mac):"
  echo "  scp root@50.114.102.254:$DEPLOY_DIR/.env root@$(hostname -I | awk '{print $1}'):$DEPLOY_DIR/.env"
else
  echo ".env уже есть — не перезаписываем."
fi

echo ""
echo "== Проверка =="
bash "$DEPLOY_DIR/scripts/check-server.sh" || true

echo ""
echo "== Дальше =="
echo "1) Заполните .env (токен бота, DeepSeek, пароль админки)"
echo "2) Остановите бота на СТАРОМ VPS (чтобы не было двух polling):"
echo "     ssh root@50.114.102.254 'cd /opt/sosed-bot && docker compose stop sosed'"
echo "3) Запуск:"
echo "     cd $DEPLOY_DIR && docker compose build --pull=false && docker compose up -d"
echo "4) Логи: docker compose logs -f sosed --tail=50"
