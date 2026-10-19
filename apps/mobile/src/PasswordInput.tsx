import React, { useState } from 'react';
import { Pressable, TextInput, TextInputProps, View } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import { palette } from './ui';

export function PasswordInput(props: TextInputProps) {
  const [visible, setVisible] = useState(false);
  return <View style={{ position: 'relative' }}>
    <TextInput {...props} autoCapitalize="none" autoCorrect={false} secureTextEntry={!visible}
      style={[props.style, { paddingRight: 54 }]} />
    <Pressable accessibilityRole="button" accessibilityLabel={`${visible ? 'Ocultar' : 'Mostrar'} ${props.accessibilityLabel?.toLowerCase() || 'senha'}`}
      disabled={props.editable === false} onPress={() => setVisible(value => !value)}
      style={{ position: 'absolute', right: 2, top: 0, bottom: 0, width: 48, minHeight: 44, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke={palette.ink} strokeWidth={1.8}>
        <Path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
        <Circle cx={12} cy={12} r={3} />
        {visible && <Path d="M3 3 21 21" />}
      </Svg>
    </Pressable>
  </View>;
}
