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
- `/pay` — оплатить доступ (если включена ЮKassa)
- `/status` — проверить подписку

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

## Бот отвечает «лампочка в подъезде»

Это значит, что Telegram работает, а запрос к LLM (DeepSeek/OpenAI) падает. На сервере:

```bash
cd /opt/sosed-bot
grep OPENAI_BASE_URL .env
grep OPENAI_MODEL .env
docker compose logs --tail=50
```

Для DeepSeek в `.env` должно быть:

```env
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

Проверка API из контейнера (подставится из `.env`):

```bash
docker compose exec sosed python -c "
import os
from openai import OpenAI
c = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_BASE_URL'], timeout=60)
r = c.chat.completions.create(
    model=os.environ['OPENAI_MODEL'],
    messages=[{'role': 'user', 'content': 'скажи ок'}],
    max_tokens=20,
)
print(r.choices[0].message.content)
"
```

Частые причины: неверный ключ, нет баланса на DeepSeek, в `.env` остался URL OpenAI (`api.openai.com`) с ключом DeepSeek.

## Web-дашборд статистики

Вместе с ботом поднимается сервис `web` — страница со статистикой:

- сколько пользователей писали боту
- Telegram ID, `@username`, имя
- число сообщений
- токены (input / output) и оценка расхода в USD по каждому пользователю

### Настройка на сервере

Добавь в `/opt/sosed-bot/.env`:

```env
ADMIN_USER=admin
ADMIN_PASSWORD=надёжный_пароль
WEB_PORT=8080
STATS_DB_PATH=/data/stats.db
COST_INPUT_PER_1M_USD=0.27
COST_OUTPUT_PER_1M_USD=1.10
```

Перезапуск:

```bash
cd /opt/sosed-bot
docker compose up -d --build
```

Открой в браузере: `http://IP_СЕРВЕРА:8080`  
Логин: `ADMIN_USER`, пароль: `ADMIN_PASSWORD`.

**Безопасность:** не открывай порт 8080 всем подряд. Лучше ограничить доступ фаерволом (только твой IP) или позже поставить HTTPS через nginx.

Статистика копится с момента обновления — старые диалоги до обновления в базу не попадут.

## Оплата через ЮKassa

Модель: **подписка на N дней** за фиксированную сумму. Без оплаты бот не отвечает на вопросы (команды `/pay`, `/status`, `/start` работают).

### 1) Кабинет ЮKassa

1. Зарегистрируй магазин на [yookassa.ru](https://yookassa.ru)
2. Возьми **shopId** и **секретный ключ** (Интеграция → API ключи)
3. Включи HTTP-уведомления (webhook):

```text
http://IP_СЕРВЕРА:8080/yookassa/webhook
```

Событие: **payment.succeeded**

Для боевого режима ЮKassa обычно требует **HTTPS** — тогда нужен домен + nginx + Let's Encrypt. На тестовом магазине часто хватает HTTP.

### 2) Переменные в `.env` на сервере

```env
PAYMENT_ENABLED=true
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_секретный_ключ
PAYMENT_AMOUNT_RUB=199
PAYMENT_ACCESS_DAYS=30
PAYMENT_DESCRIPTION=Доступ к боту Сосед на 30 дней
TELEGRAM_BOT_USERNAME=имя_бота_без_@
PUBLIC_BASE_URL=http://50.114.102.254:8080
FREE_TELEGRAM_USER_IDS=ваш_telegram_id
```

`FREE_TELEGRAM_USER_IDS` — твой Telegram ID (можно узнать у `@userinfobot`), чтобы пользоваться бесплатно.

### 3) Команды бота

- `/pay` — ссылка на оплату в ЮKassa
- `/status` — проверить, до какой даты оплачен доступ

### 4) Перезапуск

```bash
cd /opt/sosed-bot
docker compose up -d --build
```

Убедись, что порт **8080** доступен с интернета (для webhook ЮKassa).

