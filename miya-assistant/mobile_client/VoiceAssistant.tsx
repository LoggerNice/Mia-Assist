/**
 * React Native Client - Голосовой ассистент "Мия"
 * 
 * Этот модуль содержит примеры функций для:
 * - Отправки голосовых команд на бэкенд
 * - Обработки ответа (воспроизведение аудио или показ статуса)
 */

import { useState, useCallback } from 'react';
import { Alert, Platform } from 'react-native';
import Voice from '@react-native-voice/voice';
import Sound from 'react-native-sound';

// ============================================
// Типы и интерфейсы
// ============================================

interface CommandRequest {
  text: string;
  user_id: number;
}

interface CommandResponse {
  status: 'accepted' | 'ignored' | 'llm_response' | 'error';
  message: string;
  audio_url?: string | null;
  command_id?: number | null;
}

interface UseVoiceAssistantReturn {
  isListening: boolean;
  isProcessing: boolean;
  lastResponse: CommandResponse | null;
  startListening: () => Promise<void>;
  stopListening: () => Promise<void>;
  sendTextCommand: (text: string) => Promise<void>;
  cleanup: () => void;
}

// ============================================
// Конфигурация API
// ============================================

const API_BASE_URL = 'http://localhost:8000/api'; // Замените на ваш сервер
const USER_ID = 1; // В реальности берется из контекста авторизации

// ============================================
// Хук для работы с голосовым ассистентом
// ============================================

/**
 * Хук для управления голосовым ассистентом Мия
 * 
 * @returns Объект с методами и состоянием для работы с ассистентом
 */
export function useVoiceAssistant(): UseVoiceAssistantReturn {
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [lastResponse, setLastResponse] = useState<CommandResponse | null>(null);
  const [audioSound, setAudioSound] = useState<Sound | null>(null);

  /**
   * Отправка текстовой команды на сервер
   * 
   * @param text Текст команды (должен содержать активационное слово "Мия")
   */
  const sendTextCommand = useCallback(async (text: string): Promise<void> => {
    setIsProcessing(true);
    setLastResponse(null);

    try {
      const requestBody: CommandRequest = {
        text: text,
        user_id: USER_ID,
      };

      console.log(`📤 Отправка команды: ${text}`);

      const response = await fetch(`${API_BASE_URL}/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP ошибка: ${response.status}`);
      }

      const data: CommandResponse = await response.json();
      console.log(`📥 Получен ответ:`, data);

      setLastResponse(data);

      // Обработка ответа в зависимости от статуса
      handleResponse(data);

    } catch (error) {
      console.error('❌ Ошибка отправки команды:', error);
      
      const errorMessage: CommandResponse = {
        status: 'error',
        message: error instanceof Error ? error.message : 'Неизвестная ошибка',
      };
      
      setLastResponse(errorMessage);
      Alert.alert('Ошибка', 'Не удалось отправить команду. Проверьте соединение.');
    } finally {
      setIsProcessing(false);
    }
  }, []);

  /**
   * Обработка ответа от сервера
   * 
   * @param response Ответ от сервера
   */
  const handleResponse = useCallback((response: CommandResponse): void => {
    switch (response.status) {
      case 'accepted':
        // Команда принята к исполнению
        console.log('✅', response.message);
        // Можно показать уведомление пользователю
        break;

      case 'ignored':
        // Команда проигнорирована (нет активационного слова)
        console.log('⚠️', response.message);
        Alert.alert('Подсказка', 'Скажите "Мия" перед командой');
        break;

      case 'llm_response':
        // Ответ от LLM
        console.log('🤖 LLM ответ:', response.message);
        
        // Если есть аудио, воспроизводим его
        if (response.audio_url) {
          playAudio(response.audio_url);
        } else {
          // Показываем текст ответа
          Alert.alert('Мия', response.message);
        }
        break;

      case 'error':
        // Ошибка
        console.error('❌', response.message);
        Alert.alert('Ошибка', response.message);
        break;

      default:
        console.warn('⚠️ Неизвестный статус:', response);
    }
  }, []);

  /**
   * Воспроизведение аудио ответа
   * 
   * @param url URL аудиофайла
   */
  const playAudio = useCallback((url: string): void => {
    // Останавливаем предыдущее воспроизведение
    if (audioSound) {
      audioSound.stop();
      audioSound.release();
    }

    // Создаем новый звуковой объект
    Sound.setCategory('Playback');
    
    const sound = new Sound(url, '', (error) => {
      if (error) {
        console.error('❌ Ошибка загрузки аудио:', error);
        return;
      }
      
      console.log('🔊 Воспроизведение аудио...');
      sound.play((success) => {
        if (success) {
          console.log('✅ Воспроизведение завершено');
        } else {
          console.error('❌ Ошибка воспроизведения');
        }
      });
      
      setAudioSound(sound);
    });
  }, [audioSound]);

  /**
   * Начало прослушивания голоса
   */
  const startListening = useCallback(async (): Promise<void> => {
    try {
      // Проверяем доступность распознавания речи
      const available = await Voice.isAvailable();
      if (!available) {
        Alert.alert('Ошибка', 'Распознавание речи недоступно на этом устройстве');
        return;
      }

      // Начинаем запись
      await Voice.start('ru-RU');
      setIsListening(true);
      console.log('🎤 Прослушивание начато...');
      
    } catch (error) {
      console.error('❌ Ошибка начала прослушивания:', error);
      Alert.alert('Ошибка', 'Не удалось начать распознавание речи');
    }
  }, []);

  /**
   * Остановка прослушивания голоса
   */
  const stopListening = useCallback(async (): Promise<void> => {
    try {
      await Voice.stop();
      setIsListening(false);
      console.log('🛑 Прослушивание остановлено');
    } catch (error) {
      console.error('❌ Ошибка остановки прослушивания:', error);
    }
  }, []);

  /**
   * Очистка ресурсов при размонтировании
   */
  const cleanup = useCallback((): void => {
    if (audioSound) {
      audioSound.stop();
      audioSound.release();
      setAudioSound(null);
    }
    
    Voice.destroy().then(() => {
      console.log('🧹 Ресурсы голоса очищены');
    });
  }, [audioSound]);

  // ============================================
  // Настройка обработчиков событий Voice
  // ============================================

  Voice.onSpeechStart = () => {
    console.log('🎙️ Распознавание речи началось');
  };

  Voice.onSpeechEnd = () => {
    console.log('🎙️ Распознавание речи завершено');
    stopListening();
  };

  Voice.onSpeechResults = (event) => {
    const results = event.value;
    if (results && results.length > 0) {
      const recognizedText = results[0];
      console.log('📝 Распознанный текст:', recognizedText);
      
      // Автоматически отправляем команду после распознавания
      sendTextCommand(recognizedText);
    }
  };

  Voice.onSpeechError = (event) => {
    console.error('❌ Ошибка распознавания речи:', event.error?.message);
    stopListening();
    setIsListening(false);
  };

  return {
    isListening,
    isProcessing,
    lastResponse,
    startListening,
    stopListening,
    sendTextCommand,
    cleanup,
  };
}

// ============================================
// Пример компонента React Native
// ============================================

/**
 * Пример использования хука в компоненте
 * 
 * Этот код можно использовать как шаблон для создания UI
 */
export const VoiceAssistantButton = () => {
  const {
    isListening,
    isProcessing,
    lastResponse,
    startListening,
    stopListening,
    cleanup,
  } = useVoiceAssistant();

  // Очистка при размонтировании
  React.useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  // Обработчик нажатия кнопки
  const handlePress = async () => {
    if (isListening) {
      await stopListening();
    } else {
      await startListening();
    }
  };

  return (
    <View style={styles.container}>
      {/* Кнопка активации голоса */}
      <TouchableOpacity
        onPress={handlePress}
        disabled={isProcessing}
        style={[
          styles.button,
          isListening && styles.buttonListening,
          isProcessing && styles.buttonProcessing,
        ]}
      >
        <Text style={styles.buttonText}>
          {isProcessing ? '⏳ Обработка...' : isListening ? '🛑 Стоп' : '🎤 Скажите команду'}
        </Text>
      </TouchableOpacity>

      {/* Индикатор состояния */}
      {lastResponse && (
        <View style={styles.responseContainer}>
          <Text style={styles.statusText}>
            Статус: {lastResponse.status}
          </Text>
          <Text style={styles.messageText}>
            {lastResponse.message}
          </Text>
        </View>
      )}

      {/* Подсказка */}
      <Text style={styles.hint}>
        Примеры команд:{"\n"}
        • "Мия, запусти стим"{"\n"}
        • "Мия, выключи компьютер"{"\n"}
        • "Мия, открой документы"
      </Text>
    </View>
  );
};

// ============================================
// Стили (пример)
// ============================================

const styles = {
  container: {
    padding: 20,
    alignItems: 'center',
  },
  button: {
    backgroundColor: '#4A90E2',
    paddingHorizontal: 30,
    paddingVertical: 15,
    borderRadius: 30,
    marginVertical: 20,
  },
  buttonListening: {
    backgroundColor: '#E74C3C',
    animation: 'pulse 1s infinite',
  },
  buttonProcessing: {
    backgroundColor: '#95A5A6',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  responseContainer: {
    backgroundColor: '#F5F5F5',
    padding: 15,
    borderRadius: 10,
    marginTop: 10,
    width: '100%',
  },
  statusText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#666666',
    marginBottom: 5,
  },
  messageText: {
    fontSize: 16,
    color: '#333333',
  },
  hint: {
    marginTop: 20,
    fontSize: 12,
    color: '#999999',
    textAlign: 'center',
  },
};

export default useVoiceAssistant;
