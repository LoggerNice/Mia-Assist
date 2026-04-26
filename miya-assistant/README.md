# Голосовой ассистент "Мия" - MVP

Распределенная система голосового управления устройствами с микросервисной архитектурой.

## 📋 Содержание

1. [Архитектура](#архитектура)
2. [Компоненты системы](#компоненты-системы)
3. [Быстрый старт](#быстрый-старт)
4. [API Reference](#api-reference)
5. [Команды](#команды)

---

## 🏗️ Архитектура

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   Client    │─────▶│   Orchestrator   │─────▶│  PostgreSQL │
│ (React Nat.)│      │   (FastAPI)      │      │             │
└─────────────┘      └────────┬─────────┘      └─────────────┘
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
            ┌────────────────┐  ┌──────────────┐
            │   RabbitMQ     │  │  Qwen LLM    │
            │                │  │  (Fallback)  │
            └───────┬────────┘  └──────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌────────────────┐    ┌─────────────────┐
│   PC Agent     │    │ Controller Agent│
│   (Windows)    │    │  (Smart Home)   │
└────────────────┘    └─────────────────┘
```

---

## 🧩 Компоненты системы

### 1. Orchestrator (`/orchestrator`)
Центральный API Gateway на FastAPI:
- Прием команд от клиентов
- Проверка активационного слова "Мия"
- Маршрутизация команд в БД или LLM
- Публикация в RabbitMQ

**Запуск:**
```bash
cd orchestrator
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. PC Agent (`/pc_agent`)
Сервис для выполнения команд на ПК:
- Подписка на очередь RabbitMQ
- Запуск приложений (Steam, Discord, Opera)
- Системные команды (выключение, открытие папок)
- Поиск в браузере

**Запуск:**
```bash
cd pc_agent
pip install -r requirements.txt
python agent.py
```

### 3. Mobile Client (`/mobile_client`)
React Native приложение:
- Распознавание голоса (@react-native-voice/voice)
- Отправка команд на сервер
- Воспроизведение аудио ответов

**Запуск:**
```bash
cd mobile_client
npm install
npx react-native run-android  # или run-ios
```

### 4. Database (`/sql`)
SQL скрипты для PostgreSQL:
- Таблица `commands` с триггерными фразами
- Индексы для оптимизации поиска
- Примеры данных для MVP

**Установка:**
```bash
psql -U user -d miya_db -f sql/schema.sql
```

---

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.10+
- PostgreSQL 14+
- RabbitMQ 3.12+
- Node.js 18+ (для клиента)

### 1. Установка базы данных

```bash
# Создаем базу данных
createdb miya_db

# Выполняем схему
psql -U postgres -d miya_db -f sql/schema.sql
```

### 2. Настройка RabbitMQ

```bash
# Docker (рекомендуется)
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

# Или локальная установка
# https://www.rabbitmq.com/download.html
```

### 3. Запуск Orchestrator

```bash
cd orchestrator

# Создаем виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем сервер
uvicorn main:app --reload
```

Проверка: http://localhost:8000/docs

### 4. Запуск PC Agent

```bash
cd pc_agent

# Виртуальное окружение
python -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск агента
python agent.py
```

### 5. Переменные окружения

Создайте файл `.env` в директории orchestrator:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/miya_db
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
QWEN_API_KEY=your_api_key_here
QWEN_API_URL=https://api.qwen.ai/v1/chat/completions
```

---

## 📡 API Reference

### POST /api/command

Отправка голосовой команды.

**Request:**
```json
{
  "text": "Мия, запусти стим",
  "user_id": 1
}
```

**Response (успех):**
```json
{
  "status": "accepted",
  "message": "Команда 'запусти стим' принята к исполнению",
  "command_id": 1
}
```

**Response (LLM fallback):**
```json
{
  "status": "llm_response",
  "message": "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
  "audio_url": null
}
```

**Response (игнорирование):**
```json
{
  "status": "ignored",
  "message": "Команда проигнорирована: отсутствует активационное слово 'Мия'"
}
```

### GET /api/commands

Список всех активных команд (для отладки).

### GET /health

Проверка здоровья сервиса.

---

## 🎤 Команды

### Приложения

| Команда | Действие |
|---------|----------|
| "Мия, запусти стим" | Запуск Steam |
| "Мия, открой дискорд" | Запуск Discord |
| "Мия, включи оперу" | Запуск Opera |

### Системные

| Команда | Действие |
|---------|----------|
| "Мия, выключи компьютер" | Выключение ПК |
| "Мия, открой документы" | Открытие папки Документы |

### Поиск

| Команда | Действие |
|---------|----------|
| "Мия, найди в интернете" | Открыть Google |
| "Мия, погугли [запрос]" | Поиск в Google |

### LLM Fallback

Любая другая команда будет обработана через Qwen LLM:

- "Мия, расскажи шутку"
- "Мия, как дела?"
- "Мия, что ты умеешь?"

---

## 📊 Диаграммы

См. [docs/sequence_diagram.md](docs/sequence_diagram.md) для подробных диаграмм последовательности.

---

## 🛠️ Расширение

### Добавление новой команды

1. Добавьте запись в таблицу `commands`:

```sql
INSERT INTO commands (trigger_phrase, target_entity, action_type, payload_template)
VALUES (
  ARRAY['новая команда', 'синоним'],
  'PC',
  'LAUNCH_APP',
  '{"app_name": "MyApp", "executable_path": "C:\\path\\to\\app.exe"}'::jsonb
);
```

2. Если нужен новый тип действия, добавьте обработчик в `pc_agent/agent.py`:

```python
class NewActionHandler(CommandHandler):
    async def execute(self, payload: Dict[str, Any]) -> bool:
        # Ваша логика
        pass
```

3. Зарегистрируйте в `CommandDispatcher`:

```python
self.handlers[ActionType.NEW_ACTION] = NewActionHandler()
```

---

## 📝 Лицензия

MIT License

---

## 👥 Авторы

Голосовой ассистент "Мия" - MVP версия
