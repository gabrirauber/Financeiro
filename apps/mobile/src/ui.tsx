import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

export type ThemeMode = 'light' | 'dark';
const light = { bg: '#F6F5F0', ink: '#20362F', muted: '#66766E', green: '#285B49', line: '#E0E5DD', white: '#FFFFFF', soft: '#E9EFE8', track: '#F0F1EB', danger: '#AA422E' };
const dark = { bg: '#111B18', ink: '#EEF5EF', muted: '#B1C2B8', green: '#91D5AF', line: '#34473D', white: '#1C2A24', soft: '#293B31', track: '#34473D', danger: '#F4A28F' };
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
