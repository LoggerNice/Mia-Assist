"""
Orchestrator - Центральный API Gateway и роутер команд
Голосовой ассистент "Мия"

Этот модуль отвечает за:
- Прием голосовых команд от клиента
- Проверку активационного слова "Мия"
- Поиск команд в базе данных
- Публикацию команд в RabbitMQ
- Fallback к LLM (Qwen) для неизвестных команд
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncpg
import aio_pika
import json
import re
import os
from contextlib import asynccontextmanager

# ============================================
# Конфигурация
# ============================================

class Config:
    """Конфигурация приложения"""
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/miya_db")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    QWEN_API_URL: str = os.getenv("QWEN_API_URL", "https://api.qwen.ai/v1/chat/completions")
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    ACTIVATION_WORD: str = "мия"
    
    # Очереди RabbitMQ
    PC_COMMANDS_QUEUE: str = "pc_commands_queue"
    CONTROLLER_COMMANDS_QUEUE: str = "controller_commands_queue"
    GENERAL_QUEUE: str = "general_queue"


config = Config()

# ============================================
# Модели данных
# ============================================

class CommandRequest(BaseModel):
    """Запрос команды от клиента"""
    text: str = Field(..., description="Распознанный текст голосовой команды")
    user_id: int = Field(..., description="ID пользователя")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Мия, запусти стим",
                "user_id": 1
            }
        }


class CommandResponse(BaseModel):
    """Ответ клиенту"""
    status: str = Field(..., description="Статус выполнения")
    message: str = Field(..., description="Сообщение для пользователя")
    audio_url: Optional[str] = Field(None, description="URL аудио ответа (для LLM fallback)")
    command_id: Optional[int] = Field(None, description="ID выполненной команды")


class CommandDB(BaseModel):
    """Модель команды из базы данных"""
    id: int
    trigger_phrase: List[str]
    target_entity: str
    action_type: str
    payload_template: Dict[str, Any]
    is_active: bool


# ============================================
# Управление приложением
# ============================================

db_pool: Optional[asyncpg.Pool] = None
rabbitmq_connection: Optional[aio_pika.Connection] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Инициализация при запуске
    global db_pool, rabbitmq_connection
    
    # Подключение к базе данных
    db_pool = await asyncpg.create_pool(config.DATABASE_URL)
    print("✓ Подключение к базе данных установлено")
    
    # Подключение к RabbitMQ
    rabbitmq_connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
    print("✓ Подключение к RabbitMQ установлено")
    
    yield
    
    # Очистка при остановке
    if db_pool:
        await db_pool.close()
    if rabbitmq_connection:
        await rabbitmq_connection.close()
    print("✓ Соединения закрыты")


app = FastAPI(
    title="Мия Orchestrator",
    description="API Gateway для голосового ассистента Мия",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================
# Утилиты
# ============================================

def normalize_text(text: str) -> str:
    """
    Нормализация текста:
    - Приведение к нижнему регистру
    - Удаление лишних пробелов
    - Удаление специальных символов
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\sа-яё]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def check_activation_word(text: str) -> bool:
    """Проверка наличия активационного слова 'Мия'"""
    normalized = normalize_text(text)
    activation = config.ACTIVATION_WORD.lower()
    
    # Проверяем наличие слова в начале или в любом месте
    return activation in normalized.split()


def remove_activation_word(text: str) -> str:
    """Удаление активационного слова из текста"""
    normalized = normalize_text(text)
    activation = config.ACTIVATION_WORD.lower()
    
    # Удаляем активационное слово и лишние пробелы
    words = normalized.split()
    filtered_words = [w for w in words if w != activation]
    return ' '.join(filtered_words)


async def find_command_in_db(normalized_text: str) -> Optional[CommandDB]:
    """
    Поиск команды в базе данных по триггерной фразе
    
    Использует PostgreSQL оператор && для пересечения массивов
    """
    async with db_pool.acquire() as conn:
        # Разбиваем текст на слова для поиска по массиву триггеров
        words = normalized_text.split()
        
        # Поиск по точному совпадению фразы
        row = await conn.fetchrow("""
            SELECT id, trigger_phrase, target_entity, action_type, payload_template, is_active
            FROM commands
            WHERE is_active = TRUE 
              AND trigger_phrase && $1::TEXT[]
            ORDER BY id
            LIMIT 1
        """, words)
        
        if row:
            return CommandDB(
                id=row['id'],
                trigger_phrase=row['trigger_phrase'],
                target_entity=row['target_entity'],
                action_type=row['action_type'],
                payload_template=dict(row['payload_template']),
                is_active=row['is_active']
            )
        
        # Поиск по частичному совпадению (если фраза содержит ключевые слова)
        for word in words:
            if len(word) > 3:  # Игнорируем короткие слова
                row = await conn.fetchrow("""
                    SELECT id, trigger_phrase, target_entity, action_type, payload_template, is_active
                    FROM commands
                    WHERE is_active = TRUE
                      AND trigger_phrase @> ARRAY[$1::TEXT]
                    LIMIT 1
                """, word)
                
                if row:
                    return CommandDB(
                        id=row['id'],
                        trigger_phrase=row['trigger_phrase'],
                        target_entity=row['target_entity'],
                        action_type=row['action_type'],
                        payload_template=dict(row['payload_template']),
                        is_active=row['is_active']
                    )
        
        return None


async def publish_to_rabbitmq(queue_name: str, message: Dict[str, Any]) -> bool:
    """Публикация сообщения в очередь RabbitMQ"""
    try:
        channel = await rabbitmq_connection.channel()
        
        # Объявляем очередь (на случай если не существует)
        await channel.declare_queue(queue_name, durable=True)
        
        # Создаем сообщение
        body = json.dumps(message).encode('utf-8')
        message_obj = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        # Публикуем
        await channel.default_exchange.publish(
            message_obj,
            routing_key=queue_name
        )
        
        print(f"✓ Сообщение опубликовано в очередь {queue_name}")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка публикации в RabbitMQ: {e}")
        return False


async def query_qwen_llm(user_text: str, user_id: int) -> str:
    """
    Fallback запрос к LLM Qwen для обработки неизвестных команд
    
    Это мокап функции - в продакшене здесь будет реальный API вызов
    """
    # Мокап ответа (в реальности здесь будет вызов API Qwen)
    mock_responses = {
        "погода": "К сожалению, я пока не умею проверять погоду, но скоро научусь!",
        "время": "Сейчас я не могу сказать точное время, но ваш компьютер знает!",
        "шутка": "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
        "default": "Я пока не знаю эту команду, но я учусь! Попробуйте сказать что-то другое."
    }
    
    # Простой поиск ключевых слов для выбора ответа
    normalized = user_text.lower()
    for key, response in mock_responses.items():
        if key != "default" and key in normalized:
            return response
    
    return mock_responses["default"]
    
    # ============================================
    # Реальная реализация (раскомментировать для продакшена)
    # ============================================
    """
    import aiohttp
    
    headers = {
        "Authorization": f"Bearer {config.QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qwen-plus",
        "messages": [
            {
                "role": "system",
                "content": "Ты голосовой ассистент Мия. Отвечай кратко и дружелюбно."
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        "max_tokens": 150
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(config.QWEN_API_URL, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data['choices'][0]['message']['content']
            else:
                return "Извините, возникла ошибка при обработке запроса."
    """


async def generate_tts_audio(text: str) -> Optional[str]:
    """
    Генерация аудио из текста (TTS)
    
    Возвращает URL аудиофайла
    В MVP возвращает None (клиент может использовать встроенный TTS)
    """
    # В реальной реализации здесь будет вызов TTS сервиса
    # Например, Yandex SpeechKit, Google TTS, или локальный Coqui TTS
    return None


# ============================================
# API Endpoints
# ============================================

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "Mia Orchestrator",
        "version": "1.0.0"
    }


@app.post("/api/command", response_model=CommandResponse)
async def handle_command(request: CommandRequest, background_tasks: BackgroundTasks):
    """
    Основной эндпоинт для обработки голосовых команд
    
    Логика работы:
    1. Проверка активационного слова "Мия"
    2. Нормализация текста
    3. Поиск команды в БД
    4. Если найдена - публикация в RabbitMQ
    5. Если не найдена - fallback к LLM
    """
    
    # Шаг 1: Проверка активационного слова
    if not check_activation_word(request.text):
        return CommandResponse(
            status="ignored",
            message="Команда проигнорирована: отсутствует активационное слово 'Мия'"
        )
    
    # Шаг 2: Удаление активационного слова и нормализация
    cleaned_text = remove_activation_word(request.text)
    print(f"Обработка команды: {cleaned_text}")
    
    # Шаг 3: Поиск команды в базе данных
    command = await find_command_in_db(cleaned_text)
    
    if command:
        # Шаг 4a: Команда найдена - публикуем в RabbitMQ
        
        # Определяем очередь в зависимости от target_entity
        queue_mapping = {
            "PC": config.PC_COMMANDS_QUEUE,
            "CONTROLLER": config.CONTROLLER_COMMANDS_QUEUE,
            "GENERAL": config.GENERAL_QUEUE
        }
        
        queue_name = queue_mapping.get(command.target_entity, config.GENERAL_QUEUE)
        
        # Формируем сообщение для агента
        message_payload = {
            "command_id": command.id,
            "user_id": request.user_id,
            "action_type": command.action_type,
            "payload": command.payload_template,
            "original_text": request.text,
            "cleaned_text": cleaned_text,
            "timestamp": None  # Будет добавлено при публикации
        }
        
        # Добавляем текущее время
        from datetime import datetime
        message_payload["timestamp"] = datetime.utcnow().isoformat()
        
        # Публикуем в очередь
        success = await publish_to_rabbitmq(queue_name, message_payload)
        
        if success:
            return CommandResponse(
                status="accepted",
                message=f"Команда '{cleaned_text}' принята к исполнению",
                command_id=command.id
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Ошибка доставки команды агенту"
            )
    
    else:
        # Шаг 4b: Команда не найдена - fallback к LLM
        print(f"Команда не найдена, используем LLM fallback: {cleaned_text}")
        
        llm_response = await query_qwen_llm(cleaned_text, request.user_id)
        
        # Генерируем аудио ответ (опционально)
        audio_url = await generate_tts_audio(llm_response)
        
        return CommandResponse(
            status="llm_response",
            message=llm_response,
            audio_url=audio_url
        )


@app.get("/api/commands")
async def list_commands():
    """Получить список всех активных команд (для отладки)"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, trigger_phrase, target_entity, action_type, is_active
            FROM commands
            WHERE is_active = TRUE
            ORDER BY id
        """)
        
        return [
            {
                "id": row['id'],
                "trigger_phrase": row['trigger_phrase'],
                "target_entity": row['target_entity'],
                "action_type": row['action_type']
            }
            for row in rows
        ]


# ============================================
# Запуск приложения
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
