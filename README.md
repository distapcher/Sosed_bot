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

