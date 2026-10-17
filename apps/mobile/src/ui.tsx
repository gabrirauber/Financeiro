import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

export type ThemeMode = 'light' | 'dark';
const light = {
  bg: '#F6F8FC', ink: '#0C2747', muted: '#52677E', green: '#123A62',
  accent: '#E9650B', line: '#DCE5EF', white: '#FFFFFF', soft: '#E8F0F8',
  track: '#E8EDF3', danger: '#B63F32', hero: '#0C2B4D', bank: '#123A62',
  heroMuted: '#D8E9F8', heroLine: '#40617F',
};
const dark = {
  bg: '#0B1523', ink: '#F3F7FC', muted: '#B4C5D8', green: '#FF9C45',
  accent: '#FF9C45', line: '#344A63', white: '#15263B', soft: '#223851',
  track: '#2C4058', danger: '#FFA297', hero: '#102B48', bank: '#1B3856',
  heroMuted: '#D9E8F6', heroLine: '#4A6785',
};
export const palette = { ...light };
export function applyTheme(mode: ThemeMode) { Object.assign(palette, mode === 'dark' ? dark : light); }
const makeStyles = () => StyleSheet.create({
  card: { backgroundColor: palette.white, borderRadius: 22, padding: 20, borderWidth: 1, borderColor: palette.line, gap: 12 },
  button: { minHeight: 50, backgroundColor: palette.green, borderRadius: 14, alignItems: 'center', justifyContent: 'center', padding: 14 },
  buttonText: { color: palette.bg, fontWeight: '700', fontSize: 16 },
  secondary: { backgroundColor: palette.soft },
  chip: { minHeight: 46, paddingHorizontal: 14, paddingVertical: 12, borderRadius: 14, backgroundColor: palette.soft, justifyContent: 'center' },
  selected: { backgroundColor: palette.green },
});
export function Button({ label, onPress, secondary = false, disabled = false }: { label: string; onPress: () => void; secondary?: boolean; disabled?: boolean }) {
  const styles = makeStyles();
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.button, secondary && styles.secondary, disabled && { opacity: 0.5 }, pressed && { opacity: 0.7 }]}>
    <Text style={[styles.buttonText, secondary && { color: palette.green }]}>{label}</Text>
  </Pressable>;
}
export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const styles = makeStyles();
  return <Pressable accessibilityRole="button" accessibilityState={{ selected }} onPress={onPress} style={[styles.chip, selected && styles.selected]}>
    <Text style={{ color: selected ? palette.bg : palette.ink, fontWeight: '600' }}>{label}</Text>
  </Pressable>;
}
export function Card({ children }: { children: React.ReactNode }) { return <View style={makeStyles().card}>{children}</View>; }
