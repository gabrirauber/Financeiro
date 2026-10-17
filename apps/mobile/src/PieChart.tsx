import React from 'react';
import { Pressable, Text, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import { Card, palette, ThemeMode } from './ui';

export type PieSegment = {
  id: string;
  label: string;
  value: number;
  color: string;
  onPress?: () => void;
};

const lightColors = ['#123A62', '#E9650B', '#29699A', '#B64D2C', '#4765A5', '#B16A17', '#5A75A0', '#D65D53'];
const darkColors = ['#83B9EA', '#FF9C45', '#73D0E7', '#FFBE78', '#A6AEFF', '#F3C779', '#9EC6E7', '#F7A6A0'];

export function chartColor(index: number, theme: ThemeMode) {
  const colors = theme === 'dark' ? darkColors : lightColors;
  return colors[index % colors.length];
}

function point(angle: number) {
  const radians = (angle - 90) * Math.PI / 180;
  return { x: 110 + 100 * Math.cos(radians), y: 110 + 100 * Math.sin(radians) };
}

function slice(start: number, size: number) {
  const from = point(start);
  const to = point(start + size);
  return `M 110 110 L ${from.x} ${from.y} A 100 100 0 ${size > 180 ? 1 : 0} 1 ${to.x} ${to.y} Z`;
}

function percentage(value: number, total: number) {
  return `${(value / total * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

export function PieChart({ title, segments }: { title: string; segments: PieSegment[] }) {
  const visible = segments.filter(item => item.value > 0);
  const total = visible.reduce((sum, item) => sum + item.value, 0);
  if (!total) return null;
  let angle = 0;
  return <Card>
    <Text style={{ fontSize: 17, fontWeight: '700', color: palette.ink }}>{title}</Text>
    <View style={{ alignItems: 'center' }}>
      <Svg width={220} height={220} viewBox="0 0 220 220" accessibilityLabel={title}>
        {visible.map(item => {
          const start = angle;
          const size = item.value / total * 360;
          angle += size;
          return visible.length === 1 ?
            <Circle key={item.id} cx={110} cy={110} r={100} fill={item.color} onPress={item.onPress} /> :
            <Path key={item.id} d={slice(start, size)} fill={item.color}
              stroke={palette.white} strokeWidth={2} onPress={item.onPress} />;
        })}
      </Svg>
    </View>
    {visible.map(item => <Pressable key={item.id} accessibilityRole={item.onPress ? 'button' : 'text'}
      accessibilityLabel={`${item.label}, ${percentage(item.value, total)}`}
      onPress={item.onPress} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 40 }}>
      <View style={{ width: 14, height: 14, borderRadius: 4, backgroundColor: item.color }} />
      <Text style={{ flex: 1, color: palette.ink }}>{item.label}</Text>
      <Text style={{ color: palette.ink, fontWeight: '700' }}>{percentage(item.value, total)}{item.onPress ? ' ›' : ''}</Text>
    </Pressable>)}
  </Card>;
}
