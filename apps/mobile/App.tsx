import React, { useEffect, useState } from 'react';
import { Alert, AppState, BackHandler, Modal, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { ExpenseForm } from './src/ExpenseForm';
import { cards, money } from './src/prototype';
import { CategoryCreator } from './src/CategoryCreator';
import { ApiStatus } from './src/ApiStatus';
import { AccessGate } from './src/AccessGate';
import { AccountsPanel } from './src/AccountsPanel';
import { request, Workspace } from './src/api';
import { Account, Category, Expense, ExpenseInput, Subcategory, dateToDisplay, monthIso, paymentLabel } from './src/finance';
import { Button, Card, palette } from './src/ui';

type Tab = 'Resumo' | 'Contas' | 'Cartões';
export default function App() {
  return <SafeAreaProvider><AccessGate>{(workspace, token) =>
    <Home key={workspace.id} workspace={workspace} token={token} />
  }</AccessGate></SafeAreaProvider>;
}

function Home({ workspace, token }: { workspace: Workspace; token: string }) {
  const root = `/workspaces/${workspace.id}`;
  const [categories, setCategories] = useState<Category[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [tab, setTab] = useState<Tab>('Resumo');
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [detail, setDetail] = useState<string | null>(null);
  const [form, setForm] = useState(false);
  const [editing, setEditing] = useState<Expense>();
  const [manageCategories, setManageCategories] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const period = monthIso(month);
  const category = categories.find(item => item.id === detail);
  const total = expenses.reduce((sum, item) => sum + item.amount_cents, 0);
  const monthName = month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  const monthTitle = monthName.charAt(0).toUpperCase() + monthName.slice(1);
  const currentMonth = monthIso(new Date());

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      request<Category[]>(`${root}/categories`, token),
      request<Account[]>(`${root}/accounts`, token),
      request<Expense[]>(`${root}/expenses?month=${period}`, token),
    ]).then(([cats, accs, rows]) => {
      if (!active) return;
      setCategories(cats); setAccounts(accs); setExpenses(rows); setError('');
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Não foi possível carregar o resumo.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [root, token, period, refresh]);

  useEffect(() => {
    const listener = BackHandler.addEventListener('hardwareBackPress', () => {
      if (detail) { setDetail(null); return true; }
      if (tab !== 'Resumo') { setTab('Resumo'); return true; }
      return false;
    });
    return () => listener.remove();
  }, [detail, tab]);
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
  async function removeExpense(expense: Expense) {
    await request(`${root}/expenses/${expense.id}`, token, 'DELETE');
    setRefresh(value => value + 1);
    setNotice('Despesa excluída. O valor voltou ao saldo da conta.');
  }
  const visible = expenses.filter(item => !detail || item.category_id === detail);
  return <SafeAreaView style={s.safe}>
    <StatusBar style="dark" />
    <View style={s.shell}>
      <View style={s.header}><View><Text style={s.brand}>financeiro<Text style={{ color: '#A9B883' }}>.</Text></Text><Text style={s.small}>Seu dinheiro, com clareza.</Text></View><View style={s.avatar}><Text style={s.avatarText}>F</Text></View></View>
      <View style={s.demo}><View style={s.dot} /><Text style={s.demoText}>E05 · DESPESAS E SALDOS REAIS</Text></View>
      <ScrollView contentContainerStyle={s.content}>
        {tab === 'Resumo' ? <>
          <ApiStatus />
          <View style={s.month}><Pressable accessibilityRole="button" accessibilityLabel="Mês anterior" onPress={() => { setMonth(value => new Date(value.getFullYear(), value.getMonth() - 1, 1)); setNotice(''); }} style={s.arrow}><Text style={s.arrowText}>‹</Text></Pressable><Text style={s.monthText}>{monthTitle}</Text><Pressable accessibilityRole="button" accessibilityLabel="Próximo mês" onPress={() => { setMonth(value => new Date(value.getFullYear(), value.getMonth() + 1, 1)); setNotice(''); }} style={s.arrow}><Text style={s.arrowText}>›</Text></Pressable></View>
          {!!notice && <Pressable accessibilityRole="button" accessibilityLabel="Dispensar confirmação" onPress={() => setNotice('')} style={s.notice}><Text accessibilityLiveRegion="polite" style={s.small}>{notice}</Text></Pressable>}
          {!!error && <Card><Text accessibilityRole="alert" style={{ color: '#AA422E' }}>{error}</Text><Button label="Tentar novamente" secondary onPress={() => setRefresh(value => value + 1)} /></Card>}
          {loading && <Text style={s.small}>Carregando gastos…</Text>}
          <View style={s.hero}><Text style={s.heroLabel}>GASTOS DO MÊS</Text><Text style={s.heroValue}>{money(total)}</Text><View style={s.heroDivider} /><Text style={s.heroCaption}>Despesas pagas com dinheiro, Pix ou débito.</Text><Text style={s.heroFoot}>Faturas e projeções entram nas próximas etapas.</Text></View>
          <View style={s.section}><Text style={s.sectionTitle}>{category ? category.name : 'Por categoria'}</Text><Text style={s.small}>{category ? 'Subcategorias' : 'Toque para explorar'}</Text></View>
          <Button label="Gerenciar categorias e subcategorias" secondary onPress={() => setManageCategories(true)} />
          <Card>
            {category && <Button label="← Todas as categorias" secondary onPress={() => setDetail(null)} />}
            {!total ? <View style={s.empty}><Text style={s.sectionTitle}>Um mês em branco</Text><Text style={s.small}>Use o + para lançar sua primeira despesa paga.</Text></View> :
              category ? category.subcategories.map(sub => {
                const value = visible.filter(item => item.subcategory_id === sub.id).reduce((sum, item) => sum + item.amount_cents, 0);
                const categoryTotal = visible.reduce((sum, item) => sum + item.amount_cents, 0);
                return <Bar key={sub.id} label={sub.name} value={value} total={categoryTotal} color={category.color} />;
              }) : categories.map(item => {
                const value = expenses.filter(row => row.category_id === item.id).reduce((sum, row) => sum + row.amount_cents, 0);
                return <Bar key={item.id} label={item.name} value={value} total={total} color={item.color} onPress={() => setDetail(item.id)} />;
              })}
          </Card>
          <View style={s.section}><Text style={s.sectionTitle}>Despesas pagas</Text><Text style={s.small}>{visible.length} {visible.length === 1 ? 'item' : 'itens'}</Text></View>
          <Card>{visible.length ? visible.map(item => {
            const cat = categories.find(x => x.id === item.category_id);
            const sub = cat?.subcategories.find(x => x.id === item.subcategory_id);
            const acc = accounts.find(x => x.id === item.account_id);
            return <View key={item.id} style={s.transaction}>
              <View style={[s.transactionDot, { backgroundColor: cat?.color || palette.green }]} />
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={s.itemTitle}>{item.note || sub?.name || 'Despesa'}</Text>
                <Text style={s.small}>{cat?.name || 'Categoria'} · {sub?.name || 'Subcategoria'} · {dateToDisplay(item.occurred_on)}</Text>
                <Text style={s.small}>{paymentLabel[item.payment_method]} · {acc?.name || 'Conta'}</Text>
                {item.occurred_on.slice(0, 7) === currentMonth && <View style={{ flexDirection: 'row', gap: 16 }}>
                  <Text accessibilityRole="button" onPress={() => { setEditing(item); setForm(true); }} style={{ color: palette.green }}>Editar</Text>
                  <Text accessibilityRole="button" onPress={() => confirmAction('Excluir despesa?', () => removeExpense(item))} style={{ color: '#AA422E' }}>Excluir</Text>
                </View>}
              </View><Text style={s.itemValue}>{money(item.amount_cents)}</Text>
            </View>;
          }) : <Text style={s.small}>Nenhuma despesa nesta seleção.</Text>}</Card>
        </> : tab === 'Contas' ? <AccountsPanel workspace={workspace} token={token} /> : <>
          <Text style={s.pageTitle}>Seus cartões</Text><Text style={s.description}>Compras organizadas, mês a mês.</Text>
          {cards.map((card, index) => <View key={card} style={[s.bankCard, index === 1 && { backgroundColor: '#45566E' }]}><Text style={s.heroLabel}>CRÉDITO · EXEMPLO</Text><Text style={s.bankName}>{card}</Text><View style={s.bankDates}><View><Text style={s.heroCaption}>Fechamento</Text><Text style={s.bankDate}>Dia {index ? 20 : 10}</Text></View><View><Text style={s.heroCaption}>Vencimento</Text><Text style={s.bankDate}>Dia {index ? 28 : 18}</Text></View></View></View>)}
          <Card><Text style={s.sectionTitle}>Próxima etapa</Text><Text style={s.description}>Cartões, faturas e parcelas entram na E06. Esta tela ainda apresenta exemplos.</Text></Card>
        </>}
      </ScrollView>
      <Pressable accessibilityRole="button" accessibilityLabel="Adicionar despesa" onPress={() => { void openNewExpense(); }} style={({ pressed }) => [s.fab, pressed && { opacity: 0.8 }]}><Text style={s.fabText}>+</Text></Pressable>
      <View style={s.nav}>{(['Resumo', 'Contas', 'Cartões'] as Tab[]).map((item, index) => <Pressable key={item} accessibilityRole="tab" accessibilityState={{ selected: tab === item }} onPress={() => { setTab(item); setDetail(null); if (item === 'Resumo') setRefresh(value => value + 1); }} style={s.navItem}><View style={[s.navIcon, tab === item && s.navActive]}><Text style={[s.navSymbol, tab === item && { color: palette.green }]}>{['▥', '▤', '▱'][index]}</Text></View><Text style={[s.navLabel, tab === item && { color: palette.green, fontWeight: '700' }]}>{item}</Text></Pressable>)}</View>
    </View>
    {form && <Modal visible animationType="slide" onRequestClose={() => setForm(false)}><SafeAreaView style={s.safe}><View style={s.formShell}><ExpenseForm key={editing?.id || 'new'} initial={editing} categories={categories} accounts={accounts} onCategory={addCategory} onSubcategory={addSubcategory} onSave={saveExpense} onCancel={() => { setForm(false); setEditing(undefined); }} /></View></SafeAreaView></Modal>}
    {manageCategories && <Modal visible animationType="slide" onRequestClose={() => setManageCategories(false)}><SafeAreaView style={s.safe}><View style={s.formShell}><ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <Text style={s.pageTitle}>Categorias e subcategorias</Text>
      <Text style={s.description}>As opções pertencem a este espaço e ficam disponíveis para todos os participantes. Desativar preserva os lançamentos antigos.</Text>
      {!!error && <Text accessibilityRole="alert" style={{ color: '#AA422E' }}>{error}</Text>}
      <Button label="Voltar ao resumo" secondary onPress={() => setManageCategories(false)} />
      <CategoryCreator kind="categoria" existing={categories.map(item => item.name)} onCreate={async name => { await addCategory(name); }} />
      {categories.filter(item => item.active).map(item => <Card key={item.id}><Text style={s.sectionTitle}>{item.name}</Text>
        <Text style={s.description}>{item.subcategories.filter(sub => sub.active).map(sub => sub.name).join(' · ') || 'Nenhuma subcategoria ativa.'}</Text>
        <CategoryCreator kind="subcategoria" existing={item.subcategories.map(sub => sub.name)} onCreate={async name => { await addSubcategory(item.id, name); }} />
        {item.subcategories.filter(sub => sub.active).map(sub => <Button key={sub.id} label={`Desativar ${sub.name}`} secondary onPress={() => confirmAction(`Desativar ${sub.name}?`, () => deactivate(`/categories/${item.id}/subcategories/${sub.id}`))} />)}
        {item.subcategories.filter(sub => !sub.active).map(sub => <Button key={sub.id} label={`Reativar ${sub.name}`} secondary onPress={() => { void restoreSubcategory(item.id, sub).catch(e => setError(e instanceof Error ? e.message : 'Não foi possível reativar.')); }} />)}
        <Button label={`Desativar categoria ${item.name}`} secondary onPress={() => confirmAction(`Desativar ${item.name}?`, () => deactivate(`/categories/${item.id}`))} />
      </Card>)}
      {categories.filter(item => !item.active).map(item => <Card key={item.id}><Text style={s.sectionTitle}>{item.name} · inativa</Text><Button label={`Reativar categoria ${item.name}`} secondary onPress={() => { void restoreCategory(item).catch(e => setError(e instanceof Error ? e.message : 'Não foi possível reativar.')); }} /></Card>)}
    </ScrollView></View></SafeAreaView></Modal>}
  </SafeAreaView>;
}

function Bar({ label, value, total, color, onPress }: { label: string; value: number; total: number; color: string; onPress?: () => void }) {
  const content = <><View style={s.barHeading}><Text style={s.itemTitle}>{label}</Text><Text style={s.itemValue}>{money(value)}{onPress ? '  ›' : ''}</Text></View><View style={s.track}><View style={{ width: `${total ? value / total * 100 : 0}%`, backgroundColor: color, height: 9, borderRadius: 5 }} /></View></>;
  return onPress ? <Pressable accessibilityRole="button" accessibilityLabel={`${label}, ${money(value)}, ver subcategorias`} onPress={onPress} style={s.bar}>{content}</Pressable> : <View style={s.bar}>{content}</View>;
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: palette.bg }, shell: { flex: 1, width: '100%', maxWidth: 560, alignSelf: 'center' }, formShell: { flex: 1, width: '100%', maxWidth: 560, alignSelf: 'center' },
  header: { paddingHorizontal: 24, paddingTop: 12, paddingBottom: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  brand: { fontSize: 28, fontWeight: '800', letterSpacing: -1, color: palette.ink }, small: { fontSize: 12, color: palette.muted, lineHeight: 18 },
  avatar: { width: 42, height: 42, borderRadius: 21, backgroundColor: '#E5EBDD', alignItems: 'center', justifyContent: 'center' }, avatarText: { fontWeight: '700', color: palette.green },
  demo: { backgroundColor: '#E9ECDD', paddingVertical: 9, paddingHorizontal: 24, flexDirection: 'row', alignItems: 'center', gap: 8 }, dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#637B47' }, demoText: { fontSize: 10, letterSpacing: 1.2, color: '#4E633D', fontWeight: '700' },
  content: { padding: 24, gap: 18, paddingBottom: 105 }, month: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, monthText: { fontWeight: '600', fontSize: 16, color: palette.ink },
  arrow: { width: 44, height: 44, borderWidth: 1, borderColor: palette.line, borderRadius: 14, justifyContent: 'center', alignItems: 'center', backgroundColor: 'white' }, arrowText: { fontSize: 26, color: palette.green },
  hero: { borderRadius: 24, backgroundColor: palette.green, padding: 24, gap: 10 }, heroLabel: { fontSize: 11, fontWeight: '700', letterSpacing: 1.8, color: '#D5E2C4' }, heroValue: { fontSize: 38, fontWeight: '700', color: 'white', letterSpacing: -1 }, heroDivider: { height: 1, backgroundColor: '#4C7766', marginVertical: 4 }, heroCaption: { fontSize: 13, lineHeight: 20, color: '#E6EEE1' }, heroFoot: { color: '#DAE6D0', fontSize: 10, lineHeight: 16 },
  section: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }, sectionTitle: { color: palette.ink, fontSize: 17, fontWeight: '700' },
  bar: { paddingVertical: 10, gap: 10, minHeight: 58 }, barHeading: { flexDirection: 'row', justifyContent: 'space-between', gap: 10 }, track: { height: 9, borderRadius: 5, backgroundColor: '#F0F1EB', overflow: 'hidden' }, itemTitle: { color: palette.ink, fontWeight: '600', fontSize: 14 }, itemValue: { color: palette.ink, fontWeight: '600', fontSize: 13 },
  transaction: { flexDirection: 'row', alignItems: 'center', gap: 10, borderBottomWidth: 1, borderBottomColor: '#F0F1EB', paddingVertical: 10 }, transactionDot: { width: 8, height: 8, borderRadius: 4 },
  footerNote: { fontSize: 12, color: palette.muted, textAlign: 'center', lineHeight: 19 }, fab: { position: 'absolute', right: 24, bottom: 100, width: 58, height: 58, borderRadius: 19, backgroundColor: palette.green, alignItems: 'center', justifyContent: 'center', elevation: 5, boxShadow: '0 4px 12px #20362f25' }, fabText: { fontSize: 34, lineHeight: 40, color: 'white' },
  nav: { flexDirection: 'row', borderTopWidth: 1, borderColor: palette.line, backgroundColor: palette.bg, paddingVertical: 8 }, navItem: { flex: 1, alignItems: 'center', gap: 4, minHeight: 62 }, navIcon: { width: 58, height: 34, alignItems: 'center', justifyContent: 'center', borderRadius: 14 }, navActive: { backgroundColor: '#E4EBDC' }, navSymbol: { fontSize: 23, color: palette.muted }, navLabel: { fontSize: 12, color: palette.muted },
  pageTitle: { fontSize: 28, color: palette.ink, fontWeight: '700' }, description: { fontSize: 14, lineHeight: 23, color: palette.muted }, bankCard: { padding: 24, gap: 24, backgroundColor: palette.ink, borderRadius: 24 }, bankName: { fontSize: 24, color: 'white', fontWeight: '600' }, bankDates: { flexDirection: 'row', justifyContent: 'space-between' }, bankDate: { color: 'white', fontWeight: '600', marginTop: 5 }, empty: { paddingVertical: 18, gap: 12 }, notice: { backgroundColor: '#E7EDDF', padding: 14, borderRadius: 14 },
});
