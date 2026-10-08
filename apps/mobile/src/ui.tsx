import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

export const palette = { bg: '#F6F5F0', ink: '#20362F', muted: '#66766E', green: '#285B49', line: '#E0E5DD', white: '#FFFFFF' };
export function Button({ label, onPress, secondary = false }: { label: string; onPress: () => void; secondary?: boolean }) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.button, secondary && styles.secondary, pressed && { opacity: 0.7 }]}>
    <Text style={[styles.buttonText, secondary && { color: palette.green }]}>{label}</Text>
  </Pressable>;
}
export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ selected }} onPress={onPress} style={[styles.chip, selected && styles.selected]}>
    <Text style={{ color: selected ? palette.white : palette.ink, fontWeight: '600' }}>{label}</Text>
  </Pressable>;
}
export function Card({ children }: { children: React.ReactNode }) { return <View style={styles.card}>{children}</View>; }
export const styles = StyleSheet.create({
  card: { backgroundColor: palette.white, borderRadius: 22, padding: 20, borderWidth: 1, borderColor: palette.line, gap: 12 },
  button: { minHeight: 50, backgroundColor: palette.green, borderRadius: 14, alignItems: 'center', justifyContent: 'center', padding: 14 },
  buttonText: { color: 'white', fontWeight: '700', fontSize: 16 },
  secondary: { backgroundColor: '#E9EFE8' },
  chip: { minHeight: 46, paddingHorizontal: 14, paddingVertical: 12, borderRadius: 14, backgroundColor: '#EDF0E9', justifyContent: 'center' },
  selected: { backgroundColor: palette.green },
});
