import React, { useEffect, useState } from 'react';
import { Alert, AppState, BackHandler, Image, Modal, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { ExpenseForm } from './src/ExpenseForm';
import { money } from './src/prototype';
import { CategoryCreator } from './src/CategoryCreator';
import { ToastProvider, ToastViewport, useToastSetter } from './src/Toast';
import { AccessGate } from './src/AccessGate';
import { AccountsPanel } from './src/AccountsPanel';
import { CardPanel } from './src/CardPanel';
import { PlanningPanel } from './src/PlanningPanel';
import { IncomeReminder } from './src/IncomeReminder';
import { ProjectionPanel } from './src/ProjectionPanel';
import { MonthlyReport } from './src/MonthlyReport';
import { request, Workspace } from './src/api';
import { Account, Category, Expense, ExpenseInput, Subcategory, CreditCard, CardInstallment, CardPurchaseInput, FinancingInstallment, dateToDisplay, monthIso, paymentLabel } from './src/finance';
import { applyTheme, Button, Card, palette, ThemeMode } from './src/ui';
import { readThemePreference, saveThemePreference } from './src/themePreference';
import { readOnboardingStep, saveOnboardingStep } from './src/onboardingProgress';
import { FirstRunGuide } from './src/FirstRunGuide';
import { chartColor, PieChart, PieSegment } from './src/PieChart';

type Tab = 'Resumo' | 'Contas' | 'Cartões' | 'Planejamento';
export default function App() {
  const [theme, setTheme] = useState<ThemeMode>('light');
  useEffect(() => { void readThemePreference().then(setTheme).catch(() => {}); }, []);
  useEffect(() => { if (Platform.OS === 'web') document.title = 'Meu Controle'; }, []);
  applyTheme(theme);
  function toggleTheme() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    void saveThemePreference(next).catch(() => {});
  }
  return <SafeAreaProvider><ToastProvider><View style={{ flex: 1, backgroundColor: palette.bg }}><StatusBar style={theme === 'dark' ? 'light' : 'dark'} /><AccessGate theme={theme} onToggleTheme={toggleTheme}>{(workspace, token, userId, openMembers, logout) =>
    <Home key={`${workspace.id}:${userId}`} workspace={workspace} token={token} userId={userId} theme={theme} onToggleTheme={toggleTheme} onOpenMembers={openMembers} onLogout={logout} />
  }</AccessGate><ToastViewport /></View></ToastProvider></SafeAreaProvider>;
}

type GuideAction = 'account' | 'card' | 'expense' | 'card-rule';
function Home({ workspace, token, userId, theme, onToggleTheme, onOpenMembers, onLogout }: { workspace: Workspace; token: string; userId: string; theme: ThemeMode; onToggleTheme: () => void; onOpenMembers: () => void; onLogout: () => void }) {
  const s = makeStyles();
  const root = `/workspaces/${workspace.id}`;
  const [categories, setCategories] = useState<Category[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [rules, setRules] = useState<{kind: 'expense' | 'card'; active: boolean}[]>([]);
  const [guideStep, setGuideStep] = useState<number | null>(null);
  const [guideReady, setGuideReady] = useState(false);
  const [guideAction, setGuideAction] = useState<{kind: GuideAction; id: number} | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [financed, setFinanced] = useState<FinancingInstallment[]>([]);
  const [tab, setTab] = useState<Tab>('Resumo');
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [detail, setDetail] = useState<string | null>(null);
  const [form, setForm] = useState(false);
  const [editing, setEditing] = useState<Expense>();
  const [manageCategories, setManageCategories] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const setNotice = useToastSetter('success');
  const setError = useToastSetter('error');
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const period = monthIso(month);
  const category = categories.find(item => item.id === detail);
  const consumptionTotal = expenses.reduce((sum, item) => sum + item.amount_cents, 0);
  const financedTotal = financed.reduce((sum, item) => sum + item.amount_cents, 0);
  const total = consumptionTotal + financedTotal;
  const monthName = month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  const monthTitle = monthName.charAt(0).toUpperCase() + monthName.slice(1);
  const currentMonth = monthIso(new Date());
  const guideActive = guideStep !== null && guideStep < 4;
  const guideExists = guideStep === 0 ? accounts.length > 0 : guideStep === 1 ? cards.length > 0 :
    guideStep === 2 ? rules.some(rule => rule.active && rule.kind === 'expense') :
    guideStep === 3 ? rules.some(rule => rule.active && rule.kind === 'card') : false;

  useEffect(() => {
    let active = true;
    setGuideReady(false);
    void readOnboardingStep(userId).then(step => { if (active) setGuideStep(step); })
      .catch(() => { if (active) setGuideStep(null); })
      .finally(() => { if (active) setGuideReady(true); });
    return () => { active = false; };
  }, [userId]);

  function advanceGuide() {
    if (guideStep === null) return;
    const next = Math.min(4, guideStep + 1);
    setGuideStep(next); setGuideAction(null); setTab('Resumo');
    void saveOnboardingStep(userId, next).catch(() => setError('Não foi possível salvar o progresso do guia.'));
  }
  function finishGuide() {
    setGuideStep(4); setGuideAction(null); setTab('Resumo');
    void saveOnboardingStep(userId, 4).catch(() => setError('Não foi possível salvar o progresso do guia.'));
  }
  function openGuideForm() {
    if (guideStep === null) return;
    const kind: GuideAction = guideStep === 0 ? 'account' : guideStep === 1 || (guideStep === 3 && cards.length === 0) ? 'card' : guideStep === 2 ? 'expense' : 'card-rule';
    setGuideAction(value => ({ kind, id: (value?.id || 0) + 1 }));
    setTab(kind === 'account' ? 'Contas' : kind === 'card' ? 'Cartões' : 'Planejamento');
  }
  function createdGuideItem(kind: GuideAction) {
    setRefresh(value => value + 1);
    if (guideStep === 0 && kind === 'account') { setGuideAction(null); setTab('Resumo'); }
    else if ((guideStep === 1 && kind === 'card') ||
      (guideStep === 2 && kind === 'expense') || (guideStep === 3 && kind === 'card-rule')) advanceGuide();
    else if (guideStep === 3 && kind === 'card') { setGuideAction(null); setTab('Resumo'); }
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      request<Category[]>(`${root}/categories`, token),
      request<Account[]>(`${root}/accounts`, token),
      request<Expense[]>(`${root}/expenses?month=${period}`, token),
      request<CardInstallment[]>(`${root}/card-installments?month=${period}`, token),
      request<CreditCard[]>(`${root}/cards`, token),
      request<{kind: 'expense' | 'card'; active: boolean}[]>(`${root}/recurring-rules`, token),
      request<FinancingInstallment[]>(`${root}/invoice-financing-installments?month=${period}`, token),
      request<{id:string;kind:'expense'|'card';description:string;due_on:string;amount_cents:number;category_id:string;subcategory_id:string;payment_method:'pix'|'debit'|'cash'|null;expense_id:string|null}[]>(`${root}/recurring-occurrences?month=${period}`, token),
    ]).then(([cats, accs, rows, installments, cardRows, ruleRows, financedRows, recurring]) => {
      if (!active) return;
      setCategories(cats); setAccounts(accs); setCards(cardRows); setRules(ruleRows); setFinanced(financedRows);
      setExpenses([...rows, ...installments.map(item => ({
        id: item.id, account_id: '', category_id: item.category_id,
        subcategory_id: item.subcategory_id, amount_cents: item.amount_cents,
        occurred_on: item.purchased_on, payment_method: 'credit' as const,
        note: item.note, card_name: item.card_name, sequence: item.sequence,
        total_count: item.total_count, invoice_paid: item.invoice_paid,
      })), ...recurring.filter(item => item.kind === 'expense' && !item.expense_id).map(item => ({
        id: item.id, account_id: '', category_id: item.category_id,
        subcategory_id: item.subcategory_id, amount_cents: item.amount_cents,
        occurred_on: item.due_on, payment_method: (item.payment_method || 'pix') as 'pix'|'debit'|'cash',
        note: item.description, forecast: true,
      }))]); setError('');
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Não foi possível carregar o resumo.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [root, token, period, refresh]);

  useEffect(() => {
    const listener = BackHandler.addEventListener('hardwareBackPress', () => {
      if (menuOpen) { setMenuOpen(false); return true; }
      if (detail) { setDetail(null); return true; }
      if (tab !== 'Resumo') { setTab('Resumo'); return true; }
      return false;
    });
    return () => listener.remove();
  }, [detail, tab, menuOpen]);
  useEffect(() => {
    const listener = AppState.addEventListener('change', state => {
      if (state === 'active') setRefresh(value => value + 1);
    });
    return () => listener.remove();
  }, []);

  async function addCategory(name: string) {
    const created = await request<Category>(`${root}/categories`, token, 'POST', { name });
    setCategories(items => [...items, created].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')));
    return created;
  }
  async function addSubcategory(categoryId: string, name: string) {
    const created = await request<Subcategory>(`${root}/categories/${categoryId}/subcategories`, token, 'POST', { name });
    setCategories(items => items.map(item => item.id === categoryId ?
      { ...item, subcategories: [...item.subcategories, created].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')) } : item));
    return created;
  }
  async function restoreCategory(item: Category) {
    const restored = await request<Category>(`${root}/categories`, token, 'POST',
      { name: item.name, color: item.color });
    setCategories(items => items.map(old => old.id === item.id ? restored : old));
    setNotice('Categoria reativada.');
  }
  async function restoreSubcategory(categoryId: string, sub: Subcategory) {
    const restored = await request<Subcategory>(
      `${root}/categories/${categoryId}/subcategories`, token, 'POST', { name: sub.name });
    setCategories(items => items.map(item => item.id === categoryId ?
      { ...item, subcategories: item.subcategories.map(old => old.id === sub.id ? restored : old) } : item));
    setNotice('Subcategoria reativada.');
  }
  async function deactivate(path: string) {
    await request(`${root}${path}`, token, 'DELETE');
    setCategories(await request<Category[]>(`${root}/categories`, token));
    setNotice('Categoria atualizada. O histórico permanece disponível.');
  }
  function confirmAction(title: string, action: () => Promise<void>) {
    const run = () => { void action().catch(e => setError(e instanceof Error ? e.message : 'Não foi possível concluir.')); };
    if (Platform.OS === 'web') { if (window.confirm(title)) run(); }
    else Alert.alert(title, 'Os lançamentos anteriores serão preservados.', [
      { text: 'Cancelar', style: 'cancel' }, { text: 'Continuar', onPress: run },
    ]);
  }
  async function openNewExpense() {
    try {
      setAccounts(await request<Account[]>(`${root}/accounts`, token));
      setEditing(undefined); setForm(true); setError('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível carregar as contas.'); }
  }
  async function saveExpense(input: ExpenseInput) {
    await request(`${root}/expenses${editing ? '/' + editing.id : ''}`, token, editing ? 'PATCH' : 'POST', input);
    const wasEditing = !!editing;
    setForm(false); setEditing(undefined); setDetail(null); setTab('Resumo');
    const [year, number] = input.occurred_on.slice(0, 7).split('-').map(Number);
    setMonth(new Date(year, number - 1, 1));
    setRefresh(value => value + 1);
    setNotice(wasEditing ? 'Despesa atualizada e saldo corrigido.' : 'Despesa salva e descontada da conta.');
  }
  async function saveCredit(input: CardPurchaseInput) {
    await request(`${root}/card-purchases`, token, 'POST', input);
    setForm(false); setEditing(undefined); setDetail(null); setTab('Resumo');
    setRefresh(value => value + 1);
    setNotice('Compra salva nas faturas do cartão. O saldo muda quando a fatura for paga.');
  }
  async function removeExpense(expense: Expense) {
    await request(`${root}/expenses/${expense.id}`, token, 'DELETE');
    setRefresh(value => value + 1);
    setNotice('Despesa excluída. O valor voltou ao saldo da conta.');
  }
  const visible = expenses.filter(item => !detail || item.category_id === detail);
  const chartSegments: PieSegment[] = category ? category.subcategories.map((sub, index) => ({
    id: sub.id, label: sub.name, color: chartColor(index, theme),
    value: visible.filter(item => item.subcategory_id === sub.id).reduce((sum, item) => sum + item.amount_cents, 0),
  })) : [
    ...categories.map((item, index) => ({
      id: item.id, label: item.name, color: chartColor(index, theme),
      value: expenses.filter(row => row.category_id === item.id).reduce((sum, row) => sum + row.amount_cents, 0),
      onPress: () => setDetail(item.id),
    })),
    ...(financedTotal ? [{ id: 'financed', label: 'Faturas parceladas', value: financedTotal,
      color: chartColor(categories.length, theme) }] : []),
  ];
  return <SafeAreaView style={s.safe}>
    <View style={s.shell}>
      <View style={s.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Abrir menu" onPress={() => setMenuOpen(true)} style={s.menuButton}>
          <Text style={s.menuIcon}>☰</Text>
        </Pressable>
        <Image source={require('./assets/meu-controle-icon-concept-v2.png')} accessibilityLabel="Ícone do Meu Controle" style={s.logo} />
        <View style={{ flex: 1 }}><Text style={s.brand}>Meu Controle</Text><Text style={s.small}>Seu dinheiro, com clareza.</Text></View>
        <Pressable accessibilityRole="switch" aria-checked={theme === 'dark'} accessibilityLabel="Modo escuro" onPress={onToggleTheme} style={s.themeToggle}>
          <Text style={s.themeToggleText}>{theme === 'dark' ? '☀ Claro' : '☾ Escuro'}</Text>
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={s.content}>
        {!guideReady ? <Text style={s.small}>Preparando seu espaço…</Text> : <>
        {guideActive && guideStep !== null && (tab === 'Resumo' ?
          <FirstRunGuide step={guideStep} exists={guideExists} hasCard={cards.length > 0}
            onOpen={openGuideForm} onNext={advanceGuide} onFinish={finishGuide} /> :
          <View style={{ gap: 6 }}><Text style={s.small}>PRIMEIROS PASSOS · ETAPA {guideStep + 1} DE 4</Text>
            <Button label="Voltar ao guia" secondary onPress={() => { setGuideAction(null); setTab('Resumo'); }} /></View>)}
        {tab === 'Resumo' ? guideActive ? null : <>
          <View style={s.month}><Pressable accessibilityRole="button" accessibilityLabel="Mês anterior" onPress={() => { setMonth(value => new Date(value.getFullYear(), value.getMonth() - 1, 1)); setNotice(''); }} style={s.arrow}><Text style={s.arrowText}>‹</Text></Pressable><Text style={s.monthText}>{monthTitle}</Text><Pressable accessibilityRole="button" accessibilityLabel="Próximo mês" onPress={() => { setMonth(value => new Date(value.getFullYear(), value.getMonth() + 1, 1)); setNotice(''); }} style={s.arrow}><Text style={s.arrowText}>›</Text></Pressable></View>
          <ProjectionPanel workspace={workspace} token={token} period={period} refresh={refresh} />
          {loading && <Text style={s.small}>Carregando gastos…</Text>}
          <View style={s.hero}><Text style={s.heroLabel}>GASTOS E COMPROMISSOS DO MÊS</Text><Text style={s.heroValue}>{money(total)}</Text><View style={s.heroDivider} /><Text style={s.heroCaption}>Compras e despesas, incluindo fixas pendentes: {money(consumptionTotal)} · Faturas parceladas: {money(financedTotal)}</Text><Text style={s.heroFoot}>Despesa fixa paga substitui a previsão pelo valor real. Compras no cartão ficam no mês da fatura; financiamento futuro não é nova compra.</Text></View>
          <View style={s.section}><Text style={s.sectionTitle}>{category ? category.name : 'Por categoria'}</Text><Text style={s.small}>{category ? 'Subcategorias' : 'Toque para explorar'}</Text></View>
          <Card>
            {category && <Button label="← Todas as categorias" secondary onPress={() => setDetail(null)} />}
            {!total ? <View style={s.empty}><Text style={s.sectionTitle}>Um mês em branco</Text><Text style={s.small}>Use o + para lançar uma despesa ou compra no crédito.</Text></View> :
              category ? category.subcategories.map((sub, index) => {
                const value = visible.filter(item => item.subcategory_id === sub.id).reduce((sum, item) => sum + item.amount_cents, 0);
                const categoryTotal = visible.reduce((sum, item) => sum + item.amount_cents, 0);
                return <Bar key={sub.id} label={sub.name} value={value} total={categoryTotal} color={chartColor(index, theme)} />;
              }) : <>
                {categories.map((item, index) => {
                  const value = expenses.filter(row => row.category_id === item.id).reduce((sum, row) => sum + row.amount_cents, 0);
                  return <Bar key={item.id} label={item.name} value={value} total={total} color={chartColor(index, theme)} onPress={() => setDetail(item.id)} />;
                })}
                {financedTotal > 0 && <Bar label="Faturas parceladas" value={financedTotal} total={total} color={chartColor(categories.length, theme)} />}
              </>}
          </Card>
          <PieChart title={category ? `Subcategorias de ${category.name}` : 'Categorias em gráfico de pizza'} segments={chartSegments} />
          <View style={s.section}><Text style={s.sectionTitle}>Despesas do mês</Text><Text style={s.small}>{visible.length} {visible.length === 1 ? 'item' : 'itens'}</Text></View>
          <Card>{visible.length ? visible.map(item => {
            const cat = categories.find(x => x.id === item.category_id);
            const sub = cat?.subcategories.find(x => x.id === item.subcategory_id);
            const acc = accounts.find(x => x.id === item.account_id);
            return <View key={item.id} style={s.transaction}>
              <View style={[s.transactionDot, { backgroundColor: cat?.color || palette.green }]} />
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={s.itemTitle}>{item.note || sub?.name || 'Despesa'}</Text>
                <Text style={s.small}>{cat?.name || 'Categoria'} · {sub?.name || 'Subcategoria'} · {dateToDisplay(item.occurred_on)}</Text>
                <Text style={s.small}>{item.forecast ? 'Prevista · ainda não paga' : paymentLabel[item.payment_method]} · {item.payment_method === 'credit' ? `${item.card_name} · ${item.sequence}/${item.total_count}` : item.forecast ? 'Conta a escolher no pagamento' : acc?.name || 'Conta'}</Text>
                {item.forecast && <Text accessibilityRole="button" onPress={() => setTab('Planejamento')} style={{color:palette.green}}>Registrar pagamento no Planejamento</Text>}
                {!item.forecast && item.payment_method !== 'credit' && item.occurred_on.slice(0, 7) === currentMonth && <View style={{ flexDirection: 'row', gap: 16 }}>
                  <Text accessibilityRole="button" onPress={() => { setEditing(item); setForm(true); }} style={{ color: palette.green }}>Editar</Text>
                  <Text accessibilityRole="button" onPress={() => confirmAction('Excluir despesa?', () => removeExpense(item))} style={{ color: palette.danger }}>Excluir</Text>
                </View>}
              </View><Text style={s.itemValue}>{money(item.amount_cents)}</Text>
            </View>;
          }) : <Text style={s.small}>Nenhuma despesa nesta seleção.</Text>}</Card>
          {!detail && financed.length > 0 && <>
            <View style={s.section}><Text style={s.sectionTitle}>Faturas parceladas</Text><Text style={s.small}>{financed.length} {financed.length === 1 ? 'parcela' : 'parcelas'}</Text></View>
            <Card>{financed.map(item => <View key={item.id} style={s.transaction}>
              <View style={[s.transactionDot, { backgroundColor: '#6C7296' }]} />
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={s.itemTitle}>{item.card_name} · {item.sequence}/{item.total_count}</Text>
                <Text style={s.small}>Principal {money(item.principal_cents)} · encargos {money(item.fee_cents)}</Text>
                <Text style={s.small}>Compromisso da fatura {item.invoice_month.slice(0, 7).split('-').reverse().join('/')}; não é nova compra.</Text>
              </View><Text style={s.itemValue}>{money(item.amount_cents)}</Text>
            </View>)}</Card>
          </>}
        </> : tab === 'Contas' ? <AccountsPanel workspace={workspace} token={token}
          startCreateRequest={guideAction?.kind === 'account' ? guideAction.id : undefined}
          onCreated={() => createdGuideItem('account')} /> : tab === 'Cartões' ? <>
          <CardPanel workspace={workspace} token={token} refresh={() => setRefresh(value => value + 1)}
            startCreateRequest={guideAction?.kind === 'card' ? guideAction.id : undefined}
            onCreated={() => createdGuideItem('card')} />
        </> : <PlanningPanel workspace={workspace} token={token} period={period} refresh={refresh}
          onChanged={() => setRefresh(value => value + 1)}
          startCreate={guideAction?.kind === 'expense' ? 'expense' : guideAction?.kind === 'card-rule' ? 'card' : undefined}
          startCreateRequest={guideAction?.id}
          onCreated={kind => createdGuideItem(kind === 'card' ? 'card-rule' : 'expense')} />}
        </>}
      </ScrollView>
      {!guideActive && <Pressable accessibilityRole="button" accessibilityLabel="Adicionar despesa" onPress={() => { void openNewExpense(); }} style={({ pressed }) => [s.fab, pressed && { opacity: 0.8 }]}><Text style={s.fabText}>+</Text></Pressable>}
      <View style={s.nav}>{(['Resumo', 'Contas', 'Cartões', 'Planejamento'] as Tab[]).map((item, index) => <Pressable key={item} accessibilityRole="tab" accessibilityState={{ selected: tab === item }} onPress={() => { setTab(item); setDetail(null); if (item === 'Resumo') setRefresh(value => value + 1); }} style={s.navItem}><View style={[s.navIcon, tab === item && s.navActive]}><Text style={[s.navSymbol, tab === item && { color: palette.green }]}>{['▥', '▤', '▱', '◷'][index]}</Text></View><Text style={[s.navLabel, tab === item && { color: palette.green, fontWeight: '700' }]}>{item}</Text></Pressable>)}</View>
    </View>
    <Modal visible={menuOpen} transparent animationType="fade" onRequestClose={() => setMenuOpen(false)}>
      <View style={s.menuOverlay}>
        <Pressable accessibilityRole="button" accessibilityLabel="Fechar menu" style={StyleSheet.absoluteFill} onPress={() => setMenuOpen(false)} />
        <SafeAreaView style={s.menuPanel}>
          <Text style={s.menuTitle}>Meu Controle</Text>
          <Text style={s.small}>{workspace.name}</Text>
          <Button label="Participantes" secondary onPress={() => { setMenuOpen(false); onOpenMembers(); }} />
          <Button label="Relatório do mês" secondary onPress={() => { setMenuOpen(false); setReportOpen(true); }} />
          <Button label="Gerenciar categorias" secondary onPress={() => { setMenuOpen(false); setManageCategories(true); }} />
          <View style={{ flex: 1 }} />
          <Button label="Sair da conta" secondary onPress={() => { setMenuOpen(false); onLogout(); }} />
        </SafeAreaView>
      </View>
    </Modal>
    <Modal visible={reportOpen} animationType="slide" onRequestClose={() => setReportOpen(false)}>
      <SafeAreaView style={s.safe}><View style={s.formShell}><ScrollView contentContainerStyle={s.content}>
        <Text style={s.pageTitle}>Relatório do mês</Text>
        <Text style={s.description}>{monthTitle}</Text>
        <MonthlyReport workspace={workspace} token={token} period={period} />
        <Button label="Fechar" secondary onPress={() => setReportOpen(false)} />
      </ScrollView></View><ToastViewport bottom={24} /></SafeAreaView>
    </Modal>
    {form && <Modal visible animationType="slide" onRequestClose={() => setForm(false)}><SafeAreaView style={s.safe}><View style={s.formShell}><ExpenseForm key={editing?.id || 'new'} initial={editing} categories={categories} accounts={accounts} cards={cards} onCreditSave={saveCredit} onCategory={addCategory} onSubcategory={addSubcategory} onSave={saveExpense} onCancel={() => { setForm(false); setEditing(undefined); }} /></View><ToastViewport bottom={24} /></SafeAreaView></Modal>}
    {manageCategories && <Modal visible animationType="slide" onRequestClose={() => setManageCategories(false)}><SafeAreaView style={s.safe}><View style={s.formShell}><ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <Text style={s.pageTitle}>Categorias e subcategorias</Text>
      <Text style={s.description}>As opções pertencem a este espaço e ficam disponíveis para todos os participantes. Desativar preserva os lançamentos antigos.</Text>
      <Button label="Voltar ao resumo" secondary onPress={() => setManageCategories(false)} />
      <CategoryCreator kind="categoria" existing={categories.map(item => item.name)} onCreate={async name => { await addCategory(name); }} />
      {categories.filter(item => item.active).map(item => <Card key={item.id}>
        <CategoryActionRow label={item.name} action="Desativar" onAction={() => confirmAction(`Desativar ${item.name}?`, () => deactivate(`/categories/${item.id}`))} />
        {item.subcategories.filter(sub => sub.active).map(sub =>
          <CategoryActionRow key={sub.id} label={sub.name} action="Desativar" nested
            onAction={() => confirmAction(`Desativar ${sub.name}?`, () => deactivate(`/categories/${item.id}/subcategories/${sub.id}`))} />)}
        {item.subcategories.filter(sub => !sub.active).map(sub =>
          <CategoryActionRow key={sub.id} label={sub.name} action="Reativar" nested inactive
            onAction={() => { void restoreSubcategory(item.id, sub).catch(e => setError(e instanceof Error ? e.message : 'Não foi possível reativar.')); }} />)}
        <CategoryCreator kind="subcategoria" existing={item.subcategories.map(sub => sub.name)} onCreate={async name => { await addSubcategory(item.id, name); }} />
      </Card>)}
      {categories.filter(item => !item.active).map(item =>
        <Card key={item.id}><CategoryActionRow label={item.name} action="Reativar" inactive
          onAction={() => { void restoreCategory(item).catch(e => setError(e instanceof Error ? e.message : 'Não foi possível reativar.')); }} /></Card>)}
    </ScrollView></View><ToastViewport bottom={24} /></SafeAreaView></Modal>}
    <IncomeReminder workspace={workspace} token={token} refresh={refresh} onChanged={() => setRefresh(value => value + 1)} />
  </SafeAreaView>;
}

function CategoryActionRow({ label, action, onAction, nested = false, inactive = false }: {
  label: string; action: 'Desativar' | 'Reativar'; onAction: () => void;
  nested?: boolean; inactive?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return <View style={{ gap: 8 }}>
    <View style={{ flexDirection: 'row', alignItems: 'center', paddingLeft: nested ? 12 : 0, minHeight: 38 }}>
      <Text style={{ flex: 1, color: inactive ? palette.muted : palette.ink, fontWeight: nested ? '400' : '700' }}>
        {label}{inactive ? ' · inativa' : ''}
      </Text>
      <Pressable accessibilityRole="button" accessibilityLabel={`Opções de ${label}`}
        onPress={() => setOpen(value => !value)} style={{ minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: palette.green, fontSize: 24, lineHeight: 28 }}>⋯</Text>
      </Pressable>
    </View>
    {open && <View style={{ gap: 8, paddingLeft: nested ? 12 : 0 }}>
      <Button label={action} secondary onPress={() => { setOpen(false); onAction(); }} />
      <Button label="Cancelar" secondary onPress={() => setOpen(false)} />
    </View>}
  </View>;
}

function Bar({ label, value, total, color, onPress }: { label: string; value: number; total: number; color: string; onPress?: () => void }) {
  const s = makeStyles();
  const percentage = `${(total ? value / total * 100 : 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
  const content = <><View style={s.barHeading}><View style={{ flex: 1, flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}><Text style={s.itemTitle}>{label}</Text><Text style={s.barPercent}>{percentage}</Text></View><Text style={s.itemValue}>{money(value)}{onPress ? '  ›' : ''}</Text></View><View style={s.track}><View style={{ width: `${total ? value / total * 100 : 0}%`, backgroundColor: color, height: 9, borderRadius: 5 }} /></View></>;
  return onPress ? <Pressable accessibilityRole="button" accessibilityLabel={`${label}, ${percentage}, ${money(value)}, ver subcategorias`} onPress={onPress} style={s.bar}>{content}</Pressable> : <View style={s.bar}>{content}</View>;
}

const makeStyles = () => StyleSheet.create({
  safe: { flex: 1, backgroundColor: palette.bg }, shell: { flex: 1, width: '100%', maxWidth: 560, alignSelf: 'center' }, formShell: { flex: 1, width: '100%', maxWidth: 560, alignSelf: 'center' },
  header: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10 },
  menuButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: palette.soft }, menuIcon: { fontSize: 25, color: palette.ink, lineHeight: 29 },
  menuOverlay: { flex: 1, backgroundColor: '#0008', flexDirection: 'row' }, menuPanel: { width: '82%', maxWidth: 360, height: '100%', backgroundColor: palette.bg, padding: 20, gap: 14 }, menuTitle: { fontSize: 24, fontWeight: '700', color: palette.ink },
  logo: { width: 48, height: 48, borderRadius: 13 }, themeToggle: { minHeight: 44, paddingHorizontal: 10, borderRadius: 12, backgroundColor: palette.soft, justifyContent: 'center' }, themeToggleText: { color: palette.ink, fontSize: 12, fontWeight: '700' },
  brand: { fontSize: 23, fontWeight: '800', letterSpacing: -1, color: palette.ink }, small: { fontSize: 12, color: palette.muted, lineHeight: 18 },
  content: { padding: 24, gap: 18, paddingBottom: 105 }, month: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, monthText: { fontWeight: '600', fontSize: 16, color: palette.ink },
  arrow: { width: 44, height: 44, borderWidth: 1, borderColor: palette.line, borderRadius: 14, justifyContent: 'center', alignItems: 'center', backgroundColor: palette.white }, arrowText: { fontSize: 26, color: palette.green },
  hero: { borderRadius: 24, backgroundColor: '#285B49', padding: 24, gap: 10 }, heroLabel: { fontSize: 11, fontWeight: '700', letterSpacing: 1.8, color: '#D5E2C4' }, heroValue: { fontSize: 38, fontWeight: '700', color: 'white', letterSpacing: -1 }, heroDivider: { height: 1, backgroundColor: '#4C7766', marginVertical: 4 }, heroCaption: { fontSize: 13, lineHeight: 20, color: '#E6EEE1' }, heroFoot: { color: '#DAE6D0', fontSize: 10, lineHeight: 16 },
  section: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }, sectionTitle: { color: palette.ink, fontSize: 17, fontWeight: '700' },
  bar: { paddingVertical: 10, gap: 10, minHeight: 58 }, barHeading: { flexDirection: 'row', justifyContent: 'space-between', gap: 10 }, track: { height: 9, borderRadius: 5, backgroundColor: palette.track, overflow: 'hidden' }, itemTitle: { color: palette.ink, fontWeight: '600', fontSize: 14 }, itemValue: { color: palette.ink, fontWeight: '600', fontSize: 13 },
  barPercent: { color: palette.muted, fontWeight: '700', fontSize: 13 },
  transaction: { flexDirection: 'row', alignItems: 'center', gap: 10, borderBottomWidth: 1, borderBottomColor: palette.line, paddingVertical: 10 }, transactionDot: { width: 8, height: 8, borderRadius: 4 },
  footerNote: { fontSize: 12, color: palette.muted, textAlign: 'center', lineHeight: 19 }, fab: { position: 'absolute', right: 24, bottom: 100, width: 58, height: 58, borderRadius: 19, backgroundColor: palette.green, alignItems: 'center', justifyContent: 'center', elevation: 5, boxShadow: '0 4px 12px #20362f25' }, fabText: { fontSize: 34, lineHeight: 40, color: palette.bg },
  nav: { flexDirection: 'row', borderTopWidth: 1, borderColor: palette.line, backgroundColor: palette.bg, paddingVertical: 8 }, navItem: { flex: 1, alignItems: 'center', gap: 4, minHeight: 62 }, navIcon: { width: 58, height: 34, alignItems: 'center', justifyContent: 'center', borderRadius: 14 }, navActive: { backgroundColor: palette.soft }, navSymbol: { fontSize: 23, color: palette.muted }, navLabel: { fontSize: 12, color: palette.muted },
  pageTitle: { fontSize: 28, color: palette.ink, fontWeight: '700' }, description: { fontSize: 14, lineHeight: 23, color: palette.muted }, bankCard: { padding: 24, gap: 24, backgroundColor: palette.ink, borderRadius: 24 }, bankName: { fontSize: 24, color: 'white', fontWeight: '600' }, bankDates: { flexDirection: 'row', justifyContent: 'space-between' }, bankDate: { color: 'white', fontWeight: '600', marginTop: 5 }, empty: { paddingVertical: 18, gap: 12 },
});
