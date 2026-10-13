import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { ThemeMode } from './ui';

const KEY = 'meu-controle.theme';

export async function readThemePreference(): Promise<ThemeMode> {
  const value = Platform.OS === 'web' ? localStorage.getItem(KEY) : await SecureStore.getItemAsync(KEY);
  return value === 'dark' ? 'dark' : 'light';
}

export async function saveThemePreference(mode: ThemeMode) {
  if (Platform.OS === 'web') localStorage.setItem(KEY, mode);
  else await SecureStore.setItemAsync(KEY, mode);
}
