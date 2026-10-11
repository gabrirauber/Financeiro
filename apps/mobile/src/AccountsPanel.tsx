import React, { useEffect, useState } from 'react';
import { Alert, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { request, Workspace } from './api';
import { localDate, money, parseCents, validDate } from './prototype';
import { Button, Card, Chip, palette } from './ui';

type Account = { id: string; name: string; kind: 'bank' | 'cash'; opening_balance_cents: number; balance_cents: number; opened_on: string };
type Movement = { id: string; kind: 'income' | 'transfer_in' | 'transfer_out' | 'expense' | 'bill_payment'; amount_cents: number; occurred_on: string; note: string; transfer_id: string | null };
type Mode = 'account' | 'income' | 'transfer' | null;
const input = { backgroundColor: 'white', borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink };
const dateToIso = (value: string) => value.split('/').reverse().join('-');
const dateToDisplay = (value: string) => value.split('-').reverse().join('/');

export function AccountsPanel({ workspace, token }: { workspace: Workspace; token: string }) {
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
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
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
    load(undefined).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Erro ao carregar contas.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [workspace.id, token]);
  async function choose(id: string) {
    setSelected(id); setError('');
    try { setStatement(await request<Movement[]>(`${root}/accounts/${id}/statement`, token)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro ao carregar extrato.'); }
  }
  function reset() {
    setMode(null); setEditing(undefined); setName(''); setAmount(''); setNote('');
    setDate(localDate()); setError('');
  }
  function start(next: Mode) { reset(); setMode(next); setSource(selected || accounts[0]?.id || ''); setDestination(accounts.find(a => a.id !== (selected || accounts[0]?.id))?.id || ''); }
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
      if (mode === 'transfer') await request(`${root}/transfers`, token, 'POST', { from_account_id: source, to_account_id: destination, amount_cents: cents, occurred_on: dateToIso(date), note });
      const savedMode = mode; const wasEditing = !!editing; const accountId = source;
      reset(); await load(savedMode === 'account' ? undefined : accountId);
      setNotice(wasEditing ? (savedMode === 'income' ? 'Receita atualizada.' : 'Transferência atualizada.') : savedMode === 'account' ? 'Conta cadastrada.' : savedMode === 'income' ? 'Receita recebida e saldo atualizado.' : 'Transferência registrada nas duas contas.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível salvar.'); }
    finally { setBusy(false); }
  }
  function remove(row: Movement) {
    const isIncome = row.kind === 'income';
    const title = isIncome ? 'Excluir receita?' : 'Desfazer transferência?';
    const run = async () => {
      setBusy(true); setError('');
      try {
        await request(`${root}/${isIncome ? 'incomes/' + row.id : 'transfers/' + row.transfer_id}`, token, 'DELETE');
        await load(); setNotice(isIncome ? 'Receita excluída.' : 'Transferência desfeita nas duas contas.');
      } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível excluir.'); }
      finally { setBusy(false); }
    };
    if (Platform.OS === 'web') {
      if (window.confirm(title)) void run();
    } else Alert.alert(title, 'O saldo será atualizado.', [{ text: 'Cancelar', style: 'cancel' }, { text: 'Excluir', style: 'destructive', onPress: () => void run() }]);
  }
  const current = accounts.find(item => item.id === selected);
  const total = accounts.reduce((sum, item) => sum + item.balance_cents, 0);
  const thisMonth = (value: string) => value.slice(0, 7) === dateToIso(localDate()).slice(0, 7);
  const field = (label: string, value: string, change: (value: string) => void, props = {}) => <View style={{ gap: 5 }}><Text style={{ color: palette.ink, fontWeight: '600' }}>{label}</Text><TextInput style={input} value={value} onChangeText={change} {...props} /></View>;
  return <View style={{ gap: 16 }}>
    <Text style={{ color: palette.ink, fontSize: 28, fontWeight: '700' }}>Suas contas</Text>
    <Text style={{ color: palette.muted }}>Saldos e movimentações do espaço {workspace.name}.</Text>
    {loading && <Text style={{ color: palette.muted }}>Carregando contas…</Text>}
    {!!notice && <Text accessibilityLiveRegion="polite" style={{ color: palette.green }}>{notice}</Text>}
    {!!error && <Text accessibilityLiveRegion="polite" style={{ color: '#AA422E' }}>{error}</Text>}
    <Card><Text style={{ color: palette.muted }}>SALDO TOTAL</Text><Text style={{ color: palette.ink, fontSize: 32, fontWeight: '700' }}>{money(total)}</Text><Text style={{ color: palette.muted }}>O saldo inicial compõe o caixa, mas não é receita do mês.</Text></Card>
    {accounts.map(item => <Pressable key={item.id} accessibilityRole="button" onPress={() => void choose(item.id)}><Card><Text style={{ color: palette.ink, fontWeight: '700' }}>{item.name} {selected === item.id ? '✓' : ''}</Text><Text style={{ color: palette.muted }}>{item.kind === 'bank' ? 'Conta bancária' : 'Dinheiro'}</Text><Text style={{ color: palette.ink, fontSize: 22, fontWeight: '700' }}>{money(item.balance_cents)}</Text></Card></Pressable>)}
    {!accounts.length && !loading && <Text style={{ color: palette.muted }}>Cadastre sua primeira conta para começar.</Text>}
    <Button label="Cadastrar conta" onPress={() => start('account')} />
    {!!accounts.length && <Button label="Registrar receita recebida" secondary onPress={() => start('income')} />}
    {accounts.length >= 2 && <Button label="Transferir entre contas" secondary onPress={() => start('transfer')} />}
    {mode && <Card>
      <Text style={{ color: palette.ink, fontSize: 18, fontWeight: '700' }}>{mode === 'account' ? 'Nova conta' : mode === 'income' ? (editing ? 'Editar receita' : 'Receita recebida') : 'Nova transferência'}</Text>
      {mode === 'account' && <>{field('Descrição', name, setName, { placeholder: 'Ex.: Conta principal' })}<View style={{ flexDirection: 'row', gap: 8 }}><Chip label="Banco" selected={kind === 'bank'} onPress={() => setKind('bank')} /><Chip label="Dinheiro" selected={kind === 'cash'} onPress={() => setKind('cash')} /></View></>}
      {mode !== 'account' && <><Text style={{ color: palette.ink }}>Conta {mode === 'transfer' ? 'de origem' : 'de recebimento'}</Text><ScrollView horizontal contentContainerStyle={{ gap: 8 }}>{accounts.map(item => <Chip key={item.id} label={item.name} selected={source === item.id} onPress={() => setSource(item.id)} />)}</ScrollView></>}
      {mode === 'transfer' && <><Text style={{ color: palette.ink }}>Conta de destino</Text><ScrollView horizontal contentContainerStyle={{ gap: 8 }}>{accounts.map(item => <Chip key={item.id} label={item.name} selected={destination === item.id} onPress={() => setDestination(item.id)} />)}</ScrollView></>}
      {field(mode === 'account' ? 'Saldo inicial (R$)' : 'Valor (R$)', amount, setAmount, { keyboardType: 'decimal-pad', placeholder: '0,00' })}
      {mode !== 'account' && <>{field('Data (DD/MM/AAAA)', date, setDate, { keyboardType: 'numbers-and-punctuation' })}{field('Observação (opcional)', note, setNote, { placeholder: 'Ex.: Salário' })}</>}
      <Button label={busy ? 'Salvando…' : 'Salvar'} onPress={() => { if (!busy) void save(); }} />
      <Button label="Cancelar" secondary onPress={reset} />
    </Card>}
    {current && <><Text style={{ color: palette.ink, fontSize: 18, fontWeight: '700' }}>Extrato · {current.name}</Text>
      <Card>
        <Text style={{ color: palette.muted }}>Saldo inicial: {money(current.opening_balance_cents)}</Text>
        {!statement.length && <Text style={{ color: palette.muted }}>Nenhuma movimentação nesta conta.</Text>}
        {statement.map(row => <View key={row.id} style={{ paddingVertical: 8, borderTopWidth: 1, borderColor: palette.line, gap: 4 }}>
          <Text style={{ color: palette.ink, fontWeight: '600' }}>{row.kind === 'income' ? 'Receita' : row.kind === 'expense' ? 'Despesa paga' : row.kind === 'bill_payment' ? 'Fatura paga' : row.kind === 'transfer_in' ? 'Transferência recebida' : 'Transferência enviada'} · {dateToDisplay(row.occurred_on)}</Text>
          {!!row.note && <Text style={{ color: palette.muted }}>{row.note}</Text>}
          <Text style={{ color: (row.kind === 'transfer_out' || row.kind === 'expense' || row.kind === 'bill_payment') ? '#AA422E' : palette.green, fontWeight: '700' }}>{(row.kind === 'transfer_out' || row.kind === 'expense' || row.kind === 'bill_payment') ? '−' : '+'}{money(row.amount_cents)}</Text>
          {thisMonth(row.occurred_on) && row.kind !== 'expense' && row.kind !== 'bill_payment' && <View style={{ flexDirection: 'row', gap: 18 }}>{<Text onPress={() => row.kind === 'income' ? startEdit(row) : void startEditTransfer(row)} style={{ color: palette.green }}>Editar</Text>}<Text onPress={() => remove(row)} style={{ color: '#AA422E' }}>{row.kind === 'income' ? 'Excluir' : 'Desfazer'}</Text></View>}
        </View>)}
      </Card>
    </>}
  </View>;
}
