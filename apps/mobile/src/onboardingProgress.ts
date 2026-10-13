import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const key = (userId: string) => `meu-controle.onboarding.${userId}`;

// A ausência da chave distingue quem já usava o app antes da introdução do guia.
export async function readOnboardingStep(userId: string): Promise<number | null> {
  const saved = Platform.OS === 'web' ? localStorage.getItem(key(userId)) : await SecureStore.getItemAsync(key(userId));
  if (saved === null) return null;
  const step = Number(saved);
  return Number.isInteger(step) && step >= 0 && step <= 4 ? step : null;
}

export async function saveOnboardingStep(userId: string, step: number) {
  const value = String(step);
  if (Platform.OS === 'web') localStorage.setItem(key(userId), value);
  else await SecureStore.setItemAsync(key(userId), value);
}
