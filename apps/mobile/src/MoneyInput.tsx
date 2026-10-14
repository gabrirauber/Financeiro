import React from 'react';
import { TextInput, TextInputProps } from 'react-native';
import { formatMoneyInput } from './moneyInputFormat';

type MoneyInputProps = Omit<TextInputProps, 'value' | 'onChangeText'> & {
  value: string;
  onChangeText: (value: string) => void;
};

export function MoneyInput({ value, onChangeText, ...props }: MoneyInputProps) {
  return <TextInput keyboardType="number-pad" selectTextOnFocus {...props} value={value}
    onChangeText={raw => onChangeText(formatMoneyInput(raw, value))} />;
}
