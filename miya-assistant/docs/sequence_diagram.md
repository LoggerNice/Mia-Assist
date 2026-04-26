# Диаграмма последовательности взаимодействия компонентов
## Голосовой ассистент "Мия"

Этот документ содержит Mermaid диаграммы для двух сценариев работы системы.

---

## Сценарий A: Успешное выполнение известной команды ("Запусти Стим")

```mermaid
sequenceDiagram
    autonumber
    participant Client as 📱 Клиент (React Native)
    participant Orchestrator as ⚙️ Orchestrator (FastAPI)
    participant DB as 🗄️ PostgreSQL
    participant RabbitMQ as 🐰 RabbitMQ
    participant PCAgent as 💻 PC Agent

    Note over Client,PCAgent: Сценарий: Пользователь говорит "Мия, запусти стим"

    Client->>Client: Распознавание речи (Voice Recognition)
    Client->>Orchestrator: POST /api/command<br/>{text: "Мия, запусти стим", user_id: 1}
    
    activate Orchestrator
    Orchestrator->>Orchestrator: Проверка активационного слова "Мия"
    Orchestrator->>Orchestrator: Нормализация текста<br/>"запусти стим"
    
    Orchestrator->>DB: Поиск команды по trigger_phrase
    activate DB
    DB-->>Orchestrator: Найдено:<br/>id=1, action_type=LAUNCH_APP,<br/>target_entity=PC,<br/>payload={executable_path: "Steam.exe"}
    deactivate DB
    
    Orchestrator->>RabbitMQ: Публикация в pc_commands_queue<br/>{command_id: 1, action_type: LAUNCH_APP, payload: {...}}
    activate RabbitMQ
    RabbitMQ-->>Orchestrator: Сообщение доставлено
    deactivate RabbitMQ
    
    Orchestrator-->>Client: HTTP 202 Accepted<br/>{status: "accepted", message: "Команда принята", command_id: 1}
    deactivate Orchestrator
    
    Client->>Client: Показать статус "Выполняется..."
    
    Note over RabbitMQ,PCAgent: Асинхронная обработка
    
    RabbitMQ->>PCAgent: Доставить сообщение из очереди
    activate PCAgent
    PCAgent->>PCAgent: Парсинг action_type = LAUNCH_APP
    PCAgent->>PCAgent: Выполнение subprocess.Popen("Steam.exe")
    PCAgent-->>RabbitMQ: Подтверждение обработки (ack)
    deactivate PCAgent
    
    Note over Client,PCAgent: ✅ Steam запущен на ПК пользователя
```

---

## Сценарий B: Fallback к ИИ для неизвестной команды

```mermaid
sequenceDiagram
    autonumber
    participant Client as 📱 Клиент (React Native)
    participant Orchestrator as ⚙️ Orchestrator (FastAPI)
    participant DB as 🗄️ PostgreSQL
    participant LLM as 🤖 Qwen LLM Service
    participant TTS as 🔊 TTS Service

    Note over Client,TTS: Сценарий: Пользователь спрашивает "Мия, расскажи шутку"

    Client->>Client: Распознавание речи (Voice Recognition)
    Client->>Orchestrator: POST /api/command<br/>{text: "Мия, расскажи шутку", user_id: 1}
    
    activate Orchestrator
    Orchestrator->>Orchestrator: Проверка активационного слова "Мия" ✓
    Orchestrator->>Orchestrator: Нормализация текста<br/>"расскажи шутку"
    
    Orchestrator->>DB: Поиск команды по trigger_phrase
    activate DB
    DB-->>Orchestrator: Команда не найдена ❌
    deactivate DB
    
    Note right of Orchestrator: Fallback к LLM
    
    Orchestrator->>LLM: Запрос к Qwen API<br/>{prompt: "расскажи шутку"}
    activate LLM
    LLM-->>Orchestrator: Ответ: "Почему программисты путают<br/>Хэллоуин и Рождество? Oct 31 == Dec 25!"
    deactivate LLM
    
    Orchestrator->>TTS: Генерация аудио из текста
    activate TTS
    TTS-->>Orchestrator: audio_url: "https://tts.service/audio/abc123.mp3"
    deactivate TTS
    
    Orchestrator-->>Client: HTTP 200 OK<br/>{<br/>  status: "llm_response",<br/>  message: "Почему программисты...",<br/>  audio_url: "https://..."<br/>}
    deactivate Orchestrator
    
    Client->>Client: Воспроизведение аудио (Sound.play())
    Client->>Client: Показать текст ответа в UI
    
    Note over Client,TTS: 🔊 Пользователь слышит ответ и видит текст
```

---

## Общая архитектура системы

```mermaid
graph TB
    subgraph Client_Layer["📱 Клиентский слой"]
        RN[React Native App]
        Voice[Voice Recognition]
        Audio[Audio Player]
    end
    
    subgraph API_Layer["⚙️ API Layer (Orchestrator)"]
        FastAPI[FastAPI Server]
        Auth[Auth Module]
        Router[Command Router]
        LLM_Fallback[LLM Fallback]
    end
    
    subgraph Data_Layer["💾 Data Layer"]
        PostgreSQL[(PostgreSQL)]
        RabbitMQ[(RabbitMQ)]
    end
    
    subgraph Agent_Layer["🤖 Agent Layer"]
        PC_Agent[PC Agent]
        Controller_Agent[Controller Agent<br/>(Future)]
    end
    
    subgraph External_Services["🌐 External Services"]
        Qwen[Qwen LLM API]
        TTS[TTS Service]
    end
    
    RN -->|Voice Input| Voice
    RN -->|HTTP POST| FastAPI
    FastAPI --> Router
    Router -->|Query| PostgreSQL
    Router -->|Publish| RabbitMQ
    Router -->|Fallback| LLM_Fallback
    LLM_Fallback -->|Request| Qwen
    LLM_Fallback -->|Generate| TTS
    RabbitMQ -->|Consume| PC_Agent
    RabbitMQ -->|Consume| Controller_Agent
    FastAPI -->|Response| RN
    RN -->|Play| Audio
    
    style Client_Layer fill:#e1f5ff
    style API_Layer fill:#fff4e1
    style Data_Layer fill:#e8f5e9
    style Agent_Layer fill:#fce4ec
    style External_Services fill:#f3e5f5
```

---

## Диаграмма состояний команды

```mermaid
stateDiagram-v2
    [*] --> Received: Клиент отправляет команду
    Received --> Checking: Проверка активационного слова
    Checking --> Ignored: Нет слова "Мия"
    Checking --> Searching: Слово найдено
    Searching --> Found: Команда в БД
    Searching --> NotFound: Команды нет в БД
    Found --> Queued: Публикация в RabbitMQ
    Queued --> Executing: PC Agent получил
    Executing --> Completed: Успешное выполнение
    Executing --> Failed: Ошибка выполнения
    NotFound --> LLM_Query: Запрос к Qwen
    LLM_Query --> LLM_Response: Получен ответ
    LLM_Response --> TTS_Gen: Генерация аудио
    TTS_Gen --> ResponseSent: Отправка клиенту
    
    Ignored --> [*]
    Completed --> [*]
    Failed --> [*]
    ResponseSent --> [*]
    
    note right of Checking
      Оркестратор проверяет
      наличие "Мия" в тексте
    end note
    
    note right of Queued
      Статус 202 Accepted
      возвращается клиенту
    end note
    
    note right of LLM_Query
      Fallback механизм
      для неизвестных команд
    end note
```

---

## Пояснения к диаграммам

### Ключевые моменты:

1. **Асинхронность**: После публикации в RabbitMQ Orchestrator сразу возвращает ответ клиенту (202 Accepted), не дожидаясь выполнения команды агентом.

2. **Активационное слово**: Все команды игнорируются без слова "Мия" - это предотвращает ложные срабатывания.

3. **Fallback к LLM**: Если команда не найдена в базе, система использует Qwen для генерации ответа, что делает ассистента более гибким.

4. **Масштабируемость**: Архитектура позволяет добавлять новые типы агентов (Controller Agent для умного дома) без изменения ядра системы.

### Поток данных:

```
Голос → Текст → Orchestrator → [БД или LLM] → [RabbitMQ или TTS] → Клиент
```
