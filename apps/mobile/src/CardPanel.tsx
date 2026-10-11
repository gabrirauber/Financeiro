import React, { useEffect, useState } from 'react';
import { Switch, Text, TextInput, View } from 'react-native';
import { request, Workspace } from './api';
import { Account, Category, CreditCard, Invoice, dateToDisplay, dateToIso, monthIso } from './finance';
import { localDate, money, parseCents } from './prototype';
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
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<string>();
  const [payAccount, setPayAccount] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editingCard, setEditingCard] = useState<string>();
  const [legacyCard, setLegacyCard] = useState<string>();
  const [legacyAmount, setLegacyAmount] = useState('');
  const [legacyCount, setLegacyCount] = useState('');
  const [legacyCategory, setLegacyCategory] = useState('');
  const [legacySubcategory, setLegacySubcategory] = useState('');
  const [legacyNote, setLegacyNote] = useState('');
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
    const [allCards, allInvoices, allAccounts, allCategories] = await Promise.all([
      request<CreditCard[]>(`${root}/cards`, token),
      request<Invoice[]>(`${root}/invoices`, token),
      request<Account[]>(`${root}/accounts`, token),
      request<Category[]>(`${root}/categories`, token),
    ]);
    setCards(allCards); setInvoices(allInvoices); setAccounts(allAccounts); setCategories(allCategories);
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
      await request(`${root}/cards${editingCard ? '/' + editingCard : ''}`, token, editingCard ? 'PATCH' : 'POST', {
        name: name.trim(), closing_day: closeNumber, due_day: dueNumber,
        closing_day_next_bill: nextBill,
      });
      setShowCreate(false); setEditingCard(undefined); setName(''); setClosing(''); setDue(''); setNextBill(false);
      setNotice(editingCard ? 'Cartão atualizado. As faturas já criadas mantêm as datas anteriores.' :
        'Cartão cadastrado. Você já pode lançar compras no crédito pelo +.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível cadastrar o cartão.'); }
    finally { setBusy(false); }
  }
  function startEditCard(card: CreditCard) {
    setEditingCard(card.id); setShowCreate(true); setLegacyCard(undefined);
    setName(card.name); setClosing(String(card.closing_day)); setDue(String(card.due_day));
    setNextBill(card.closing_day_next_bill); setError('');
  }
  function cancelCardForm() {
    setShowCreate(false); setEditingCard(undefined);
    setName(''); setClosing(''); setDue(''); setNextBill(false); setError('');
  }
  function startLegacy(card: CreditCard) {
    setLegacyCard(card.id); cancelCardForm();
    setLegacyAmount(''); setLegacyCount(''); setLegacyCategory(''); setLegacySubcategory('');
    setLegacyNote(''); setError('');
  }
  async function saveLegacy() {
    const cents = parseCents(legacyAmount);
    const count = Number(legacyCount);
    const category = categories.find(item => item.id === legacyCategory && item.active);
    const sub = category?.subcategories.find(item => item.id === legacySubcategory && item.active);
    if (!cents) return setError('Informe o valor de cada parcela em reais.');
    if (!Number.isInteger(count) || count < 1 || count > 120)
      return setError('Informe de 1 a 120 parcelas restantes.');
    if (!category || !sub) return setError('Escolha categoria e subcategoria.');
    if (cents * count > 999999999) return setError('O valor total excede o permitido.');
    setBusy(true); setError('');
    try {
      await request(`${root}/card-purchases`, token, 'POST', {
        card_id: legacyCard, category_id: category.id, subcategory_id: sub.id,
        purchased_on: dateToIso(localDate()), total_cents: cents * count,
        installment_count: count, legacy: true,
        first_bill_month: `${monthIso(new Date())}-01`, first_sequence: 1,
        note: legacyNote.trim(),
      });
      setLegacyCard(undefined);
      setNotice(`${count} ${count === 1 ? 'parcela lançada' : 'parcelas lançadas'} a partir da fatura atual.`);
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível lançar as parcelas antigas.'); }
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
  const cardForm = <Card>
        <Text style={label}>{editingCard ? 'Editar cartão' : 'Novo cartão'}</Text>
        {editingCard && <Text style={muted}>As faturas já criadas manterão suas datas. Novas compras usarão os dias atualizados.</Text>}
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
        <Button label={busy ? 'Salvando…' : editingCard ? 'Salvar alterações' : 'Salvar cartão'} onPress={() => { if (!busy) void create(); }} />
      <Button label="Cancelar" secondary onPress={cancelCardForm} />
    </Card>;
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
      {!editingCard && <Button label={showCreate ? 'Cancelar' : 'Cadastrar cartão'}
        secondary onPress={() => { if (showCreate) cancelCardForm(); else { cancelCardForm(); setShowCreate(true); setLegacyCard(undefined); } }} />}
      {showCreate && !editingCard && cardForm}
      {cards.map(card => <Card key={card.id}>
        <Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>{card.name}</Text>
        <Text style={muted}>Fecha dia {card.closing_day} · vence dia {card.due_day}</Text>
        <Button label="Editar cartão" secondary onPress={() => startEditCard(card)} />
        {editingCard === card.id && cardForm}
        <Button label="Lançar parcelas antigas" secondary onPress={() => startLegacy(card)} />
        {legacyCard === card.id && <Card>
          <Text style={label}>Parcelas antigas · {card.name}</Text>
          <Text style={muted}>Informe o valor de cada parcela e quantas faltam. A primeira entra na fatura de {monthIso(new Date()).split('-').reverse().join('/')}.</Text>
          <Text style={label}>Valor de cada parcela *</Text>
          <TextInput accessibilityLabel="Valor de cada parcela antiga" style={input} value={legacyAmount}
            onChangeText={setLegacyAmount} keyboardType="decimal-pad" placeholder="200,00" />
          <Text style={label}>Quantidade de parcelas restantes *</Text>
          <TextInput accessibilityLabel="Quantidade de parcelas restantes" style={input} value={legacyCount}
            onChangeText={setLegacyCount} keyboardType="number-pad" maxLength={3} />
          <Text style={label}>Categoria *</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{categories.filter(item => item.active).map(item =>
            <Chip key={item.id} label={item.name} selected={legacyCategory === item.id}
              onPress={() => { setLegacyCategory(item.id); setLegacySubcategory(''); }} />)}</View>
          <Text style={label}>Subcategoria *</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{categories.find(item => item.id === legacyCategory)
            ?.subcategories.filter(item => item.active).map(item =>
              <Chip key={item.id} label={item.name} selected={legacySubcategory === item.id}
                onPress={() => setLegacySubcategory(item.id)} />)}</View>
          <Text style={label}>Observação (opcional)</Text>
          <TextInput accessibilityLabel="Observação da compra antiga" style={input} value={legacyNote}
            onChangeText={setLegacyNote} maxLength={200} placeholder="Ex.: Compra antiga" />
          <Button label={busy ? 'Salvando…' : 'Lançar parcelas'} onPress={() => { if (!busy) void saveLegacy(); }} />
          <Button label="Cancelar" secondary onPress={() => setLegacyCard(undefined)} />
        </Card>}
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
