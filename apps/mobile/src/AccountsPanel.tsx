import React, { useEffect, useState } from 'react';
import { Alert, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { request, Workspace } from './api';
import { localDate, money, parseCents, validDate } from './prototype';
import { MoneyInput } from './MoneyInput';
import { Expense } from './finance';
import { Button, Card, Chip, palette } from './ui';
import { useToastSetter } from './Toast';

type Account = { id: string; name: string; kind: 'bank' | 'cash'; opening_balance_cents: number; balance_cents: number; opened_on: string };
type Movement = { id: string; kind: 'income' | 'transfer_in' | 'transfer_out' | 'expense' | 'bill_payment'; amount_cents: number; occurred_on: string; note: string; transfer_id: string | null; payment_kind: 'advance' | 'partial' | 'full' | null; expense: null | { id: string; category_id: string; subcategory_id: string; payment_method: 'pix' | 'debit' | 'cash' } };
type Mode = 'account' | 'income' | 'transfer' | 'payment' | null;
const input = () => ({ backgroundColor: palette.white, borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink });
const dateToIso = (value: string) => value.split('/').reverse().join('-');
const dateToDisplay = (value: string) => value.split('-').reverse().join('/');

export function AccountsPanel({ workspace, token, refresh, startCreateRequest, onCreated, onEditExpense, onChanged }: { workspace: Workspace; token: string; refresh: number; startCreateRequest?: number; onCreated?: () => void; onEditExpense: (expense: Expense) => void; onChanged: () => void }) {
  const root = `/workspaces/${workspace.id}`;
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selected, setSelected] = useState<string>();
  const [statement, setStatement] = useState<Movement[]>([]);
  const [mode, setMode] = useState<Mode>(null);
  const [name, setName] = useState('');
  const [kind, setKind] = useState<'bank' | 'cash'>('bank');
  const [amount, setAmount] = useState('');
  const [date, setDate] = useState(localDate());
  const [note, setNote] = useState('');
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [editing, setEditing] = useState<string>();
  const [editingPaymentKind, setEditingPaymentKind] = useState<Movement['payment_kind']>(null);
  const [editingOpening, setEditingOpening] = useState(false);
  const [openingAmount, setOpeningAmount] = useState('');
  const setError = useToastSetter('error');
  const setNotice = useToastSetter('success');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load(accountId = selected) {
    const all = await request<Account[]>(`${root}/accounts`, token);
    setAccounts(all);
    const target = all.find(item => item.id === accountId)?.id;
    setSelected(target);
    if (target) setStatement(await request<Movement[]>(`${root}/accounts/${target}/statement`, token));
    else setStatement([]);
  }
  useEffect(() => {
    let active = true;
    setLoading(true);
    load(selected).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Erro ao carregar contas.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [workspace.id, token, refresh]);
  async function choose(id: string) {
    setSelected(id); setEditingOpening(false); setError('');
    try { setStatement(await request<Movement[]>(`${root}/accounts/${id}/statement`, token)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro ao carregar extrato.'); }
  }
  function reset() {
    setMode(null); setEditing(undefined); setName(''); setAmount(''); setNote('');
    setEditingPaymentKind(null);
    setDate(localDate()); setError('');
  }
  async function saveOpening() {
    if (!selected) return;
    const cents = parseCents(openingAmount);
    if (cents === null && !/^0(?:,0{1,2})?$/.test(openingAmount.trim())) {
      setError('Informe um saldo inicial válido.'); return;
    }
    setBusy(true); setError('');
    try {
      await request(`${root}/accounts/${selected}/opening-balance`, token, 'PATCH',
        { opening_balance_cents: cents || 0 });
      setEditingOpening(false); await load(selected);
      setNotice('Saldo inicial corrigido. O saldo atual foi atualizado.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível corrigir o saldo inicial.'); }
    finally { setBusy(false); }
  }
  function start(next: Mode) { reset(); setMode(next); setAmount(next === 'account' ? '0,00' : ''); setSource(selected || accounts[0]?.id || ''); setDestination(accounts.find(a => a.id !== (selected || accounts[0]?.id))?.id || ''); }
  useEffect(() => { if (startCreateRequest) start('account'); }, [startCreateRequest]);
  function startEdit(row: Movement) {
    setMode('income'); setEditing(row.id); setSource(selected || '');
    setAmount((row.amount_cents / 100).toFixed(2).replace('.', ','));
    setDate(dateToDisplay(row.occurred_on)); setNote(row.note); setError('');
  }
  async function startEditTransfer(row: Movement) {
    if (!row.transfer_id) return;
    setError('');
    try {
      const transfer = await request<{ id: string; from_account_id: string; to_account_id: string; amount_cents: number; occurred_on: string; note: string }>(`${root}/transfers/${row.transfer_id}`, token);
      setMode('transfer'); setEditing(transfer.id);
      setSource(transfer.from_account_id); setDestination(transfer.to_account_id);
      setAmount((transfer.amount_cents / 100).toFixed(2).replace('.', ','));
      setDate(dateToDisplay(transfer.occurred_on)); setNote(transfer.note);
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível abrir a transferência.'); }
  }
  function startEditPayment(row: Movement) {
    setMode('payment'); setEditing(row.id); setSource(selected || '');
    setEditingPaymentKind(row.payment_kind);
    setAmount((row.amount_cents / 100).toFixed(2).replace('.', ','));
    setDate(dateToDisplay(row.occurred_on)); setError('');
  }
  async function save() {
    const cents = parseCents(amount);
    if (cents === null && !(mode === 'account' && /^0(?:,0{1,2})?$/.test(amount.trim()))) { setError('Informe um valor válido em reais.'); return; }
    if (mode !== 'account' && !validDate(date)) { setError('Informe uma data válida no formato DD/MM/AAAA.'); return; }
    if (mode === 'account' && !name.trim()) { setError('Informe a descrição da conta.'); return; }
    if (mode === 'transfer' && source === destination) { setError('Escolha duas contas diferentes.'); return; }
    setBusy(true); setError('');
    try {
      if (mode === 'account') await request(`${root}/accounts`, token, 'POST', { name: name.trim(), kind, opening_balance_cents: cents || 0 });
      if (mode === 'income') await request(`${root}/incomes${editing ? '/' + editing : ''}`, token, editing ? 'PATCH' : 'POST', { account_id: source, amount_cents: cents, occurred_on: dateToIso(date), note });
      if (mode === 'transfer') await request(`${root}/transfers${editing ? '/' + editing : ''}`, token, editing ? 'PATCH' : 'POST', { from_account_id: source, to_account_id: destination, amount_cents: cents, occurred_on: dateToIso(date), note });
      if (mode === 'payment' && editing) await request(`${root}/bill-payments/${editing}`, token, 'PATCH', { account_id: source, amount_cents: cents, occurred_on: dateToIso(date) });
      const savedMode = mode; const wasEditing = !!editing; const accountId = source;
      reset(); await load(savedMode === 'account' ? undefined : accountId); onChanged();
      setNotice(wasEditing ? (savedMode === 'income' ? 'Receita atualizada.' : savedMode === 'payment' ? 'Pagamento corrigido e fatura recalculada.' : 'Transferência atualizada.') : savedMode === 'account' ? 'Conta cadastrada.' : savedMode === 'income' ? 'Receita recebida e saldo atualizado.' : 'Transferência registrada nas duas contas.');
      if (savedMode === 'account') onCreated?.();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível salvar.'); }
    finally { setBusy(false); }
  }
  function remove(row: Movement) {
    const isIncome = row.kind === 'income';
    const isExpense = row.kind === 'expense';
    const isPayment = row.kind === 'bill_payment';
    const title = isIncome ? 'Desfazer receita?' : isExpense ? 'Desfazer despesa?' : isPayment ? 'Desfazer pagamento da fatura?' : 'Desfazer transferência?';
    const run = async () => {
      setBusy(true); setError('');
      try {
        await request(`${root}/${isIncome ? 'incomes/' + row.id : isExpense ? 'expenses/' + row.expense?.id : isPayment ? 'bill-payments/' + row.id : 'transfers/' + row.transfer_id}`, token, 'DELETE');
        await load(); onChanged();
        setNotice(isIncome ? 'Receita desfeita.' : isExpense ? 'Despesa desfeita e saldo corrigido.' : isPayment ? 'Pagamento desfeito e fatura recalculada.' : 'Transferência desfeita nas duas contas.');
      } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível excluir.'); }
      finally { setBusy(false); }
    };
    if (Platform.OS === 'web') {
      if (window.confirm(title)) void run();
    } else Alert.alert(title, 'O saldo será atualizado.', [{ text: 'Cancelar', style: 'cancel' }, { text: 'Desfazer', style: 'destructive', onPress: () => void run() }]);
  }
  const current = accounts.find(item => item.id === selected);
  const total = accounts.reduce((sum, item) => sum + item.balance_cents, 0);
  const thisMonth = (value: string) => value.slice(0, 7) === dateToIso(localDate()).slice(0, 7);
  const field = (label: string, value: string, change: (value: string) => void, props = {}) => <View style={{ gap: 5 }}><Text style={{ color: palette.ink, fontWeight: '600' }}>{label}</Text><TextInput style={input()} value={value} onChangeText={change} {...props} /></View>;
  const form = mode && <Card>
      <Text style={{ color: palette.ink, fontSize: 18, fontWeight: '700' }}>{mode === 'account' ? 'Nova conta' : mode === 'income' ? (editing ? 'Editar receita' : 'Receita recebida') : mode === 'payment' ? 'Corrigir pagamento da fatura' : editing ? 'Editar transferência' : 'Nova transferência'}</Text>
      {mode === 'payment' && <Text style={{ color: palette.muted }}>{editingPaymentKind === 'full' ? 'Na quitação integral, o valor deve ser igual ao saldo da fatura. Você pode corrigir a conta ou a data; para mudar o valor, desfaça o pagamento.' : editingPaymentKind === 'partial' ? 'O valor restante será redistribuído entre as parcelas futuras ainda não pagas.' : 'O saldo da fatura será recalculado ao salvar.'}</Text>}
      {mode === 'account' && <>{field('Descrição', name, setName, { placeholder: 'Ex.: Conta principal' })}<View style={{ flexDirection: 'row', gap: 8 }}><Chip label="Banco" selected={kind === 'bank'} onPress={() => setKind('bank')} /><Chip label="Dinheiro" selected={kind === 'cash'} onPress={() => setKind('cash')} /></View></>}
      {mode !== 'account' && <><Text style={{ color: palette.ink }}>Conta {mode === 'transfer' ? 'de origem' : mode === 'payment' ? 'do pagamento' : 'de recebimento'}</Text><ScrollView horizontal contentContainerStyle={{ gap: 8 }}>{accounts.filter(item => mode !== 'payment' || item.kind === 'bank').map(item => <Chip key={item.id} label={item.name} selected={source === item.id} onPress={() => setSource(item.id)} />)}</ScrollView></>}
      {mode === 'transfer' && <><Text style={{ color: palette.ink }}>Conta de destino</Text><ScrollView horizontal contentContainerStyle={{ gap: 8 }}>{accounts.map(item => <Chip key={item.id} label={item.name} selected={destination === item.id} onPress={() => setDestination(item.id)} />)}</ScrollView></>}
      <View style={{ gap: 5 }}><Text style={{ color: palette.ink, fontWeight: '600' }}>{mode === 'account' ? 'Saldo inicial (R$)' : 'Valor (R$)'}</Text>
        <MoneyInput accessibilityLabel={mode === 'account' ? 'Saldo inicial (R$)' : 'Valor (R$)'} style={input()} value={amount} onChangeText={setAmount} placeholder={mode === 'account' ? undefined : 'Informe o valor'} /></View>
      {mode !== 'account' && <>{field('Data (DD/MM/AAAA)', date, setDate, { keyboardType: 'numbers-and-punctuation' })}{mode !== 'payment' && field('Observação (opcional)', note, setNote, { placeholder: 'Ex.: Salário' })}</>}
      <Button label={busy ? 'Salvando…' : 'Salvar'} onPress={() => { if (!busy) void save(); }} />
      <Button label="Cancelar" secondary onPress={reset} />
    </Card>;
  return <View style={{ gap: 16 }}>
    <Text style={{ color: palette.ink, fontSize: 28, fontWeight: '700' }}>Suas contas</Text>
    <Text style={{ color: palette.muted }}>Saldos e movimentações do espaço {workspace.name}.</Text>
    {loading && <Text style={{ color: palette.muted }}>Carregando contas…</Text>}
    <Card><Text style={{ color: palette.muted }}>SALDO TOTAL</Text><Text style={{ color: palette.ink, fontSize: 32, fontWeight: '700' }}>{money(total)}</Text><Text style={{ color: palette.muted }}>O saldo inicial compõe o caixa, mas não é receita do mês.</Text></Card>
    {accounts.map(item => <Pressable key={item.id} accessibilityRole="button" onPress={() => void choose(item.id)}><Card><Text style={{ color: palette.ink, fontWeight: '700' }}>{item.name} {selected === item.id ? '✓' : ''}</Text><Text style={{ color: palette.muted }}>{item.kind === 'bank' ? 'Conta bancária' : 'Dinheiro'}</Text><Text style={{ color: palette.ink, fontSize: 22, fontWeight: '700' }}>{money(item.balance_cents)}</Text></Card></Pressable>)}
    {!accounts.length && !loading && <Text style={{ color: palette.muted }}>Cadastre sua primeira conta para começar.</Text>}
    <Button label="Cadastrar conta" onPress={() => start('account')} />
    {!!accounts.length && <Button label="Registrar receita recebida" secondary onPress={() => start('income')} />}
    {accounts.length >= 2 && <Button label="Transferir entre contas" secondary onPress={() => start('transfer')} />}
    {!editing && form}
    {current && <><Text style={{ color: palette.ink, fontSize: 18, fontWeight: '700' }}>Extrato · {current.name}</Text>
      <Card>
        <Text style={{ color: palette.muted }}>Saldo inicial: {money(current.opening_balance_cents)}</Text>
        {!editingOpening ? <Button label="Corrigir saldo inicial" secondary onPress={() => {
          setOpeningAmount((current.opening_balance_cents / 100).toFixed(2).replace('.', ','));
          setEditingOpening(true); setError('');
        }} /> : <View style={{ gap: 8 }}>
          <Text style={{ color: palette.muted }}>A correção altera o saldo da conta sem criar uma receita.</Text>
          <MoneyInput accessibilityLabel="Novo saldo inicial" style={input()} value={openingAmount}
            onChangeText={setOpeningAmount} />
          <Button label={busy ? 'Salvando…' : 'Salvar saldo inicial'} onPress={() => { if (!busy) void saveOpening(); }} />
          <Button label="Cancelar" secondary onPress={() => setEditingOpening(false)} />
        </View>}
        {!statement.length && <Text style={{ color: palette.muted }}>Nenhuma movimentação nesta conta.</Text>}
        {statement.map(row => <View key={row.id} style={{ paddingVertical: 8, borderTopWidth: 1, borderColor: palette.line, gap: 4 }}>
          <Text style={{ color: palette.ink, fontWeight: '600' }}>{row.kind === 'income' ? 'Receita' : row.kind === 'expense' ? 'Despesa paga' : row.kind === 'bill_payment' ? 'Fatura paga' : row.kind === 'transfer_in' ? 'Transferência recebida' : 'Transferência enviada'} · {dateToDisplay(row.occurred_on)}</Text>
          {!!row.note && <Text style={{ color: palette.muted }}>{row.note}</Text>}
          <Text style={{ color: (row.kind === 'transfer_out' || row.kind === 'expense' || row.kind === 'bill_payment') ? palette.danger : palette.green, fontWeight: '700' }}>{(row.kind === 'transfer_out' || row.kind === 'expense' || row.kind === 'bill_payment') ? '−' : '+'}{money(row.amount_cents)}</Text>
          {thisMonth(row.occurred_on) && <View style={{ flexDirection: 'row', gap: 18 }}>
            <Text accessibilityRole="button" onPress={() => {
              if (row.kind === 'income') startEdit(row);
              else if (row.kind === 'expense' && row.expense) onEditExpense({
                id: row.expense.id, account_id: current.id, category_id: row.expense.category_id,
                subcategory_id: row.expense.subcategory_id, amount_cents: row.amount_cents,
                occurred_on: row.occurred_on, payment_method: row.expense.payment_method, note: row.note,
              });
              else if (row.kind === 'bill_payment') startEditPayment(row);
              else void startEditTransfer(row);
            }} style={{ color: palette.green }}>Editar</Text>
            <Text accessibilityRole="button" onPress={() => remove(row)} style={{ color: palette.danger }}>Desfazer</Text>
          </View>}
          {editing === (row.transfer_id || row.id) && form}
        </View>)}
      </Card>
    </>}
  </View>;
}
