
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Animated, Dimensions } from 'react-native';
import MicButton from '@/components/MicButton';

const { width, height } = Dimensions.get('window');

export default function App() {
  const [isRecording, setIsRecording] = useState(false);

  // === Анимация градиентного фона ===
  const animation = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.timing(animation, {
        toValue: 1,
        duration: 8000,
        useNativeDriver: true,
      })
    ).start();
  }, []);

  const backgroundColor1 = animation.interpolate({
    inputRange: [0, 0.25, 0.5, 0.75, 1],
    outputRange: ['#1a1a2e', '#16213e', '#0f3460', '#533483', '#1a1a2e'],
  });

  const backgroundColor2 = animation.interpolate({
    inputRange: [0, 0.25, 0.5, 0.75, 1],
    outputRange: ['#533483', '#e94560', '#1a1a2e', '#0f3460', '#533483'],
  });

  const backgroundColor3 = animation.interpolate({
    inputRange: [0, 0.25, 0.5, 0.75, 1],
    outputRange: ['#0f3460', '#16213e', '#e94560', '#1a1a2e', '#0f3460'],
  });

  return (
    <Animated.View style={[styles.container, { backgroundColor: backgroundColor1 }]}>
      {/* Цветные пятна фона */}
      <Animated.View style={[styles.blob, styles.blob1, { backgroundColor: backgroundColor2 }]} />
      <Animated.View style={[styles.blob, styles.blob2, { backgroundColor: backgroundColor3 }]} />
      <Animated.View style={[styles.blob, styles.blob3, { backgroundColor: backgroundColor2 }]} />
      

      {/* Контент */}
      <View style={styles.content}>
        <Text style={styles.title}>Голосовой помощник</Text>
        <Text style={styles.subtitle}>
          {isRecording ? 'Слушаю вас...' : 'Нажмите, чтобы начать'}
        </Text>

        {/* 🔘 Кнопка микрофона */}
        <MicButton onToggle={setIsRecording} />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    overflow: 'hidden',
  },
  blob: {
    position: 'absolute',
    borderRadius: 9999,
    opacity: 0.6,
    filter: 'blur(80px)',
  },
  blob1: {
    width: width * 0.9,
    height: width * 0.9,
    top: -width * 0.2,
    left: -width * 0.2,
  },
  blob2: {
    width: width * 0.8,
    height: width * 0.8,
    bottom: -width * 0.1,
    right: -width * 0.2,
  },
  blob3: {
    width: width * 0.6,
    height: width * 0.6,
    top: height * 0.4,
    left: width * 0.3,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    marginBottom: 80,
  },
});