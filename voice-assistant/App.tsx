import './global.css';
import { StatusBar } from 'expo-status-bar';
import { useState, useEffect } from 'react';
import { View, TouchableOpacity, Animated, Text } from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';

export default function App() {
  const [isListening, setIsListening] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | undefined>(undefined);
  const scaleValue = new Animated.Value(1);

  useEffect(() => {
    (async () => {
      try {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          alert('Sorry, we need microphone permissions to work!');
        }
      } catch (error) {
        console.error('Error requesting microphone permissions:', error);
      }
    })();
  }, []);

  const startListening = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      setRecording(recording);
      setIsListening(true);

      // Анимация пульсации кнопки
      Animated.loop(
        Animated.sequence([
          Animated.timing(scaleValue, {
            toValue: 1.2,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(scaleValue, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      ).start();

    } catch (error) {
      console.error('Failed to start recording', error);
    }
  };

  const stopListening = async () => {
    try {
      if (recording) {
        await recording.stopAndUnloadAsync();
        setRecording(undefined);
      }
      
      setIsListening(false);
      scaleValue.setValue(1); // Сброс анимации

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: false,
      });
    } catch (error) {
      console.error('Failed to stop recording', error);
    }
  };

  const handlePress = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <View className="flex-1 relative bg-gradient-yandex">
      {/* Переливающийся градиентный фон как в Яндекс Музыке */}
      <View 
        className="absolute inset-0 bg-gradient-animated"
      />
      
      {/* Контент по центру */}
      <View className="flex-1 items-center justify-center">
        <Animated.View
          style={{
            transform: [{ scale: scaleValue }],
          }}
        >
          <TouchableOpacity
            onPress={handlePress}
            activeOpacity={0.8}
            className={`w-32 h-32 rounded-full items-center justify-center shadow-2xl ${
              isListening ? 'bg-white' : 'bg-white/90'
            }`}
            style={{
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 10 },
              shadowOpacity: 0.3,
              shadowRadius: 20,
              elevation: 10,
            }}
          >
            <Ionicons
              name={isListening ? 'mic' : 'mic-outline'}
              size={48}
              color={isListening ? '#ff6b6b' : '#333'}
            />
            
            {/* Индикатор записи вокруг кнопки */}
            {isListening && (
              <View 
                className="absolute inset-0 rounded-full border-4 border-red-500"
                style={{
                  opacity: 0.6,
                }}
              />
            )}
          </TouchableOpacity>
        </Animated.View>

        <Text className={`mt-8 text-xl font-semibold ${isListening ? 'text-white' : 'text-white/90'}`}>
          {isListening ? 'Слушаю...' : 'Нажмите для записи'}
        </Text>
      </View>

      <StatusBar style="light" />
    </View>
  );
}
