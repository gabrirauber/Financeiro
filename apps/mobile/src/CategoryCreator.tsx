import React, { useRef, useState } from 'react';
import { Text, TextInput, View } from 'react-native';
import { Button, palette } from './ui';

export function CategoryCreator({ kind, existing, onCreate }: {
  kind: 'categoria' | 'subcategoria'; existing: string[];
  onCreate: (name: string) => Promise<void> | void;
}) {
  const input = useRef<TextInput>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  function close() {
    input.current?.blur();
    setOpen(false); setName(''); setError('');
  }
  async function create() {
    const clean = name.trim().replace(/\s+/g, ' ');
    if (!clean) return setError(`Informe o nome da ${kind}.`);
    if (existing.some(value => value.normalize('NFC').toLocaleLowerCase('pt-BR') === clean.normalize('NFC').toLocaleLowerCase('pt-BR'))) return setError(`Esta ${kind} já existe.`);
    setBusy(true); setError('');
    try {
      await onCreate(clean);
      close();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível cadastrar.'); }
    finally { setBusy(false); }
  }
  return <View style={{ gap: 10 }}>
    <TextInput ref={input} accessibilityLabel={`Nome da ${kind}`}
      placeholder={`Nova ${kind}`} value={name} maxLength={40} editable={!busy}
      onFocus={() => setOpen(true)}
      onChangeText={value => { setName(value); setError(''); }}
      style={{ borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, backgroundColor: 'white', fontSize: 16, color: palette.ink }} />
    {!!error && <Text accessibilityRole="alert" style={{ color: '#923D2B' }}>{error}</Text>}
    {open && <View style={{ gap: 8 }}>
      <Button label={busy ? 'Cadastrando…' : 'Criar'} onPress={() => { if (!busy) void create(); }} />
      <Button label="Cancelar" secondary onPress={close} />
    </View>}
  </View>;
}
