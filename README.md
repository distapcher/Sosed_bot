# Сосед — Telegram-бот с ИИ

Бот “Сосед” даёт советы по бытовым и хозяйственным делам на русском, в стиле добродушного советского мужика с юмором.

## Что нужно

- Python 3.10+
- Токен Telegram-бота от `@BotFather`
- API ключ LLM (по умолчанию OpenAI, но можно указать совместимый `OPENAI_BASE_URL`)

## Быстрый старт

1) Создай виртуальное окружение и поставь зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

2) Скопируй переменные окружения:

```bash
cp .env.example .env
```

3) Заполни в `.env`:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- (опционально) `OPENAI_MODEL`, `OPENAI_BASE_URL`

4) Запусти:

```bash
python -m src.bot
```

## Команды бота

- `/start` — приветствие
- `/reset` — очистить память диалога в текущем чате

## Где менять характер “Соседа”

- `src/prompts.py` — системный промпт (стиль, ограничения, формат ответа)

## DeepSeek вместо OpenAI

В `.env` на сервере (файл не в git):

```env
OPENAI_API_KEY=ваш_ключ_deepseek
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

Перезапуск: `cd /opt/sosed-bot && docker compose up -d --build`

## Деплой одной командой (Mac → GitHub → VPS)

1) Один раз сделай скрипт исполняемым:

```bash
chmod +x scripts/deploy.sh
```

2) При каждом обновлении (из папки проекта на Mac):

```bash
./scripts/deploy.sh "краткое описание изменений"
```

Скрипт: коммитит изменения, пушит в `origin/master`, по SSH на сервере делает `git pull` и `docker compose up -d --build`. Файл `.env` на сервере **не трогает**.

Переменные (если нужно): `DEPLOY_HOST`, `DEPLOY_DIR`, `DEPLOY_BRANCH`.

