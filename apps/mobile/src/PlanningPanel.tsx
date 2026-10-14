import React, { useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { Member, request, Workspace } from './api';
import { Account, Category, CreditCard, Subcategory } from './finance';
import { localDate, money, parseCents, validDate } from './prototype';
import { MoneyInput } from './MoneyInput';
import { CategoryCreator } from './CategoryCreator';
import { Button, Card, Chip, palette } from './ui';
import { useToastSetter } from './Toast';

type Rule = { id: string; kind: 'expense' | 'card'; description: string; amount_cents: number; day_of_month: number; category_id: string; subcategory_id: string; payment_method: 'pix' | 'debit' | 'cash' | null; card_id: string | null; active: boolean };
type Occurrence = { id: string; rule_id: string; kind: 'expense' | 'card'; description: string; due_on: string; amount_cents: number; expense_id: string | null; purchase_id: string | null; paid_cents: number | null; payment_method: 'pix' | 'debit' | 'cash' | null };
type Plan = { id: string; description: string; amount_cents: number; day_of_month: number; responsible_user_id: string; active: boolean };
type Expected = { id: string; description: string; due_on: string; expected_cents: number; received_cents: number; remaining_cents: number; completed: boolean; responsible_user_id: string };
const input = () => ({ backgroundColor: palette.white, borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink });
const display = (cents: number) => (cents / 100).toFixed(2).replace('.', ',');
const dateToIso = (value: string) => value.split('/').reverse().join('-');
const label = (name: string, value: string, onChangeText: (value: string) => void, props = {}) => <View style={{gap:5}}><Text style={{color:palette.ink,fontWeight:'600'}}>{name}</Text><TextInput accessibilityLabel={name} style={input()} value={value} onChangeText={onChangeText} {...props} /></View>;
const moneyLabel = (name: string, value: string, onChangeText: (value: string) => void) => <View style={{gap:5}}><Text style={{color:palette.ink,fontWeight:'600'}}>{name}</Text><MoneyInput accessibilityLabel={name} style={input()} value={value} onChangeText={onChangeText} /></View>;

export function PlanningPanel({workspace, token, period, refresh, onChanged, startCreate, startCreateRequest, onCreated}: {workspace: Workspace; token: string; period: string; refresh: number; onChanged: () => void; startCreate?: 'expense' | 'card'; startCreateRequest?: number; onCreated?: (kind: 'expense' | 'card') => void}) {
  const root = `/workspaces/${workspace.id}`;
  const [rules, setRules] = useState<Rule[]>([]);
  const [occurrences, setOccurrences] = useState<Occurrence[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [expected, setExpected] = useState<Expected[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [mode, setMode] = useState<'expense' | 'card' | 'income' | null>(null);
  const [editing, setEditing] = useState<string>();
  const [openRuleMenu, setOpenRuleMenu] = useState<string | null>(null);
  const handledCreateRequest = useRef<number | undefined>(undefined);
  const [loaded, setLoaded] = useState(false);
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [day, setDay] = useState(String(new Date().getDate()));
  const [categoryId, setCategoryId] = useState('');
  const [subcategoryId, setSubcategoryId] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<'pix' | 'debit' | 'cash'>('pix');
  const [cardId, setCardId] = useState('');
  const [responsibleId, setResponsibleId] = useState('');
  const [paying, setPaying] = useState<Occurrence>();
  const [receiving, setReceiving] = useState<Expected>();
  const [actual, setActual] = useState('');
  const [accountId, setAccountId] = useState('');
  const [date, setDate] = useState(localDate());
  const [complete, setComplete] = useState(true);
  const [busy, setBusy] = useState(false);
  const setError = useToastSetter('error');
  const setNotice = useToastSetter('success');

  async function load() {
    const [r, o, p, e, a, c, cats, m] = await Promise.all([
      request<Rule[]>(`${root}/recurring-rules`, token),
      request<Occurrence[]>(`${root}/recurring-occurrences?month=${period}`, token),
      request<Plan[]>(`${root}/income-plans`, token),
      request<Expected[]>(`${root}/income-occurrences?month=${period}`, token),
      request<Account[]>(`${root}/accounts`, token), request<CreditCard[]>(`${root}/cards`, token),
      request<Category[]>(`${root}/categories`, token),
      request<Member[]>(`${root}/members`, token),
    ]);
    setRules(r); setOccurrences(o); setPlans(p); setExpected(e);
    setAccounts(a); setCards(c); setCategories(cats); setMembers(m);
  }
  useEffect(() => {
    setLoaded(false);
    void load().then(() => setLoaded(true))
      .catch(e => setError(e instanceof Error ? e.message : 'Não foi possível carregar o planejamento.'));
  }, [workspace.id, period, refresh]);
  async function action(work: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await work(); await load(); onChanged(); return true; }
    catch(e) { setError(e instanceof Error ? e.message : 'Não foi possível concluir.'); return false; }
    finally { setBusy(false); }
  }
  function start(next: 'expense' | 'card' | 'income', item?: Rule | Plan) {
    setMode(next); setEditing(item?.id); setDescription(item?.description || '');
    setAmount(item ? display(item.amount_cents) : '');
    setDay(String(item?.day_of_month || new Date().getDate()));
    setCategoryId(next === 'income' ? '' : (item as Rule)?.category_id || categories.find(c => c.active)?.id || '');
    setSubcategoryId(next === 'income' ? '' : (item as Rule)?.subcategory_id || categories.find(c => c.active)?.subcategories.find(s => s.active)?.id || '');
    setPaymentMethod((item as Rule)?.payment_method || 'pix');
    setCardId((item as Rule)?.card_id || cards.find(c => c.active)?.id || '');
    setResponsibleId((item as Plan)?.responsible_user_id || members[0]?.id || '');
    setError('');
  }
  useEffect(() => {
    if (!loaded || !startCreate || !startCreateRequest || handledCreateRequest.current === startCreateRequest) return;
    handledCreateRequest.current = startCreateRequest;
    start(startCreate);
  }, [startCreate, startCreateRequest, loaded]);
  async function save() {
    const createdKind = !editing && mode !== 'income' ? mode : null;
    const cents = parseCents(amount);
    if (!description.trim() || cents === null) { setError('Informe a descrição e um valor válido.'); return; }
    if (mode !== 'income') {
      const chosenCategory = categories.find(item => item.id === categoryId);
      if (!chosenCategory) { setError('Escolha uma categoria.'); return; }
      if (!chosenCategory.subcategories.some(item => item.id === subcategoryId)) {
        setError('Escolha uma subcategoria.'); return;
      }
    }
    const dueDay = Number(day);
    if (!Number.isInteger(dueDay) || dueDay < 1 || dueDay > 31) { setError('Informe um dia entre 1 e 31.'); return; }
    const saved = await action(async () => {
      if (mode === 'income') {
        await request(`${root}/income-plans${editing ? '/' + editing : ''}`, token, editing ? 'PATCH' : 'POST', {
          description: description.trim(), amount_cents: cents, day_of_month: dueDay,
          responsible_user_id: responsibleId,
        });
      } else {
        await request(`${root}/recurring-rules${editing ? '/' + editing : ''}`, token, editing ? 'PATCH' : 'POST', {
          kind: mode, description: description.trim(), amount_cents: cents,
          day_of_month: dueDay, category_id: categoryId, subcategory_id: subcategoryId,
          payment_method: mode === 'expense' ? paymentMethod : null,
          card_id: mode === 'card' ? cardId : null,
        });
      }
      setMode(null); setEditing(undefined); setNotice('Planejamento salvo.');
    });
    if (saved && createdKind) onCreated?.(createdKind);
  }
  function startPay(item: Occurrence) {
    setPaying(item); setReceiving(undefined); setActual(display(item.amount_cents));
    const method = item.payment_method || 'pix';
    setAccountId(accounts.find(account => account.kind === (method === 'cash' ? 'cash' : 'bank'))?.id || '');
    setPaymentMethod(method);
    setDate(localDate()); setError('');
  }
  function selectPaymentMethod(method: 'pix' | 'debit' | 'cash') {
    setPaymentMethod(method);
    const eligible = accounts.filter(account => account.kind === (method === 'cash' ? 'cash' : 'bank'));
    if (!eligible.some(account => account.id === accountId)) setAccountId(eligible[0]?.id || '');
  }
  function startReceive(item: Expected) {
    setReceiving(item); setPaying(undefined); setActual(display(item.remaining_cents));
    setAccountId(accounts[0]?.id || ''); setComplete(true); setDate(localDate()); setError('');
  }
  async function submitMoney() {
    const cents = parseCents(actual);
    if (cents === null || !validDate(date) || !accountId) { setError('Informe conta, valor e data válidos.'); return; }
    await action(async () => {
      if (paying) {
        await request(`${root}/recurring-occurrences/${paying.id}/pay`, token, 'POST', {
          account_id: accountId, amount_cents: cents, occurred_on: dateToIso(date), payment_method: paymentMethod,
        });
        setPaying(undefined); setNotice('Despesa paga e saldo atualizado.');
      } else if (receiving) {
        await request(`${root}/income-occurrences/${receiving.id}/receive`, token, 'POST', {
          account_id: accountId, amount_cents: cents, occurred_on: dateToIso(date),
          complete, request_id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        });
        setReceiving(undefined); setNotice('Receita recebida e saldo atualizado.');
      }
    });
  }
  const currentMonth = dateToIso(localDate()).slice(0, 7) === period;
  const activeRules = rules.filter(rule => rule.active && period >= dateToIso(localDate()).slice(0, 7));
  const occurrencesByRule = new Map(occurrences.map(item => [item.rule_id, item]));
  const activeRuleIds = new Set(activeRules.map(rule => rule.id));
  const selectedCategory = categories.find(c => c.id === categoryId);
  const visibleCategories = categories.filter(item => item.active || item.id === categoryId);
  const visibleSubcategories = selectedCategory?.subcategories.filter(item => item.active || item.id === subcategoryId) || [];
  function paymentForm(item: Occurrence) {
    if (paying?.id !== item.id) return null;
    const eligible = accounts.filter(account => account.kind === (paymentMethod === 'cash' ? 'cash' : 'bank'));
    return <View style={{gap:8,marginTop:8}}>
      <Text style={{fontSize:18,fontWeight:'700',color:palette.ink}}>Pagar {item.description}</Text>
      <Text style={{color:palette.ink}}>Forma de pagamento</Text>
      <View style={{flexDirection:'row',gap:8}}>{(['pix','debit','cash'] as const).map(method =>
        <Chip key={method} label={{pix:'Pix',debit:'Débito',cash:'Dinheiro'}[method]}
          selected={paymentMethod === method} onPress={() => selectPaymentMethod(method)} />)}</View>
      <Text style={{color:palette.ink}}>Conta</Text>
      {eligible.length ? <ScrollView horizontal contentContainerStyle={{gap:8}}>{eligible.map(account =>
        <Chip key={account.id} label={account.name} selected={accountId === account.id}
          onPress={() => setAccountId(account.id)} />)}</ScrollView> :
        <Text style={{color:palette.muted}}>Cadastre uma conta {paymentMethod === 'cash' ? 'dinheiro' : 'bancária'} para pagar desta forma.</Text>}
      {moneyLabel('Valor real (R$)', actual, setActual)}
      {label('Data (DD/MM/AAAA)', date, setDate, {keyboardType:'numbers-and-punctuation'})}
      <Button label={busy ? 'Salvando…' : 'Confirmar pagamento'} onPress={() => { if (!busy) void submitMoney(); }} />
      <Button label="Cancelar" secondary onPress={() => setPaying(undefined)} />
    </View>;
  }
  async function createCategory(name: string) {
    const created = await request<Category>(`${root}/categories`, token, 'POST', { name });
    setCategories(items => [...items, created].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')));
    setCategoryId(created.id); setSubcategoryId('');
  }
  async function createSubcategory(name: string) {
    if (!selectedCategory) return;
    const created = await request<Subcategory>(`${root}/categories/${selectedCategory.id}/subcategories`, token, 'POST', { name });
    setCategories(items => items.map(item => item.id === selectedCategory.id ?
      { ...item, subcategories: [...item.subcategories, created].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')) } : item));
    setSubcategoryId(created.id);
  }
  return <View style={{gap:16}}>
    <Text style={{fontSize:28,fontWeight:'700',color:palette.ink}}>Planejamento</Text>
    <Text style={{color:palette.muted}}>Contas fixas, assinaturas e rendas previstas de {period.slice(5)}/{period.slice(0,4)}.</Text>
    <View style={{gap:8}}><Button label="Nova despesa fixa" onPress={() => start('expense')} /><Button label="Nova assinatura no cartão" secondary onPress={() => start('card')} /><Button label="Nova renda prevista" secondary onPress={() => start('income')} /></View>
    {mode && <Card>
      <Text style={{fontSize:20,color:palette.ink,fontWeight:'700'}}>{editing ? 'Editar' : 'Cadastrar'} {mode === 'expense' ? 'despesa fixa' : mode === 'card' ? 'assinatura no cartão' : 'renda prevista'}</Text>
      {label('Descrição', description, setDescription)}
      {moneyLabel('Valor mensal (R$)', amount, setAmount)}
      {label('Dia do mês', day, setDay, {keyboardType:'number-pad'})}
      {mode === 'income' ? <><Text style={{ color: palette.ink }}>Responsável pelo recebimento</Text><ScrollView horizontal contentContainerStyle={{gap:8}}>{members.map(m => <Chip key={m.id} label={m.email} selected={responsibleId === m.id} onPress={() => setResponsibleId(m.id)} />)}</ScrollView></> : <>
        <Text style={{ color: palette.ink }}>Categoria</Text><ScrollView horizontal contentContainerStyle={{gap:8}}>{visibleCategories.map(c => <Chip key={c.id} label={c.name} selected={categoryId === c.id} onPress={() => { setCategoryId(c.id); setSubcategoryId(c.subcategories.find(s => s.active)?.id || ''); }} />)}</ScrollView>
        <CategoryCreator kind="categoria" existing={categories.map(item => item.name)} onCreate={createCategory} />
        <Text style={{ color: palette.ink }}>Subcategoria</Text>
        {selectedCategory ? <ScrollView horizontal contentContainerStyle={{gap:8}}>{visibleSubcategories.map(s => <Chip key={s.id} label={s.name} selected={subcategoryId === s.id} onPress={() => setSubcategoryId(s.id)} />)}</ScrollView> :
          <Text style={{ color: palette.muted }}>Selecione ou crie uma categoria acima.</Text>}
        {selectedCategory?.active && <CategoryCreator key={selectedCategory.id} kind="subcategoria" existing={selectedCategory.subcategories.map(item => item.name)} onCreate={createSubcategory} />}
        {mode === 'card' ? <><Text style={{ color: palette.ink }}>Cartão</Text><ScrollView horizontal contentContainerStyle={{gap:8}}>{cards.filter(c => c.active).map(c => <Chip key={c.id} label={c.name} selected={cardId === c.id} onPress={() => setCardId(c.id)} />)}</ScrollView></> : <><Text style={{ color: palette.ink }}>Forma de pagamento</Text><View style={{flexDirection:'row',gap:8}}>{(['pix','debit','cash'] as const).map(method => <Chip key={method} label={{pix:'Pix',debit:'Débito',cash:'Dinheiro'}[method]} selected={paymentMethod === method} onPress={() => setPaymentMethod(method)} />)}</View></>}
      </>}
      <Button label={busy ? 'Salvando…' : 'Salvar'} onPress={() => { if (!busy) void save(); }} />
      <Button label="Cancelar" secondary onPress={() => setMode(null)} />
    </Card>}
    <Text style={{fontSize:20,fontWeight:'700',color:palette.ink}}>Despesas fixas e assinaturas</Text>
    {activeRules.map(rule => {
      const item = occurrencesByRule.get(rule.id);
      return <Card key={rule.id}>
        <View style={{flexDirection:'row',alignItems:'flex-start',gap:8}}>
          <Text style={{fontWeight:'700',color:palette.ink,flex:1}}>{item?.description || rule.description} · {money(item?.paid_cents ?? item?.amount_cents ?? rule.amount_cents)}</Text>
          <Pressable accessibilityRole="button" accessibilityLabel={`Opções de ${rule.description}`} onPress={() => setOpenRuleMenu(openRuleMenu === rule.id ? null : rule.id)} style={{minWidth:44,minHeight:44,alignItems:'center',justifyContent:'center'}}>
            <Text style={{color:palette.green,fontSize:26,lineHeight:30}}>⋯</Text>
          </Pressable>
        </View>
        <Text style={{color:palette.ink}}>{rule.kind === 'card' ? item?.purchase_id ? 'Assinatura lançada no cartão' : 'Assinatura prevista no cartão' : item?.expense_id ? 'Despesa paga' : 'Despesa fixa prevista'} · {item ? `vence em ${item.due_on.split('-').reverse().join('/')}` : `todo dia ${rule.day_of_month}`}</Text>
        {item?.kind === 'expense' && !item.expense_id && currentMonth && <>
          <Button label="Registrar pagamento" onPress={() => startPay(item)} />
          {paymentForm(item)}
        </>}
        {openRuleMenu === rule.id && <View style={{gap:8}}>
          <Button label="Editar atual e futuras" secondary onPress={() => { setOpenRuleMenu(null); start(rule.kind, rule); }} />
          <Button label="Desativar próximas ocorrências" secondary onPress={() => { setOpenRuleMenu(null); void action(async () => { await request(`${root}/recurring-rules/${rule.id}`, token, 'DELETE'); setNotice('Recorrência desativada. O histórico foi preservado.'); }); }} />
        </View>}
      </Card>;
    })}
    {occurrences.filter(item => !activeRuleIds.has(item.rule_id)).map(item => <Card key={item.id}>
      <Text style={{fontWeight:'700',color:palette.ink}}>{item.description} · {money(item.paid_cents ?? item.amount_cents)}</Text>
      <Text style={{color:palette.ink}}>{item.kind === 'card' ? item.purchase_id ? 'Assinatura lançada no cartão' : 'Assinatura prevista no cartão' : item.expense_id ? 'Despesa paga' : 'Despesa fixa prevista'} · vence em {item.due_on.split('-').reverse().join('/')}</Text>
      {item.kind === 'expense' && !item.expense_id && currentMonth && <>
        <Button label="Registrar pagamento" onPress={() => startPay(item)} />
        {paymentForm(item)}
      </>}
    </Card>)}
    <Text style={{fontSize:20,fontWeight:'700',color:palette.ink}}>Rendas previstas</Text>
    {plans.filter(p => p.active).map(plan => <Card key={plan.id}>
      <Text style={{fontWeight:'700',color:palette.ink}}>{plan.description} · {money(plan.amount_cents)}</Text>
      <Text style={{ color: palette.ink }}>Todo dia {plan.day_of_month} · {members.find(m => m.id === plan.responsible_user_id)?.email || 'Responsável'}</Text>
      <Button label="Editar atual e futuras" secondary onPress={() => start('income', plan)} />
      <Button label="Desativar próximas previsões" secondary onPress={() => void action(async () => { await request(`${root}/income-plans/${plan.id}`, token, 'DELETE'); setNotice('Previsão desativada. O histórico foi preservado.'); })} />
    </Card>)}
    {expected.map(item => <Card key={item.id}>
      <Text style={{fontWeight:'700',color:palette.ink}}>{item.description} · {money(item.expected_cents)}</Text>
      <Text style={{ color: palette.ink }}>Recebido: {money(item.received_cents)} · restante: {money(item.remaining_cents)} · dia {item.due_on.slice(-2)}</Text>
      {!item.completed && currentMonth && <><Button label="Registrar recebimento" onPress={() => startReceive(item)} /><Button label="Ajustar só este mês" secondary onPress={() => { setActual(display(item.expected_cents)); setReceiving(undefined); setPaying(undefined); setEditing(item.id); setMode(null); }} /></>}
      {editing === item.id && !mode && <>{moneyLabel('Novo valor previsto (R$)', actual, setActual)}<Button label="Salvar ajuste do mês" onPress={() => void action(async () => { const cents = parseCents(actual); if (cents === null) throw new Error('Informe um valor válido.'); await request(`${root}/income-occurrences/${item.id}`, token, 'PATCH', {expected_cents:cents}); setEditing(undefined); setNotice('Ajuste aplicado somente a este mês.'); })} /></>}
    </Card>)}
    {receiving && <Card>
      <Text style={{fontSize:20,fontWeight:'700',color:palette.ink}}>Receber renda prevista</Text>
      <Text style={{ color: palette.ink }}>Conta</Text><ScrollView horizontal contentContainerStyle={{gap:8}}>{accounts.map(a => <Chip key={a.id} label={a.name} selected={accountId === a.id} onPress={() => setAccountId(a.id)} />)}</ScrollView>
      {moneyLabel('Valor real (R$)', actual, setActual)}
      {label('Data (DD/MM/AAAA)', date, setDate, {keyboardType:'numbers-and-punctuation'})}
      <Text style={{ color: palette.ink }}>Depois deste recebimento</Text><View style={{flexDirection:'row',gap:8}}><Chip label="Concluir previsão" selected={complete} onPress={() => setComplete(true)} /><Chip label="Manter diferença" selected={!complete} onPress={() => setComplete(false)} /></View>
      <Button label={busy ? 'Salvando…' : 'Confirmar'} onPress={() => { if (!busy) void submitMoney(); }} />
      <Button label="Cancelar" secondary onPress={() => { setPaying(undefined); setReceiving(undefined); }} />
    </Card>}
  </View>;
}
