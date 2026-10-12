import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Account, Category, Expense, ExpenseInput, Subcategory, CreditCard, CardPurchaseInput, dateToDisplay, dateToIso, paymentLabel } from './finance';
import { localDate, parseCents, validDate } from './prototype';
import { CategoryCreator } from './CategoryCreator';
import { Button, Chip, palette } from './ui';
import { useToastSetter } from './Toast';

export function ExpenseForm({ onCancel, onSave, categories, accounts, onCategory, onSubcategory, onCreditSave, cards, initial }: {
  onCancel: () => void;
  onSave: (expense: ExpenseInput) => Promise<void>;
  onCreditSave: (purchase: CardPurchaseInput) => Promise<void>;
  cards: CreditCard[];
  categories: Category[];
  accounts: Account[];
  onCategory: (name: string) => Promise<Category>;
  onSubcategory: (id: string, name: string) => Promise<Subcategory>;
  initial?: Expense;
}) {
  const [amount, setAmount] = useState(initial ? (initial.amount_cents / 100).toFixed(2).replace('.', ',') : '');
  const [category, setCategory] = useState(initial?.category_id || '');
  const [subcategory, setSubcategory] = useState(initial?.subcategory_id || '');
  const [date, setDate] = useState(initial ? dateToDisplay(initial.occurred_on) : localDate());
  const [payment, setPayment] = useState<'pix' | 'debit' | 'cash' | 'credit'>(initial?.payment_method || 'pix');
  const [source, setSource] = useState(initial?.account_id || accounts.find(a => a.kind === 'bank')?.id || '');
  const [note, setNote] = useState(initial?.note || '');
  const [cardId, setCardId] = useState(cards[0]?.id || '');
  const [count, setCount] = useState('1');
  const [firstBill, setFirstBill] = useState('');
  const setError = useToastSetter('error');
  const [busy, setBusy] = useState(false);
  const selected = categories.find(item => item.id === category);
  const visibleCategories = categories.filter(item => item.active || item.id === category);
  const visibleSubcategories = selected?.subcategories.filter(item => item.active || item.id === subcategory) || [];
  const options = accounts.filter(item => payment === 'cash' ? item.kind === 'cash' : item.kind === 'bank');
  async function save() {
    const cents = parseCents(amount);
    if (!cents) return setError('Informe um valor maior que zero. Exemplo: 45,90.');
    if (!selected) return setError('Escolha uma categoria.');
    if (!visibleSubcategories.some(item => item.id === subcategory)) return setError('Escolha uma subcategoria.');
    if (!validDate(date)) return setError('Informe uma data válida no formato DD/MM/AAAA.');
    if (payment === 'credit') {
      if (!cards.some(item => item.id === cardId)) return setError('Cadastre e escolha um cartão na aba Cartões.');
      if (!Number.isInteger(Number(count)) || Number(count) < 1 || Number(count) > 120) return setError('Informe de 1 a 120 parcelas.');
      if (firstBill && !/^(0[1-9]|1[0-2])\/\d{4}$/.test(firstBill)) return setError('Informe a primeira fatura no formato MM/AAAA.');
    } else if (!options.some(item => item.id === source)) return setError('Escolha uma conta de saída.');
    setBusy(true); setError('');
    try {
      if (payment === 'credit') {
        const [billMonth, billYear] = firstBill.split('/');
        await onCreditSave({
          card_id: cardId, category_id: category, subcategory_id: subcategory,
          purchased_on: dateToIso(date), total_cents: cents,
          installment_count: Number(count), note: note.trim(), legacy: false,
          ...(firstBill ? {
            first_bill_month: `${billYear}-${billMonth}-01`,
          } : {}),
        });
      } else await onSave({
        account_id: source, category_id: category, subcategory_id: subcategory,
        amount_cents: cents, occurred_on: dateToIso(date), payment_method: payment,
        note: note.trim(),
      });
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível salvar a despesa.'); }
    finally { setBusy(false); }
  }
  return <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <View><Text style={s.eyebrow}>LANÇAMENTO RÁPIDO</Text><Text style={s.title}>{initial ? 'Editar despesa' : 'Nova despesa'}</Text><Text style={s.hint}>{payment === 'credit' ? 'Compra no crédito: entra na fatura. O saldo muda ao pagar a fatura.' : 'Despesa já paga: o saldo da conta muda ao salvar.'}</Text></View>
      <Text style={s.label}>Valor *</Text>
      <View style={s.amountRow}><Text style={s.currency}>R$</Text><TextInput accessibilityLabel="Valor da despesa" placeholder="Informe o valor" placeholderTextColor="#829187" keyboardType="decimal-pad" value={amount} onChangeText={setAmount} style={s.amount} maxLength={14} /></View>
      <Text style={s.label}>Categoria *</Text>
      <View style={s.wrap}>{visibleCategories.map(item => <Chip key={item.id} label={item.name} selected={category === item.id} onPress={() => { setCategory(item.id); setSubcategory(''); }} />)}</View>
      <CategoryCreator kind="categoria" existing={categories.map(item => item.name)} onCreate={async name => {
        const created = await onCategory(name); setCategory(created.id); setSubcategory('');
      }} />
      <Text style={s.label}>Subcategoria *</Text>
      <View style={s.wrap}>{selected ? visibleSubcategories.length ? visibleSubcategories.map(item => <Chip key={item.id} label={item.name} selected={subcategory === item.id} onPress={() => setSubcategory(item.id)} />) : <Text style={s.hint}>Cadastre uma subcategoria abaixo.</Text> : <Text style={s.hint}>Selecione uma categoria acima.</Text>}</View>
      {selected?.active && <CategoryCreator key={selected.id} kind="subcategoria" existing={selected.subcategories.map(item => item.name)} onCreate={async name => {
        const created = await onSubcategory(selected.id, name); setSubcategory(created.id);
      }} />}
      <Text style={s.label}>Data da compra *</Text>
      <TextInput accessibilityLabel="Data da compra" style={s.input} value={date} onChangeText={setDate} placeholder="DD/MM/AAAA" keyboardType="numbers-and-punctuation" maxLength={10} />
      <Text style={s.label}>Forma de pagamento *</Text>
      <View style={s.wrap}>{(['pix', 'debit', 'cash', ...(!initial ? ['credit'] as const : [])] as const).map(item => <Chip key={item} label={paymentLabel[item]} selected={payment === item} onPress={() => {
        setPayment(item);
        setSource(accounts.find(a => item === 'cash' ? a.kind === 'cash' : a.kind === 'bank')?.id || '');
      }} />)}</View>
      {payment === 'credit' ? <>
        <Text style={s.label}>Cartão *</Text>
        <View style={s.wrap}>{cards.length ? cards.map(item =>
          <Chip key={item.id} label={item.name} selected={cardId === item.id} onPress={() => setCardId(item.id)} />) :
          <Text style={s.hint}>Cadastre um cartão na aba Cartões.</Text>}</View>
        <Text style={s.label}>Parcelas *</Text>
        <TextInput accessibilityLabel="Número de parcelas" style={s.input} value={count} onChangeText={setCount} keyboardType="number-pad" maxLength={3} />
        <Text style={s.label}>Primeira fatura (MM/AAAA, opcional)</Text>
        <TextInput accessibilityLabel="Primeira fatura" style={s.input} value={firstBill}
          onChangeText={setFirstBill} placeholder="MM/AAAA"
          keyboardType="numbers-and-punctuation" maxLength={7} />
      </> : <>
        <Text style={s.label}>Conta de saída *</Text>
        <View style={s.wrap}>{options.length ? options.map(item => <Chip key={item.id} label={item.name} selected={source === item.id} onPress={() => setSource(item.id)} />) : <Text style={s.hint}>Cadastre uma conta {payment === 'cash' ? 'dinheiro' : 'bancária'} na aba Contas.</Text>}</View>
      </>}
      <Text style={s.label}>Observação <Text style={s.hint}>(opcional)</Text></Text>
      <TextInput accessibilityLabel="Observação" placeholder="Algo para lembrar?" style={[s.input, { minHeight: 80 }]} value={note} onChangeText={setNote} multiline maxLength={200} />
      <Button label={busy ? 'Salvando…' : initial ? 'Salvar alterações' : payment === 'credit' ? 'Salvar compra no cartão' : 'Salvar despesa'} onPress={() => { if (!busy) void save(); }} />
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
});
