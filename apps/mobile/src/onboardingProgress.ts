import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// Migra o progresso salvo nas versões anteriores para o servidor.
export async function readPreviousOnboardingStep(userId: string): Promise<number | null> {
  const key = `meu-controle.onboarding.${userId}`;
  const saved = Platform.OS === 'web'
    ? localStorage.getItem(key)
    : await SecureStore.getItemAsync(key);
  if (saved === null) return null;
  const step = Number(saved);
  return Number.isInteger(step) && step >= 0 && step <= 4 ? step : null;
}
