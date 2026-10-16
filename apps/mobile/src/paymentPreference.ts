import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

export type PaymentMethod = 'pix' | 'debit' | 'cash' | 'credit';
export type PaymentPreference = { method: PaymentMethod; cardId?: string };

const key = (workspaceId: string) => `meu-controle.payment.${workspaceId}`;
const isMethod = (value: unknown): value is PaymentMethod =>
  value === 'pix' || value === 'debit' || value === 'cash' || value === 'credit';

export async function readPaymentPreference(workspaceId: string): Promise<PaymentPreference | null> {
  const saved = Platform.OS === 'web' ? localStorage.getItem(key(workspaceId)) :
    await SecureStore.getItemAsync(key(workspaceId));
  if (!saved) return null;
  try {
    const parsed: unknown = JSON.parse(saved);
    if (!parsed || typeof parsed !== 'object' || !('method' in parsed) ||
      !isMethod(parsed.method)) return null;
    return { method: parsed.method,
      cardId: 'cardId' in parsed && typeof parsed.cardId === 'string' ? parsed.cardId : undefined };
  } catch { return null; }
}

export async function savePaymentPreference(workspaceId: string, preference: PaymentPreference) {
  const value = JSON.stringify(preference);
  if (Platform.OS === 'web') localStorage.setItem(key(workspaceId), value);
  else await SecureStore.setItemAsync(key(workspaceId), value);
}
