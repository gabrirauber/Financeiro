import React, { useEffect, useState } from 'react';
import { Switch, Text, TextInput, View } from 'react-native';
import { request, Workspace } from './api';
import { Account, CreditCard, Invoice, dateToDisplay, monthIso } from './finance';
import { money, parseCents } from './prototype';
import { Button, Card, Chip, palette } from './ui';

const input = { backgroundColor: 'white', borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink };
const label = { color: palette.ink, fontSize: 15, fontWeight: '600' as const };
const muted = { color: palette.muted, fontSize: 13, lineHeight: 20 };

export function CardPanel({ workspace, token, refresh }: {
  workspace: Workspace; token: string; refresh: () => void;
}) {
  const root = `/workspaces/${workspace.id}`;
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selected, setSelected] = useState<string>();
  const [payAccount, setPayAccount] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [closing, setClosing] = useState('');
  const [due, setDue] = useState('');
  const [nextBill, setNextBill] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState<string>();
  const [remainingAmount, setRemainingAmount] = useState('');
  const [remainingNote, setRemainingNote] = useState('');
  async function load() {
    const [allCards, allInvoices, allAccounts] = await Promise.all([
      request<CreditCard[]>(`${root}/cards`, token),
      request<Invoice[]>(`${root}/invoices`, token),
      request<Account[]>(`${root}/accounts`, token),
    ]);
    setCards(allCards); setInvoices(allInvoices); setAccounts(allAccounts);
    setPayAccount(current => current || allAccounts.find(a => a.kind === 'bank')?.id || '');
  }
  useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : 'Não foi possível carregar os cartões.')); }, [root, token]);
  async function create() {
    const closeNumber = Number(closing); const dueNumber = Number(due);
    if (!name.trim() || !Number.isInteger(closeNumber) || !Number.isInteger(dueNumber) ||
      closeNumber < 1 || closeNumber > 31 || dueNumber < 1 || dueNumber > 31) {
      setError('Informe o nome e os dias de fechamento e vencimento entre 1 e 31.'); return;
    }
    setBusy(true); setError('');
    try {
      await request(`${root}/cards`, token, 'POST', {
        name: name.trim(), closing_day: closeNumber, due_day: dueNumber,
        closing_day_next_bill: nextBill,
      });
      setShowCreate(false); setName(''); setClosing(''); setDue(''); setNextBill(false);
      setNotice('Cartão cadastrado. Você já pode lançar compras no crédito pelo +.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível cadastrar o cartão.'); }
    finally { setBusy(false); }
  }
  async function pay(invoice: Invoice) {
    if (!payAccount) return setError('Escolha uma conta bancária.');
    setBusy(true); setError('');
    try {
      await request(`${root}/invoices/${invoice.id}/pay`, token, 'POST',
        { account_id: payAccount });
      setNotice('Fatura paga. O valor foi descontado da conta bancária.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível pagar a fatura.'); }
    finally { setBusy(false); }
  }
  const current = invoices.find(x => x.id === selected);
  function startCorrection(purchaseId: string) {
    const editable = invoices.flatMap(invoice => invoice.installments)
      .filter(item => item.purchase_id === purchaseId &&
        !item.invoice_paid && item.invoice_month.slice(0, 7) >= monthIso(new Date()));
    setEditingPurchase(purchaseId);
    setRemainingAmount((editable.reduce((sum, item) => sum + item.amount_cents, 0) / 100)
      .toFixed(2).replace('.', ','));
    setRemainingNote(editable[0]?.note || '');
  }
  async function saveCorrection() {
    const editable = invoices.flatMap(invoice => invoice.installments)
      .find(item => item.purchase_id === editingPurchase && !item.invoice_paid);
    const cents = parseCents(remainingAmount);
    if (!editable || !cents) return setError('Informe um valor válido para as parcelas restantes.');
    setBusy(true); setError('');
    try {
      await request(`${root}/card-purchases/${editingPurchase}/remaining`, token, 'PATCH', {
        remaining_total_cents: cents, category_id: editable.category_id,
        subcategory_id: editable.subcategory_id, note: remainingNote.trim(),
      });
      setEditingPurchase(undefined); setNotice('Parcelas atuais e futuras corrigidas. O passado foi preservado.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível corrigir as parcelas.'); }
    finally { setBusy(false); }
  }
  return <View style={{ gap: 16 }}>
    <Text style={{ fontSize: 28, fontWeight: '700', color: palette.ink }}>Seus cartões</Text>
    <Text style={muted}>Compras por fatura. O saldo da conta muda quando a fatura é paga.</Text>
    {!!notice && <Card><Text style={muted}>{notice}</Text></Card>}
    {!!error && <Card><Text accessibilityRole="alert" style={{ color: '#AA422E' }}>{error}</Text></Card>}
    {current ? <>
      <Button secondary label="← Todas as faturas" onPress={() => setSelected(undefined)} />
      <Card>
        <Text style={label}>{current.card_name} · {current.month.slice(0, 7).split('-').reverse().join('/')}</Text>
        <Text style={{ fontSize: 29, fontWeight: '700', color: palette.ink }}>{money(current.total_cents)}</Text>
        <Text style={muted}>Fecha em {dateToDisplay(current.closes_on)} · vence em {dateToDisplay(current.due_on)}</Text>
        <Text style={muted}>{current.status === 'paid' ? `Paga em ${dateToDisplay(current.paid_on!)}` :
          current.status === 'open' ? 'Fatura aberta' : 'Fatura fechada · aguardando pagamento'}</Text>
        {current.installments.map(item => <View key={item.id} style={{ paddingVertical: 9, borderTopWidth: 1, borderColor: palette.line }}>
          <Text style={label}>{item.note || 'Compra no crédito'} · {item.sequence}/{item.total_count}</Text>
          <Text style={muted}>{dateToDisplay(item.purchased_on)} · {money(item.amount_cents)}</Text>
          {!item.invoice_paid && <Button secondary label="Corrigir parcelas atuais e futuras"
            onPress={() => startCorrection(item.purchase_id)} />}
        </View>)}
      </Card>
      {editingPurchase && <Card>
        <Text style={label}>Corrigir parcelas não pagas</Text>
        <Text style={muted}>Informe o valor total restante. O app redistribui entre os meses atuais e futuros; faturas pagas e meses anteriores permanecem intactos.</Text>
        <TextInput accessibilityLabel="Total restante das parcelas" style={input}
          keyboardType="decimal-pad" value={remainingAmount} onChangeText={setRemainingAmount} />
        <TextInput accessibilityLabel="Observação das parcelas restantes" style={input}
          value={remainingNote} onChangeText={setRemainingNote} maxLength={200} />
        <Button label={busy ? 'Salvando…' : 'Salvar correção'}
          onPress={() => { if (!busy) void saveCorrection(); }} />
        <Button label="Cancelar" secondary onPress={() => setEditingPurchase(undefined)} />
      </Card>}
      {current.status === 'closed' && <Card>
        <Text style={label}>Pagar fatura integral</Text>
        <Text style={muted}>Todas as parcelas desta fatura serão quitadas juntas.</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{accounts.filter(a => a.kind === 'bank').map(a =>
          <Chip key={a.id} label={a.name} selected={payAccount === a.id} onPress={() => setPayAccount(a.id)} />)}</View>
        <Button label={busy ? 'Pagando…' : `Pagar ${money(current.total_cents)}`}
          onPress={() => { if (!busy) void pay(current); }} />
      </Card>}
    </> : <>
      <Button label={showCreate ? 'Cancelar cadastro' : 'Cadastrar cartão'}
        secondary onPress={() => { setShowCreate(!showCreate); setError(''); }} />
      {showCreate && <Card>
        <Text style={label}>Nome do cartão *</Text>
        <TextInput accessibilityLabel="Nome do cartão" style={input} value={name} onChangeText={setName} placeholder="Ex.: Cartão principal" />
        <Text style={label}>Dia de fechamento *</Text>
        <TextInput accessibilityLabel="Dia de fechamento" style={input} value={closing} onChangeText={setClosing} keyboardType="number-pad" maxLength={2} placeholder="10" />
        <Text style={label}>Dia de vencimento *</Text>
        <TextInput accessibilityLabel="Dia de vencimento" style={input} value={due} onChangeText={setDue} keyboardType="number-pad" maxLength={2} placeholder="20" />
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Switch accessibilityLabel="Compra no fechamento vai para a próxima fatura" value={nextBill} onValueChange={setNextBill} />
          <Text style={[muted, { flex: 1 }]}>Compra no dia do fechamento entra na próxima fatura</Text>
        </View>
        <Button label={busy ? 'Salvando…' : 'Salvar cartão'} onPress={() => { if (!busy) void create(); }} />
      </Card>}
      {cards.map(card => <Card key={card.id}>
        <Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>{card.name}</Text>
        <Text style={muted}>Fecha dia {card.closing_day} · vence dia {card.due_day}</Text>
        {invoices.filter(i => i.card_id === card.id).length ? invoices.filter(i => i.card_id === card.id).map(invoice =>
          <Button key={invoice.id} secondary
            label={`${invoice.month.slice(0, 7).split('-').reverse().join('/')} · ${money(invoice.total_cents)} · ${invoice.status === 'paid' ? 'Paga' : invoice.status === 'open' ? 'Aberta' : 'Fechada'}`}
            onPress={() => setSelected(invoice.id)} />) :
          <Text style={muted}>Ainda não há compras neste cartão.</Text>}
      </Card>)}
      {!cards.length && <Card><Text style={muted}>Cadastre seu primeiro cartão para lançar compras parceladas.</Text></Card>}
    </>}
  </View>;
}
