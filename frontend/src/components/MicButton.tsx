// MicButton.tsx
import React, { useRef, useState, useCallback } from 'react';
import { View, Pressable, StyleSheet, Animated, Easing } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const RIPPLE_COUNT = 3;

interface MicButtonProps {
  onToggle?: (isRecording: boolean) => void;
}

export default function MicButton({ onToggle }: MicButtonProps) {
  const [isRecording, setIsRecording] = useState(false);

  const toggleRecording = () => {
    const newState = !isRecording;
    setIsRecording(newState);
    onToggle?.(newState);  // ← уведомляем родителя

    if (newState) {
      startRipples();
      startBreathing();
      Animated.timing(glow, { toValue: 1, duration: 300, useNativeDriver: true }).start();
    } else {
      stopRipples();
      breathe.stopAnimation();
      breathe.setValue(1);
      Animated.timing(glow, { toValue: 0, duration: 300, useNativeDriver: true }).start();
    }
  };

  // Анимации волн
  const rippleAnims = useRef(
    Array.from({ length: RIPPLE_COUNT }, () => new Animated.Value(0))
  ).current;

  // Анимация нажатия кнопки
  const scale = useRef(new Animated.Value(1)).current;

  // Анимация свечения
  const glow = useRef(new Animated.Value(0)).current;

  // Анимация "дыхания" во время записи
  const breathe = useRef(new Animated.Value(1)).current;

  const startRipples = useCallback(() => {
    // Запускаем волны каскадом с задержкой
    const animations = rippleAnims.map((anim, i) => {
      anim.setValue(0);
      return Animated.timing(anim, {
        toValue: 1,
        duration: 1800,
        delay: i * 400,
        easing: Easing.out(Easing.ease),
        useNativeDriver: true,
      });
    });
    Animated.loop(Animated.stagger(0, animations)).start();
  }, [rippleAnims]);

  const stopRipples = useCallback(() => {
    rippleAnims.forEach((anim) => anim.stopAnimation());
  }, [rippleAnims]);

  const startBreathing = useCallback(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(breathe, {
          toValue: 1.06,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(breathe, {
          toValue: 1,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, [breathe]);

  const onPressIn = () => {
    Animated.spring(scale, { toValue: 0.9, useNativeDriver: true }).start();
  };

  const onPressOut = () => {
    Animated.spring(scale, {
      toValue: 1,
      friction: 3,
      tension: 40,
      useNativeDriver: true,
    }).start();
    toggleRecording();
  };

  // Интерполяция для каждой волны
  const renderRipples = () =>
    rippleAnims.map((anim, i) => {
      const rippleScale = anim.interpolate({
        inputRange: [0, 1],
        outputRange: [1, 2.8],
      });
      const rippleOpacity = anim.interpolate({
        inputRange: [0, 0.4, 1],
        outputRange: [0, 0.45, 0],
      });

      return (
        <Animated.View
          key={i}
          pointerEvents="none"
          style={[
            styles.ripple,
            {
              transform: [{ scale: rippleScale }],
              opacity: isRecording ? rippleOpacity : 0,
            },
          ]}
        />
      );
    });

  // Свечение вокруг кнопки
  const glowOpacity = glow.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 0.5],
  });

  return (
    <View style={styles.wrapper}>
      {/* Волны */}
      {renderRipples()}

      {/* Свечение */}
      <Animated.View
        pointerEvents="none"
        style={[styles.glow, { opacity: glowOpacity }]}
      />

      {/* Кнопка */}
      <Animated.View
        style={{
          transform: [{ scale: Animated.multiply(scale, breathe) }],
        }}
      >
        <Pressable
          onPressIn={onPressIn}
          onPressOut={onPressOut}
          style={[
            styles.button,
            isRecording && styles.buttonActive,
          ]}
        >
          <View>
            <Ionicons
              name={isRecording ? 'stop' : 'mic'}
              size={44}
              color="#fff"
            />
          </View>
        </Pressable>
      </Animated.View>
    </View>
  );
}

const BUTTON_SIZE = 120;

const styles = StyleSheet.create({
  wrapper: {
    width: BUTTON_SIZE * 3,
    height: BUTTON_SIZE * 3,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ripple: {
    position: 'absolute',
    width: BUTTON_SIZE,
    height: BUTTON_SIZE,
    borderRadius: BUTTON_SIZE / 2,
    borderWidth: 2,
    borderColor: 'rgba(180, 28, 28, 0.8)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  glow: {
    position: 'absolute',
    width: BUTTON_SIZE * 1.6,
    height: BUTTON_SIZE * 1.6,
    borderRadius: BUTTON_SIZE * 0.8,
    backgroundColor: '#e945601e',
    shadowColor: '#e94560',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 60,
    elevation: 20,
  },
  button: {
    width: BUTTON_SIZE,
    height: BUTTON_SIZE,
    borderRadius: BUTTON_SIZE / 2,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.25)',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'visible',
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 10 },
    shadowOpacity: 0.9,
    shadowRadius: 20,
  },
  buttonActive: {
    backgroundColor: 'rgba(233, 69, 96, 0.35)',
    borderColor: 'rgba(233, 69, 96, 0.6)',
  },
});