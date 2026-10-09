import React, { useState } from 'react';
import { Text, TextInput, View } from 'react-native';
import { Button, palette } from './ui';

export function CategoryCreator({ kind, existing, onCreate }: {
  kind: 'categoria' | 'subcategoria'; existing: string[];
  onCreate: (name: string) => Promise<void> | void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function create() {
    const clean = name.trim().replace(/\s+/g, ' ');
    if (!clean) return setError(`Informe o nome da ${kind}.`);
    if (existing.some(value => value.normalize('NFC').toLocaleLowerCase('pt-BR') === clean.normalize('NFC').toLocaleLowerCase('pt-BR'))) return setError(`Esta ${kind} já existe.`);
    setBusy(true); setError('');
    try {
      await onCreate(clean);
      setName(''); setOpen(false);
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível cadastrar.'); }
    finally { setBusy(false); }
  }
  return <View style={{ gap: 10 }}>
    {!open ? <Button label={`+ Nova ${kind}`} secondary onPress={() => setOpen(true)} /> : <>
      <TextInput accessibilityLabel={`Nome da ${kind}`} placeholder={`Nome da ${kind}`} value={name} maxLength={40} onChangeText={value => { setName(value); setError(''); }} style={{ borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, backgroundColor: 'white', fontSize: 16, color: palette.ink }} />
      {!!error && <Text accessibilityRole="alert" style={{ color: '#923D2B' }}>{error}</Text>}
      <Button label={busy ? 'Cadastrando…' : `Criar ${kind}`} onPress={() => { if (!busy) void create(); }} />
      <Button label="Cancelar cadastro" secondary onPress={() => { setOpen(false); setName(''); setError(''); }} />
    </>}
  </View>;
}
