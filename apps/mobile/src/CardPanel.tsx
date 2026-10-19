import React, { useEffect, useState } from 'react';
import { Alert, Keyboard, Platform, Pressable, Switch, Text, TextInput, View } from 'react-native';
import { request, Workspace } from './api';
import { Account, Category, CreditCard, Invoice, CardInstallment, Subcategory, dateToDisplay, dateToIso, monthIso } from './finance';
import { localDate, money, parseCents } from './prototype';
import { MoneyInput } from './MoneyInput';
import { CategoryCreator } from './CategoryCreator';
import { Button, Card, Chip, palette } from './ui';
import { useToastSetter } from './Toast';

const input = () => ({ backgroundColor: palette.white, borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink });
const label = () => ({ color: palette.ink, fontSize: 15, fontWeight: '600' as const });
const muted = () => ({ color: palette.muted, fontSize: 13, lineHeight: 20 });
const centsToInput = (cents: number) => (cents / 100).toFixed(2).replace('.', ',');

export function CardPanel({ workspace, token, refresh, startCreateRequest, onCreated }: {
  workspace: Workspace; token: string; refresh: () => void; startCreateRequest?: number; onCreated?: () => void;
}) {
  const root = `/workspaces/${workspace.id}`;
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [refundItem, setRefundItem] = useState<CardInstallment>();
  const [refundAmount, setRefundAmount] = useState('');
  const [refundMonth, setRefundMonth] = useState('');
  const [refundDate, setRefundDate] = useState('');
  const [refundNote, setRefundNote] = useState('');
  const [refundRequest, setRefundRequest] = useState('');
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
  const selectedLegacyCategory = categories.find(item => item.id === legacyCategory);
  const [name, setName] = useState('');
  const [closing, setClosing] = useState('10');
  const [due, setDue] = useState('20');
  const [nextBill, setNextBill] = useState(false);
  const setError = useToastSetter('error');
  const setNotice = useToastSetter('success');
  const [busy, setBusy] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState<string>();
  const [installmentAmount, setInstallmentAmount] = useState('');
  const [remainingCount, setRemainingCount] = useState('');
  const [remainingNote, setRemainingNote] = useState('');
  const [partialOpen, setPartialOpen] = useState(false);
  const [partialAmount, setPartialAmount] = useState('600,00');
  const [partialFees, setPartialFees] = useState('0,00');
  const [partialCount, setPartialCount] = useState('2');
  const [advanceOpen, setAdvanceOpen] = useState(false);
  const [advanceAmount, setAdvanceAmount] = useState('100,00');
  const [advanceRequestId, setAdvanceRequestId] = useState('');
  useEffect(() => { if (startCreateRequest) { setEditingCard(undefined); setShowCreate(true); } }, [startCreateRequest]);
  async function load() {
    const [allCards, allInvoices, allAccounts, allCategories] = await Promise.all([
      request<CreditCard[]>(`${root}/cards`, token),
      request<Invoice[]>(`${root}/invoices`, token),
      request<Account[]>(`${root}/accounts`, token),
      request<Category[]>(`${root}/categories`, token),
    ]);
    setCards(allCards); setInvoices(allInvoices); setAccounts(allAccounts); setCategories(allCategories);
    setSelected(current => current && allInvoices.some(invoice => invoice.id === current) ? current : undefined);
    setPayAccount(current => current || allAccounts.find(a => a.kind === 'bank')?.id || '');
  }
  useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : 'Não foi possível carregar os cartões.')); }, [root, token]);
  async function create() {
    const wasEditing = !!editingCard;
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
      setShowCreate(false); setEditingCard(undefined); setName(''); setClosing('10'); setDue('20'); setNextBill(false);
      setNotice(editingCard ? 'Cartão atualizado. As faturas já criadas mantêm as datas anteriores.' :
        'Cartão cadastrado. Você já pode lançar compras no crédito pelo +.');
      await load(); refresh();
      if (!wasEditing) onCreated?.();
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
    setName(''); setClosing('10'); setDue('20'); setNextBill(false); setError('');
  }
  function startLegacy(card: CreditCard) {
    setLegacyCard(card.id); cancelCardForm();
    setLegacyAmount(''); setLegacyCount(''); setLegacyCategory(''); setLegacySubcategory('');
    setLegacyNote(''); setError('');
  }
  async function createLegacyCategory(name: string) {
    const created = await request<Category>(`${root}/categories`, token, 'POST', { name });
    setCategories(items => [...items, created].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')));
    setLegacyCategory(created.id); setLegacySubcategory('');
  }
  async function createLegacySubcategory(name: string) {
    if (!selectedLegacyCategory) return;
    const created = await request<Subcategory>(`${root}/categories/${selectedLegacyCategory.id}/subcategories`, token, 'POST', { name });
    setCategories(items => items.map(item => item.id === selectedLegacyCategory.id ?
      { ...item, subcategories: [...item.subcategories, created].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')) } : item));
    setLegacySubcategory(created.id);
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
  async function payPartial(invoice: Invoice) {
    const paid = parseCents(partialAmount);
    const fees = parseCents(partialFees) ?? (/^0(?:,0{1,2})?$/.test(partialFees.trim()) ? 0 : null);
    const count = Number(partialCount);
    if (!payAccount) return setError('Escolha uma conta bancária.');
    if (!paid || paid >= invoice.remaining_cents)
      return setError('O pagamento deve ser maior que zero e menor que o total da fatura.');
    if (fees === null) return setError('Informe os juros e encargos em reais; use 0,00 se não houver.');
    if (!Number.isInteger(count) || count < 1 || count > 120 ||
      invoice.remaining_cents - paid < count) return setError('Informe uma quantidade válida de parcelas.');
    setBusy(true); setError('');
    try {
      await request(`${root}/invoices/${invoice.id}/pay-partial`, token, 'POST', {
        account_id: payAccount, paid_cents: paid, fee_cents: fees,
        installment_count: count,
      });
      setPartialOpen(false);
      setNotice('Pagamento parcial registrado. O restante foi lançado nas próximas faturas.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível registrar o pagamento parcial.'); }
    finally { setBusy(false); }
  }
  function startAdvance(invoice: Invoice) {
    setAdvanceOpen(true); setAdvanceAmount(centsToInput(Math.min(10000, invoice.remaining_cents))); setError('');
    setAdvanceRequestId(`${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`);
  }
  async function advance(invoice: Invoice) {
    const cents = parseCents(advanceAmount);
    if (!payAccount) return setError('Escolha uma conta bancária.');
    if (!cents || cents > invoice.remaining_cents)
      return setError('A antecipação deve ser maior que zero e não pode superar o saldo da fatura.');
    setBusy(true); setError('');
    try {
      await request(`${root}/invoices/${invoice.id}/advance`, token, 'POST', {
        account_id: payAccount, amount_cents: cents, request_id: advanceRequestId,
      });
      setAdvanceOpen(false); setAdvanceAmount('');
      setNotice('Antecipação registrada. O valor foi descontado da conta e da fatura.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível antecipar o pagamento.'); }
    finally { setBusy(false); }
  }
  function startRefund(item: CardInstallment) {
    setEditingPurchase(undefined); setRefundItem(item); setRefundAmount(centsToInput(item.amount_cents - (item.refunded_cents || 0)));
    const now = new Date();
    const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const existingCurrent = invoices.find(i => i.card_id === item.card_id && i.month.slice(0, 7) === monthIso(now));
    setRefundMonth(monthIso(existingCurrent?.paid_on ? next : now));
    setRefundDate(localDate(now)); setRefundNote('');
    setRefundRequest(`${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`);
  }
  async function saveRefund() {
    const cents = parseCents(refundAmount);
    if (!refundItem || !cents || cents > refundItem.amount_cents - (refundItem.refunded_cents || 0))
      return setError('Informe um valor até o saldo ainda não estornado da parcela.');
    if (!/^\d{2}\/\d{2}\/\d{4}$/.test(refundDate)) return setError('Informe a data do crédito como DD/MM/AAAA.');
    setBusy(true);
    try {
      const result = await request<Invoice>(`${root}/card-installments/${refundItem.id}/refund`, token, 'POST', {
        amount_cents: cents, credited_on: dateToIso(refundDate), invoice_month: `${refundMonth}-01`,
        note: refundNote.trim(), request_id: refundRequest,
      });
      setRefundItem(undefined); setSelected(result.id);
      await load(); refresh(); setNotice('Estorno registrado como crédito na fatura selecionada.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível registrar o estorno.'); }
    finally { setBusy(false); }
  }
  const current = invoices.find(x => x.id === selected);
  function startCorrection(purchaseId: string) {
    const editable = invoices.flatMap(invoice => invoice.installments)
      .filter(item => item.purchase_id === purchaseId &&
        !item.invoice_paid && item.invoice_month.slice(0, 7) >= monthIso(new Date()))
      .sort((a, b) => a.sequence - b.sequence);
    if (!editable.length) {
      const item = current?.installments.find(row => row.purchase_id === purchaseId);
      if (item && current!.month.slice(0, 7) <= monthIso(new Date()) && (item.refunded_cents || 0) < item.amount_cents) {
        startRefund(item); return;
      }
      return setError('Esta compra não tem parcelas atuais ou futuras para corrigir.');
    }
    setEditingPurchase(purchaseId);
    setInstallmentAmount(centsToInput(editable[0].amount_cents));
    setRemainingCount(String(editable.length));
    setRemainingNote(editable[0]?.note || '');
  }
  async function saveCorrection() {
    const editable = invoices.flatMap(invoice => invoice.installments)
      .find(item => item.purchase_id === editingPurchase && !item.invoice_paid);
    const cents = parseCents(installmentAmount);
    const count = Number(remainingCount);
    if (!editable || !cents) return setError('Informe o valor de cada parcela.');
    if (!Number.isInteger(count) || count < 1 || count > 120)
      return setError('Informe de 1 a 120 parcelas restantes.');
    if (cents * count > 999999999) return setError('O valor total excede o permitido.');
    setBusy(true); setError('');
    try {
      await request(`${root}/card-purchases/${editingPurchase}/remaining`, token, 'PATCH', {
        installment_amount_cents: cents, remaining_installment_count: count,
        category_id: editable.category_id,
        subcategory_id: editable.subcategory_id, note: remainingNote.trim(),
      });
      setEditingPurchase(undefined); setNotice('Valor e quantidade das parcelas restantes atualizados.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível corrigir as parcelas.'); }
    finally { setBusy(false); }
  }
  function confirmDeletePurchase() {
    if (!editingPurchase || busy) return;
    const purchaseId = editingPurchase;
    const installments = invoices.flatMap(invoice => invoice.installments)
      .filter(item => item.purchase_id === purchaseId);
    const hasProtected = installments.some(item =>
      item.invoice_paid || item.invoice_month.slice(0, 7) < monthIso(new Date()));
    const message = hasProtected
      ? 'Excluir as parcelas atuais e futuras não pagas? As parcelas anteriores ou já pagas serão preservadas.'
      : 'Excluir esta compra e todas as suas parcelas das faturas?';
    const remove = () => { void deletePurchase(purchaseId); };
    if (Platform.OS === 'web') { if (window.confirm(message)) remove(); }
    else Alert.alert('Excluir compra', message, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Excluir', style: 'destructive', onPress: remove },
    ]);
  }
  async function deletePurchase(purchaseId: string) {
    setBusy(true); setError('');
    try {
      await request(`${root}/card-purchases/${purchaseId}`, token, 'DELETE');
      setEditingPurchase(undefined);
      setNotice('Parcelas atuais e futuras não pagas excluídas.');
      await load(); refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível excluir a compra.'); }
    finally { setBusy(false); }
  }
  const cardForm = <Card>
        <Text style={label()}>{editingCard ? 'Editar cartão' : 'Novo cartão'}</Text>
        {editingCard && <Text style={muted()}>As faturas já criadas manterão suas datas. Novas compras usarão os dias atualizados.</Text>}
        <Text style={label()}>Nome do cartão *</Text>
        <TextInput accessibilityLabel="Nome do cartão" style={input()} value={name} onChangeText={setName} placeholder="Ex.: Cartão principal" />
        <Text style={label()}>Dia de fechamento *</Text>
        <TextInput accessibilityLabel="Dia de fechamento" style={input()} value={closing} onChangeText={setClosing} keyboardType="number-pad" maxLength={2} />
        <Text style={label()}>Dia de vencimento *</Text>
        <TextInput accessibilityLabel="Dia de vencimento" style={input()} value={due} onChangeText={setDue} keyboardType="number-pad" maxLength={2} />
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Switch accessibilityLabel="Compra no fechamento vai para a próxima fatura" value={nextBill} onValueChange={setNextBill} />
          <Text style={[muted(), { flex: 1 }]}>Compra no dia do fechamento entra na próxima fatura</Text>
        </View>
        <Button label={busy ? 'Salvando…' : editingCard ? 'Salvar alterações' : 'Salvar cartão'} onPress={() => { if (!busy) void create(); }} />
      <Button label="Cancelar" secondary onPress={cancelCardForm} />
    </Card>;
  return <View style={{ gap: 16 }}>
    <Text style={{ fontSize: 28, fontWeight: '700', color: palette.ink }}>Seus cartões</Text>
    <Text style={muted()}>Compras por fatura. O saldo da conta muda quando a fatura é paga.</Text>
    {current ? <>
      <Button secondary label="← Todas as faturas" onPress={() => { setSelected(undefined); setPartialOpen(false); setAdvanceOpen(false); setRefundItem(undefined); }} />
      <Card>
        <Text style={label()}>{current.card_name} · {current.month.slice(0, 7).split('-').reverse().join('/')}</Text>
        <Text style={muted()}>Saldo a pagar</Text>
        <Text style={{ fontSize: 29, fontWeight: '700', color: palette.ink }}>{money(current.remaining_cents)}</Text>
        <Text style={muted()}>Total da fatura: {money(current.total_cents)} · Antecipado: {money(current.advanced_cents)}</Text>
        <Text style={muted()}>Fecha em {dateToDisplay(current.closes_on)} · vence em {dateToDisplay(current.due_on)}</Text>
        <Text style={muted()}>{current.status === 'refinanced' ? 'Pagamento parcial registrado · restante parcelado' :
          current.status === 'paid' ? `Paga em ${dateToDisplay(current.paid_on!)}` :
          current.status === 'open' ? 'Fatura aberta' :
          current.status === 'settled' ? 'Quitada por antecipações' : 'Fatura fechada · aguardando pagamento'}</Text>
        {!!current.refund_total_cents && <Text style={muted()}>Estornos nesta fatura: {money(current.refund_total_cents)}</Text>}
        {!!current.credit_brought_cents && <Text style={muted()}>Crédito de faturas anteriores: {money(current.credit_brought_cents)}</Text>}
        {!!current.credit_balance_cents && <Text style={muted()}>Crédito disponível para próximas faturas: {money(current.credit_balance_cents)}. Esse valor permanece no cartão.</Text>}
        {current.refunds?.map(item => <Text key={item.id} style={muted()}>Crédito de estorno em {dateToDisplay(item.credited_on)}: −{money(item.amount_cents)}{item.note ? ` · ${item.note}` : ''}</Text>)}
        {current.advances.map(item => <Text key={item.id} style={muted()}>Antecipação registrada: {money(item.amount_cents)}</Text>)}
        {current.financing && <Text style={muted()}>Pago agora: {money(current.financing.paid_cents)} ·
          Principal parcelado: {money(current.financing.principal_cents)} ·
          Encargos: {money(current.financing.fee_cents)}</Text>}
        {current.financing_installments.map(item => <View key={item.id} style={{ paddingVertical: 9, borderTopWidth: 1, borderColor: palette.line }}>
          <Text style={label()}>Faturas parceladas · {item.sequence}/{item.total_count}</Text>
          <Text style={muted()}>Principal {money(item.principal_cents)} · encargos {money(item.fee_cents)} · total {money(item.amount_cents)}</Text>
        </View>)}
        {[...current.installments].sort((a, b) =>
          b.created_at.localeCompare(a.created_at) || b.id.localeCompare(a.id)).map(item =>
          <View key={item.id} style={{ paddingVertical: 9, borderTopWidth: 1, borderColor: palette.line }}>
          <Pressable accessibilityRole="button" accessibilityLabel={`Abrir compra ${item.note || 'no crédito'}`}
            onPress={() => { Keyboard.dismiss(); startCorrection(item.purchase_id); }} style={{ gap: 3 }}>
            <Text style={label()}>{item.note || 'Compra no crédito'} · {item.sequence}/{item.total_count}</Text>
            <Text style={muted()}>{dateToDisplay(item.purchased_on)} · {money(item.amount_cents)}{item.invoice_paid ? ' · parcela já paga' : ''}</Text>
          </Pressable>
          {!!item.refunded_cents && <Text style={muted()}>Já estornado: {money(item.refunded_cents)}</Text>}
          {editingPurchase !== item.purchase_id && current.month.slice(0, 7) <= monthIso(new Date()) && (item.refunded_cents || 0) < item.amount_cents &&
            <Button label="Registrar estorno" secondary disabled={busy} onPress={() => startRefund(item)} />}
          {refundItem?.id === item.id && <Card>
            <Text style={label()}>Crédito recebido pelo estorno</Text>
            <Text style={muted()}>A compra original permanece no histórico. Informe a fatura em que o banco lançou o crédito. Outras parcelas da compra continuam como estão.</Text>
            <Text style={label()}>Valor estornado (R$)</Text>
            <MoneyInput accessibilityLabel="Valor do estorno" style={input()} value={refundAmount} onChangeText={setRefundAmount} />
            <Text style={label()}>Data em que recebeu o crédito</Text>
            <TextInput accessibilityLabel="Data do crédito do estorno" style={input()} value={refundDate} onChangeText={setRefundDate} placeholder="DD/MM/AAAA" maxLength={10} />
            <Text style={label()}>Fatura que recebeu o crédito</Text>
            <View style={{ flexDirection: 'row', gap: 8 }}>{[new Date(), new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1)].map(date =>
              <Chip key={monthIso(date)} label={monthIso(date).split('-').reverse().join('/')} selected={refundMonth === monthIso(date)} onPress={() => setRefundMonth(monthIso(date))} />)}</View>
            <TextInput accessibilityLabel="Observação do estorno" placeholder="Observação (opcional)" style={input()} value={refundNote} onChangeText={setRefundNote} maxLength={200} />
            <Button label={busy ? 'Registrando…' : 'Confirmar crédito de estorno'} disabled={busy} onPress={() => void saveRefund()} />
            <Button label="Cancelar" secondary disabled={busy} onPress={() => setRefundItem(undefined)} />
          </Card>}
          {editingPurchase === item.purchase_id && <Card>
            <Text style={label()}>Corrigir parcelas não pagas</Text>
            <Text style={muted()}>Informe quanto será cada parcela e quantas ainda faltam, incluindo a desta fatura. Parcelas anteriores ou já pagas permanecem intactas.</Text>
            <Text style={label()}>Valor de cada parcela (R$)</Text>
            <MoneyInput accessibilityLabel="Novo valor de cada parcela" style={input()}
              value={installmentAmount} onChangeText={setInstallmentAmount} />
            <Text style={label()}>Quantidade de parcelas restantes</Text>
            <TextInput accessibilityLabel="Quantidade de parcelas restantes da compra" style={input()}
              keyboardType="number-pad" maxLength={3} value={remainingCount} onChangeText={setRemainingCount} />
            {!!parseCents(installmentAmount) && Number(remainingCount) > 0 &&
              <Text style={muted()}>Novo total a lançar: {money(parseCents(installmentAmount)! * Number(remainingCount))}.</Text>}
            {current.month.slice(0, 7) <= monthIso(new Date()) && (item.refunded_cents || 0) < item.amount_cents &&
              <Button label="Registrar estorno" secondary disabled={busy} onPress={() => startRefund(item)} />}
            <Button label={busy ? 'Salvando…' : 'Salvar correção'}
              onPress={() => { if (!busy) void saveCorrection(); }} />
            <Button label="Excluir compra" secondary onPress={confirmDeletePurchase} disabled={busy} />
            <Button label="Cancelar" secondary onPress={() => setEditingPurchase(undefined)} />
          </Card>}
        </View>)}
      </Card>
      {current.status === 'open' && current.remaining_cents > 0 && <Card>
        <Text style={label()}>Antecipar pagamento</Text>
        <Text style={muted()}>Você pode pagar antes do fechamento. Novas compras ainda podem entrar nesta fatura e aumentar o saldo.</Text>
        {!advanceOpen ? <Button label="Antecipar pagamento" secondary onPress={() => startAdvance(current)} /> : <>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{accounts.filter(a => a.kind === 'bank').map(a =>
            <Chip key={a.id} label={a.name} selected={payAccount === a.id} onPress={() => setPayAccount(a.id)} />)}</View>
          <Text style={label()}>Valor a antecipar *</Text>
          <MoneyInput accessibilityLabel="Valor da antecipação" style={input()} value={advanceAmount}
            onChangeText={setAdvanceAmount} />
          <Text style={muted()}>Saldo atual da fatura: {money(current.remaining_cents)}. O valor informado sai da conta agora.</Text>
          <Button label={busy ? 'Registrando…' : 'Confirmar antecipação'}
            onPress={() => { if (!busy) void advance(current); }} />
          <Button label="Cancelar" secondary onPress={() => { setAdvanceOpen(false); setError(''); }} />
        </>}
      </Card>}
      {current.status === 'closed' && current.remaining_cents > 0 && <Card>
        <Text style={label()}>Pagar fatura integral</Text>
        <Text style={muted()}>Todas as parcelas desta fatura serão quitadas juntas.</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{accounts.filter(a => a.kind === 'bank').map(a =>
          <Chip key={a.id} label={a.name} selected={payAccount === a.id} onPress={() => setPayAccount(a.id)} />)}</View>
        <Button label={busy ? 'Pagando…' : `Pagar saldo de ${money(current.remaining_cents)}`}
          onPress={() => { if (!busy) void pay(current); }} />
        <Button label="Pagar parcialmente e parcelar restante" secondary
          onPress={() => { setPartialOpen(true); setPartialAmount(centsToInput(Math.min(60000, Math.floor(current.remaining_cents / 2)))); setError(''); }} />
        {partialOpen && <>
          <Text style={label()}>Valor pago agora *</Text>
          <MoneyInput accessibilityLabel="Valor do pagamento parcial" style={input()} value={partialAmount}
            onChangeText={setPartialAmount} />
          <Text style={label()}>Juros e encargos totais *</Text>
          <MoneyInput accessibilityLabel="Juros e encargos do financiamento" style={input()} value={partialFees}
            onChangeText={setPartialFees} placeholder="0,00" />
          <Text style={label()}>Número de parcelas futuras *</Text>
          <TextInput accessibilityLabel="Número de parcelas do financiamento" style={input()} value={partialCount}
            onChangeText={setPartialCount} keyboardType="number-pad" maxLength={3} />
          {(() => {
            const paid = parseCents(partialAmount);
            const fees = parseCents(partialFees) ?? (/^0(?:,0{1,2})?$/.test(partialFees.trim()) ? 0 : null);
            const count = Number(partialCount);
            if (!paid || paid >= current.remaining_cents || fees === null ||
              !Number.isInteger(count) || count < 1) return null;
            return <Text style={muted()}>Sai da conta agora: {money(paid)}. Restante:
              {money(current.remaining_cents - paid)} + encargos {money(fees)} =
              {money(current.remaining_cents - paid + fees)} em {count} {count === 1 ? 'fatura futura' : 'faturas futuras'}.</Text>;
          })()}
          <Button label={busy ? 'Confirmando…' : 'Confirmar pagamento e parcelamento'}
            onPress={() => { if (!busy) void payPartial(current); }} />
          <Button label="Cancelar" secondary onPress={() => { setPartialOpen(false); setError(''); }} />
        </>}
      </Card>}
    </> : <>
      {!editingCard && <Button label={showCreate ? 'Cancelar' : 'Cadastrar cartão'}
        secondary onPress={() => { if (showCreate) cancelCardForm(); else { cancelCardForm(); setShowCreate(true); setLegacyCard(undefined); } }} />}
      {showCreate && !editingCard && cardForm}
      {cards.map(card => <Card key={card.id}>
        <Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>{card.name}</Text>
        <Text style={muted()}>Fecha dia {card.closing_day} · vence dia {card.due_day}</Text>
        <Button label="Editar cartão" secondary onPress={() => startEditCard(card)} />
        {editingCard === card.id && cardForm}
        <Button label="Lançar parcelas antigas" secondary onPress={() => startLegacy(card)} />
        {legacyCard === card.id && <Card>
          <Text style={label()}>Parcelas antigas · {card.name}</Text>
          <Text style={muted()}>Informe o valor de cada parcela e quantas faltam. A primeira entra na fatura de {monthIso(new Date()).split('-').reverse().join('/')}.</Text>
          <Text style={label()}>Valor de cada parcela *</Text>
          <MoneyInput accessibilityLabel="Valor de cada parcela antiga" style={input()} value={legacyAmount}
            onChangeText={setLegacyAmount} />
          <Text style={label()}>Quantidade de parcelas restantes *</Text>
          <TextInput accessibilityLabel="Quantidade de parcelas restantes" style={input()} value={legacyCount}
            onChangeText={setLegacyCount} keyboardType="number-pad" maxLength={3} />
          <Text style={label()}>Categoria *</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{categories.filter(item => item.active).map(item =>
            <Chip key={item.id} label={item.name} selected={legacyCategory === item.id}
              onPress={() => { Keyboard.dismiss(); setLegacyCategory(item.id); setLegacySubcategory(''); }} />)}</View>
          <CategoryCreator kind="categoria" existing={categories.map(item => item.name)} onCreate={createLegacyCategory} />
          <Text style={label()}>Subcategoria *</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{selectedLegacyCategory
            ?.subcategories.filter(item => item.active).map(item =>
              <Chip key={item.id} label={item.name} selected={legacySubcategory === item.id}
                onPress={() => { Keyboard.dismiss(); setLegacySubcategory(item.id); }} />)}</View>
          {selectedLegacyCategory?.active && <CategoryCreator key={selectedLegacyCategory.id} kind="subcategoria" existing={selectedLegacyCategory.subcategories.map(item => item.name)} onCreate={createLegacySubcategory} />}
          <Text style={label()}>Observação (opcional)</Text>
          <TextInput accessibilityLabel="Observação da compra antiga" style={input()} value={legacyNote}
            onChangeText={setLegacyNote} maxLength={200} placeholder="Ex.: Compra antiga" />
          <Button label={busy ? 'Salvando…' : 'Lançar parcelas'} onPress={() => { if (!busy) void saveLegacy(); }} />
          <Button label="Cancelar" secondary onPress={() => setLegacyCard(undefined)} />
        </Card>}
        {invoices.filter(i => i.card_id === card.id).length ? invoices.filter(i => i.card_id === card.id).map(invoice =>
          <Button key={invoice.id} secondary
            label={`${invoice.month.slice(0, 7).split('-').reverse().join('/')} · saldo ${money(invoice.remaining_cents)} · ${invoice.status === 'refinanced' ? 'Parcelada' : invoice.status === 'paid' ? 'Paga' : invoice.status === 'settled' ? 'Quitada' : invoice.status === 'open' ? 'Aberta' : 'Fechada'}`}
            onPress={() => { setSelected(invoice.id); setPartialOpen(false); setAdvanceOpen(false); setPartialAmount(centsToInput(Math.min(60000, Math.floor(invoice.remaining_cents / 2)))); setPartialFees('0,00'); setPartialCount('2'); }} />) :
          <Text style={muted()}>Ainda não há compras neste cartão.</Text>}
      </Card>)}
      {!cards.length && <Card><Text style={muted()}>Cadastre seu primeiro cartão para lançar compras parceladas.</Text></Card>}
    </>}
  </View>;
}
