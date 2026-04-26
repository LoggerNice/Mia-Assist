"""
PC Agent - Сервис для выполнения системных команд на компьютере пользователя
Голосовой ассистент "Мия"

Этот модуль отвечает за:
- Подписку на очередь RabbitMQ pc_commands_queue
- Парсинг команд и выполнение действий через subprocess
- Обработку различных типов команд (запуск приложений, системные команды, поиск)
"""

import asyncio
import aio_pika
import json
import subprocess
import os
import sys
from typing import Dict, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod


# ============================================
# Конфигурация
# ============================================

class Config:
    """Конфигурация PC Agent"""
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    PC_COMMANDS_QUEUE: str = "pc_commands_queue"
    
    # Пути к приложениям (можно переопределить через переменные окружения)
    STEAM_PATH: str = os.getenv("STEAM_PATH", r"C:\Program Files (x86)\Steam\Steam.exe")
    DISCORD_PATH: str = os.getenv("DISCORD_PATH", r"C:\Users\%USER%\AppData\Local\Discord\Update.exe")
    OPERA_PATH: str = os.getenv("OPERA_PATH", r"C:\Program Files\Opera\launcher.exe")
    DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", r"C:\Users\%USER%\Documents")


config = Config()


# ============================================
# Типы команд (Enum)
# ============================================

class ActionType(str, Enum):
    """Перечень поддерживаемых типов действий"""
    LAUNCH_APP = "LAUNCH_APP"      # Запуск приложения
    SYSTEM_CMD = "SYSTEM_CMD"       # Системная команда
    SEARCH = "SEARCH"               # Поиск в браузере
    OPEN_FOLDER = "OPEN_FOLDER"     # Открытие папки
    SMART_HOME = "SMART_HOME"       # Умный дом (будущее расширение)
    GREETING = "GREETING"           # Приветствие


# ============================================
# Базовый класс обработчика команд
# ============================================

class CommandHandler(ABC):
    """Абстрактный базовый класс для обработчиков команд"""
    
    @abstractmethod
    async def execute(self, payload: Dict[str, Any]) -> bool:
        """
        Выполнение команды
        
        Args:
            payload: Параметры команды из JSON
            
        Returns:
            bool: True если успешно, False иначе
        """
        pass
    
    def log(self, message: str, success: bool = True):
        """Логирование выполнения команды"""
        status = "✓" if success else "✗"
        print(f"[{status}] {message}")


# ============================================
# Конкретные обработчики команд
# ============================================

class LaunchAppHandler(CommandHandler):
    """Обработчик команд запуска приложений"""
    
    async def execute(self, payload: Dict[str, Any]) -> bool:
        app_name = payload.get("app_name", "Неизвестное приложение")
        executable_path = payload.get("executable_path", "")
        arguments = payload.get("arguments", "")
        
        self.log(f"Запуск приложения: {app_name}")
        
        try:
            # Подставляем переменные окружения (например, %USER%)
            executable_path = os.path.expandvars(executable_path)
            
            # Формируем команду
            cmd = [executable_path]
            if arguments:
                cmd.extend(arguments.split())
            
            # Запускаем процесс (не блокируя выполнение)
            if sys.platform == "win32":
                # Windows: используем CREATE_NEW_PROCESS_GROUP для независимого запуска
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Linux/Mac
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            self.log(f"Приложение {app_name} запущено", success=True)
            return True
            
        except FileNotFoundError:
            self.log(f"Файл не найден: {executable_path}", success=False)
            return False
        except Exception as e:
            self.log(f"Ошибка запуска {app_name}: {e}", success=False)
            return False


class SystemCommandHandler(CommandHandler):
    """Обработчик системных команд"""
    
    async def execute(self, payload: Dict[str, Any]) -> bool:
        command = payload.get("command", "")
        arguments = payload.get("arguments", "")
        description = payload.get("description", "Системная команда")
        
        self.log(f"Выполнение: {description}")
        
        try:
            # Формируем полную команду
            full_cmd = f"{command} {arguments}".strip()
            
            # Для безопасности проверяем разрешенные команды
            allowed_commands = ["shutdown", "restart", "logoff", "taskkill"]
            if command not in allowed_commands:
                self.log(f"Команда запрещена: {command}", success=False)
                return False
            
            # Выполняем команду
            if sys.platform == "win32":
                # Windows
                result = subprocess.run(
                    full_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5  # Таймаут для безопасности
                )
            else:
                # Linux/Mac (адаптируем команды)
                if command == "shutdown":
                    full_cmd = "shutdown -h now"
                elif command == "restart":
                    full_cmd = "reboot"
                
                result = subprocess.run(
                    full_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0 or result.returncode is None:
                # returncode=None нормален для shutdown/restart
                self.log(f"Команда выполнена: {description}", success=True)
                return True
            else:
                self.log(f"Ошибка выполнения: {result.stderr}", success=False)
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Таймаут выполнения команды", success=False)
            return False
        except Exception as e:
            self.log(f"Ошибка системной команды: {e}", success=False)
            return False


class SearchHandler(CommandHandler):
    """Обработчик команд поиска в браузере"""
    
    async def execute(self, payload: Dict[str, Any]) -> bool:
        browser = payload.get("browser", "Opera")
        search_engine = payload.get("search_engine", "https://www.google.com/search?q={query}")
        new_tab = payload.get("new_tab", True)
        
        # В MVP поиск без конкретного запроса открывает главную Google
        query = payload.get("query", "")
        
        self.log(f"Поиск в {browser}: {query if query else '(главная)'}")
        
        try:
            # Формируем URL
            if query:
                from urllib.parse import quote
                url = search_engine.replace("{query}", quote(query))
            else:
                url = "https://www.google.com"
            
            # Открываем URL в браузере по умолчанию
            import webbrowser
            
            if new_tab:
                webbrowser.open_new_tab(url)
            else:
                webbrowser.open(url)
            
            self.log(f"Поиск открыт в браузере", success=True)
            return True
            
        except Exception as e:
            self.log(f"Ошибка поиска: {e}", success=False)
            return False


class OpenFolderHandler(CommandHandler):
    """Обработчик команд открытия папок"""
    
    async def execute(self, payload: Dict[str, Any]) -> bool:
        folder_path = payload.get("folder_path", "")
        use_explorer = payload.get("explorer", True)
        
        self.log(f"Открытие папки: {folder_path}")
        
        try:
            # Подставляем переменные окружения
            folder_path = os.path.expandvars(folder_path)
            
            # Проверяем существование папки
            if not os.path.exists(folder_path):
                self.log(f"Папка не найдена: {folder_path}", success=False)
                return False
            
            # Открываем папку
            if sys.platform == "win32":
                if use_explorer:
                    subprocess.Popen(["explorer", folder_path])
                else:
                    os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            
            self.log(f"Папка открыта: {folder_path}", success=True)
            return True
            
        except Exception as e:
            self.log(f"Ошибка открытия папки: {e}", success=False)
            return False


class GreetingHandler(CommandHandler):
    """Обработчик приветственных команд"""
    
    async def execute(self, payload: Dict[str, Any]) -> bool:
        default_answer = payload.get("default_answer", "Привет!")
        
        self.log(f"Приветствие: {default_answer}")
        
        # В реальной реализации здесь может быть отправка ответа обратно клиенту
        # или воспроизведение через TTS локально
        print(f"🤖 Мия: {default_answer}")
        
        return True


# ============================================
# Диспетчер команд (Command Dispatcher)
# ============================================

class CommandDispatcher:
    """
    Диспетчер команд - распределяет команды по обработчикам
    
    Использует паттерн Strategy для гибкого добавления новых типов команд
    """
    
    def __init__(self):
        # Регистрируем обработчики
        self.handlers: Dict[ActionType, CommandHandler] = {
            ActionType.LAUNCH_APP: LaunchAppHandler(),
            ActionType.SYSTEM_CMD: SystemCommandHandler(),
            ActionType.SEARCH: SearchHandler(),
            ActionType.OPEN_FOLDER: OpenFolderHandler(),
            ActionType.GREETING: GreetingHandler(),
            # SMART_HOME будет реализован в будущем
        }
    
    async def dispatch(self, action_type: str, payload: Dict[str, Any]) -> bool:
        """
        Диспетчеризация команды к соответствующему обработчику
        
        Args:
            action_type: Тип действия (строка)
            payload: Параметры команды
            
        Returns:
            bool: Результат выполнения
        """
        try:
            # Преобразуем строку в enum
            action = ActionType(action_type)
        except ValueError:
            print(f"[✗] Неизвестный тип действия: {action_type}")
            return False
        
        # Получаем обработчик
        handler = self.handlers.get(action)
        
        if not handler:
            print(f"[✗] Обработчик для {action} не зарегистрирован")
            return False
        
        # Выполняем команду
        return await handler.execute(payload)


# ============================================
# Слушатель очереди RabbitMQ
# ============================================

class RabbitMQListener:
    """
    Слушатель очереди RabbitMQ
    
    Подписывается на pc_commands_queue и передает команды диспетчеру
    """
    
    def __init__(self, dispatcher: CommandDispatcher):
        self.dispatcher = dispatcher
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
    
    async def connect(self):
        """Подключение к RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            
            # Объявляем очередь
            self.queue = await self.channel.declare_queue(
                config.PC_COMMANDS_QUEUE,
                durable=True
            )
            
            print("✓ Подключено к RabbitMQ")
            print(f"✓ Очередь: {config.PC_COMMANDS_QUEUE}")
            
        except Exception as e:
            print(f"✗ Ошибка подключения к RabbitMQ: {e}")
            raise
    
    async def process_message(self, message: aio_pika.IncomingMessage):
        """
        Обработка входящего сообщения
        
        Args:
            message: Сообщение из RabbitMQ
        """
        async with message.process():
            try:
                # Парсим JSON
                body = json.loads(message.body.decode('utf-8'))
                
                command_id = body.get("command_id")
                user_id = body.get("user_id")
                action_type = body.get("action_type")
                payload = body.get("payload", {})
                original_text = body.get("original_text", "")
                
                print(f"\n{'='*50}")
                print(f"📥 Получена команда #{command_id} от пользователя #{user_id}")
                print(f"   Текст: {original_text}")
                print(f"   Действие: {action_type}")
                print(f"{'='*50}")
                
                # Передаем команду диспетчеру
                success = await self.dispatcher.dispatch(action_type, payload)
                
                if success:
                    print(f"✓ Команда #{command_id} выполнена успешно")
                else:
                    print(f"✗ Команда #{command_id} выполнена с ошибкой")
                
            except json.JSONDecodeError as e:
                print(f"✗ Ошибка парсинга JSON: {e}")
            except Exception as e:
                print(f"✗ Ошибка обработки сообщения: {e}")
    
    async def start_listening(self):
        """Запуск прослушивания очереди"""
        if not self.queue:
            raise RuntimeError("Сначала необходимо подключиться к RabbitMQ")
        
        print(f"\n🎧 Начинаю прослушивание очереди {config.PC_COMMANDS_QUEUE}...")
        print("Нажмите Ctrl+C для остановки\n")
        
        # Начинаем потреблять сообщения
        await self.queue.consume(self.process_message)
        
        # Держим соединение активным
        while True:
            await asyncio.sleep(1)
    
    async def close(self):
        """Закрытие соединения"""
        if self.connection:
            await self.connection.close()
            print("✓ Соединение с RabbitMQ закрыто")


# ============================================
# Главная функция
# ============================================

async def main():
    """Точка входа приложения"""
    print("="*60)
    print("🤖 PC Agent голосового ассистента 'Мия'")
    print("="*60)
    
    # Создаем диспетчер
    dispatcher = CommandDispatcher()
    
    # Создаем слушателя
    listener = RabbitMQListener(dispatcher)
    
    try:
        # Подключаемся
        await listener.connect()
        
        # Начинаем слушать очередь
        await listener.start_listening()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Получен сигнал остановки")
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
    finally:
        # Закрываем соединение
        await listener.close()
        print("\n👋 PC Agent остановлен")


if __name__ == "__main__":
    # Запускаем асинхронный цикл
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
