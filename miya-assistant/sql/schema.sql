-- SQL Schema для голосового ассистента "Мия"
-- Версия: MVP 1.0
-- Дата создания: 2024

-- Создаем таблицу команд
CREATE TABLE IF NOT EXISTS commands (
    id SERIAL PRIMARY KEY,
    trigger_phrase TEXT[] NOT NULL, -- Массив синонимов команды
    target_entity VARCHAR(50) NOT NULL CHECK (target_entity IN ('PC', 'CONTROLLER', 'GENERAL')),
    action_type VARCHAR(100) NOT NULL,
    payload_template JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации поиска
-- Индекс по массиву триггерных фраз (GIN индекс для работы с массивами)
CREATE INDEX idx_commands_trigger_phrase ON commands USING GIN (trigger_phrase);

-- Индекс по целевой сущности для фильтрации
CREATE INDEX idx_commands_target_entity ON commands (target_entity);

-- Индекс по типу действия
CREATE INDEX idx_commands_action_type ON commands (action_type);

-- Композитный индекс для активных команд по целевой сущности
CREATE INDEX idx_commands_active_target ON commands (is_active, target_entity) WHERE is_active = TRUE;

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_commands_updated_at 
    BEFORE UPDATE ON commands 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Пример заполнения данными для MVP
-- ============================================

-- Команды для запуска приложений
INSERT INTO commands (trigger_phrase, target_entity, action_type, payload_template, is_active) VALUES
(ARRAY['запусти стим', 'открой стим', 'включи стим', 'steam'], 'PC', 'LAUNCH_APP', '{"app_name": "Steam", "executable_path": "C:\\Program Files (x86)\\Steam\\Steam.exe", "arguments": ""}'::jsonb, TRUE),

(ARRAY['запусти дискорд', 'открой дискорд', 'включи дискорд', 'discord'], 'PC', 'LAUNCH_APP', '{"app_name": "Discord", "executable_path": "C:\\Users\\%USER%\\AppData\\Local\\Discord\\Update.exe", "arguments": "--processStart Discord.exe"}'::jsonb, TRUE),

(ARRAY['запусти оперу', 'открой оперу', 'включи оперу', 'opera'], 'PC', 'LAUNCH_APP', '{"app_name": "Opera", "executable_path": "C:\\Program Files\\Opera\\launcher.exe", "arguments": ""}'::jsonb, TRUE);

-- Команда для поиска в браузере
INSERT INTO commands (trigger_phrase, target_entity, action_type, payload_template, is_active) VALUES
(ARRAY['найди в интернете', 'поиск', 'погугли', 'найти'], 'PC', 'SEARCH', '{"browser": "Opera", "search_engine": "https://www.google.com/search?q={query}", "new_tab": true}'::jsonb, TRUE);

-- Системные команды
INSERT INTO commands (trigger_phrase, target_entity, action_type, payload_template, is_active) VALUES
(ARRAY['выключи компьютер', 'выключи пк', 'завершение работы', 'выруби комп'], 'PC', 'SYSTEM_CMD', '{"command": "shutdown", "arguments": "/s /t 0", "description": "Выключение ПК"}'::jsonb, TRUE),

(ARRAY['открой документы', 'папка документы', 'мои документы'], 'PC', 'OPEN_FOLDER', '{"folder_path": "C:\\Users\\%USER%\\Documents", "explorer": true}'::jsonb, TRUE);

-- Команды для контроллера умного дома (задел на будущее)
INSERT INTO commands (trigger_phrase, target_entity, action_type, payload_template, is_active) VALUES
(ARRAY['включи свет', 'свет включи', 'освещение'], 'CONTROLLER', 'SMART_HOME', '{"device_type": "light", "action": "on", "room": "living_room"}'::jsonb, TRUE),

(ARRAY['выключи свет', 'свет выключи', 'погаси свет'], 'CONTROLLER', 'SMART_HOME', '{"device_type": "light", "action": "off", "room": "living_room"}'::jsonb, TRUE);

-- Общие команды (ответ через LLM)
INSERT INTO commands (trigger_phrase, target_entity, action_type, payload_template, is_active) VALUES
(ARRAY['как дела', 'привет', 'здравствуй'], 'GENERAL', 'GREETING', '{"response_type": "text", "default_answer": "Привет! Я Мия, ваш голосовой помощник."}'::jsonb, TRUE);

-- Проверка вставленных данных
SELECT id, trigger_phrase, target_entity, action_type, is_active FROM commands ORDER BY id;
