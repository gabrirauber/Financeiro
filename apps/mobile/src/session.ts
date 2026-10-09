import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const KEY = 'financeiro.session';
// Na prévia web a sessão dura apenas nesta aba. Android usa armazenamento protegido.
export async function readSession() {
  return Platform.OS === 'web' ? sessionStorage.getItem(KEY) : SecureStore.getItemAsync(KEY);
}
export async function saveSession(token: string) {
  if (Platform.OS === 'web') sessionStorage.setItem(KEY, token);
  else await SecureStore.setItemAsync(KEY, token);
}
export async function clearSession() {
  if (Platform.OS === 'web') sessionStorage.removeItem(KEY);
  else await SecureStore.deleteItemAsync(KEY);
}
