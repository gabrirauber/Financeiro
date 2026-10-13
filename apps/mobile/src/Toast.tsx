import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { palette } from './ui';

type Tone = 'success' | 'error';
type ToastItem = { id: number; message: string; tone: Tone };
type ToastContextValue = { show: (message: string, tone?: Tone) => void; clear: (tone: Tone) => void; item: ToastItem | null; dismiss: () => void };
const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [item, setItem] = useState<ToastItem | null>(null);
  const nextId = useRef(0);
  const show = useCallback((message: string, tone: Tone = 'success') => {
    if (message.trim()) setItem({ id: ++nextId.current, message: message.trim(), tone });
  }, []);
  const dismiss = useCallback(() => setItem(null), []);
  const clear = useCallback((tone: Tone) => setItem(current => current?.tone === tone ? null : current), []);
  useEffect(() => {
    if (!item) return;
    const timeout = setTimeout(() => setItem(current => current?.id === item.id ? null : current),
      item.tone === 'error' ? 5000 : 3500);
    return () => clearTimeout(timeout);
  }, [item]);
  return <ToastContext.Provider value={{ show, clear, item, dismiss }}>{children}</ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('ToastProvider ausente.');
  return context;
}

export function useToastSetter(tone: Tone) {
  const { show, clear } = useToast();
  return useCallback((message: string) => message.trim() ? show(message, tone) : clear(tone),
    [show, clear, tone]);
}

export function ToastViewport({ bottom = 96 }: { bottom?: number }) {
  const { item, dismiss } = useToast();
  if (!item) return null;
  return <View pointerEvents="box-none" style={{ position: 'absolute', left: 16, right: 16, bottom,
    zIndex: 100, alignItems: 'center' }}>
    <Pressable accessibilityRole="button" accessibilityLabel={`${item.message}. Toque para dispensar`}
      onPress={dismiss} style={{ maxWidth: 560, width: '100%', borderRadius: 16, paddingVertical: 14,
        paddingHorizontal: 18, backgroundColor: item.tone === 'error' ? '#923D2B' : '#20362F',
        shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 12, elevation: 8 }}>
      <Text accessibilityLiveRegion={item.tone === 'error' ? 'assertive' : 'polite'}
        style={{ color: 'white', fontSize: 15, fontWeight: '600', lineHeight: 21 }}>{item.message}</Text>
    </Pressable>
  </View>;
}
