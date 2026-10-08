import React, { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { accounts, cards, categories, Expense, localDate, parseCents, validDate } from './prototype';
import { Button, Chip, palette } from './ui';

export function ExpenseForm({ onCancel, onSave }: { onCancel: () => void; onSave: (expense: Expense) => void }) {
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('');
  const [subcategory, setSubcategory] = useState('');
  const [date, setDate] = useState(localDate());
  const [payment, setPayment] = useState('Pix');
  const [source, setSource] = useState(accounts[0]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { setError(''); }, [amount, category, subcategory, date, payment, source, note]);
  const selected = categories.find(item => item.id === category);
  const options = payment === 'Crédito' ? cards : payment === 'Dinheiro' ? [accounts[1]] : accounts;
  function save() {
    const cents = parseCents(amount);
    if (!cents) return setError('Informe um valor maior que zero. Exemplo: 45,90.');
    if (!selected) return setError('Escolha uma categoria.');
    if (!selected.subcategories.some(item => item === subcategory)) return setError('Escolha uma subcategoria.');
    if (!validDate(date)) return setError('Informe uma data válida no formato DD/MM/AAAA.');
    setError('');
    onSave({ id: `${Date.now()}-${Math.random()}`, cents, category, subcategory, date, payment, source, note: note.trim() });
  }
  return <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <View><Text style={s.eyebrow}>LANÇAMENTO RÁPIDO</Text><Text style={s.title}>Nova despesa</Text><Text style={s.hint}>Simulação • fica apenas nesta sessão.</Text></View>
      <Text style={s.label}>Valor *</Text>
      <View style={s.amountRow}><Text style={s.currency}>R$</Text><TextInput accessibilityLabel="Valor da despesa" placeholder="0,00" placeholderTextColor="#829187" keyboardType="decimal-pad" value={amount} onChangeText={setAmount} style={s.amount} maxLength={14} /></View>
      <Text style={s.label}>Categoria *</Text>
      <View style={s.wrap}>{categories.map(item => <Chip key={item.id} label={item.name} selected={category === item.id} onPress={() => { setCategory(item.id); setSubcategory(''); }} />)}</View>
      <Text style={s.label}>Subcategoria *</Text>
      <View style={s.wrap}>{selected ? selected.subcategories.map(item => <Chip key={item} label={item} selected={subcategory === item} onPress={() => setSubcategory(item)} />) : <Text style={s.hint}>Escolha a categoria para ver as opções.</Text>}</View>
      <Text style={s.label}>Data da compra *</Text>
      <TextInput accessibilityLabel="Data da compra" style={s.input} value={date} onChangeText={setDate} placeholder="DD/MM/AAAA" keyboardType="numbers-and-punctuation" maxLength={10} />
      <Text style={s.label}>Forma de pagamento *</Text>
      <View style={s.wrap}>{['Pix', 'Débito', 'Dinheiro', 'Crédito'].map(item => <Chip key={item} label={item} selected={payment === item} onPress={() => { setPayment(item); setSource(item === 'Crédito' ? cards[0] : item === 'Dinheiro' ? accounts[1] : accounts[0]); }} />)}</View>
      <Text style={s.label}>{payment === 'Crédito' ? 'Cartão' : 'Conta de saída'} *</Text>
      <View style={s.wrap}>{options.map(item => <Chip key={item} label={item} selected={source === item} onPress={() => setSource(item)} />)}</View>
      {payment === 'Crédito' && <Text style={s.hint}>Nesta prévia, o valor aparece no mês da compra. Faturas e parcelas serão implementadas na E06.</Text>}
      <Text style={s.label}>Observação <Text style={s.hint}>(opcional)</Text></Text>
      <TextInput accessibilityLabel="Observação" placeholder="Algo para lembrar?" style={[s.input, { minHeight: 80 }]} value={note} onChangeText={setNote} multiline maxLength={300} />
      {!!error && <Text accessibilityRole="alert" accessibilityLiveRegion="assertive" style={s.error}>{error}</Text>}
      <Button label="Adicionar à simulação" onPress={save} />
      <Button label="Cancelar" onPress={onCancel} secondary />
    </ScrollView>
  </KeyboardAvoidingView>;
}
const s = StyleSheet.create({
  content: { padding: 24, gap: 12, paddingBottom: 40 }, title: { fontSize: 30, fontWeight: '700', color: palette.ink, marginVertical: 8 },
  eyebrow: { color: palette.green, fontSize: 12, letterSpacing: 2, fontWeight: '700' }, hint: { color: palette.muted, fontSize: 13, lineHeight: 20 },
  label: { color: palette.ink, fontSize: 15, fontWeight: '600', marginTop: 10 }, wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  input: { borderColor: palette.line, borderWidth: 1, backgroundColor: 'white', borderRadius: 14, padding: 15, fontSize: 16, color: palette.ink },
  amountRow: { flexDirection: 'row', alignItems: 'center', borderBottomWidth: 2, borderBottomColor: palette.green, paddingVertical: 8 },
  currency: { fontSize: 25, color: palette.muted, marginRight: 12 }, amount: { fontSize: 40, color: palette.ink, flex: 1, minHeight: 64 },
  error: { backgroundColor: '#FCE9E3', color: '#923D2B', padding: 14, borderRadius: 12 },
});
