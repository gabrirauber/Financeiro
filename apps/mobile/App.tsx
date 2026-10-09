import React, { useEffect, useState } from 'react';
import { BackHandler, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { ExpenseForm } from './src/ExpenseForm';
import { cards, categories as initialCategories, Expense, initialExpenses, money, monthKey } from './src/prototype';
import { CategoryCreator } from './src/CategoryCreator';
import { ApiStatus } from './src/ApiStatus';
import { AccessGate } from './src/AccessGate';
import { AccountsPanel } from './src/AccountsPanel';
import { Workspace } from './src/api';
import { Button, Card, palette } from './src/ui';

type Tab = 'Resumo' | 'Contas' | 'Cartões';
export default function App() { return <SafeAreaProvider><AccessGate>{(workspace, token) => <Prototype key={workspace.id} workspace={workspace} token={token} />}</AccessGate></SafeAreaProvider>; }

function Prototype({ workspace, token }: { workspace: Workspace; token: string }) {
  const [categories, setCategories] = useState(() => initialCategories.map(item => ({ ...item, subcategories: [...item.subcategories] })));
  const [manageCategories, setManageCategories] = useState(false);
  function addCategory(name: string) {
    const id = `category-${Date.now()}-${Math.random()}`;
    setCategories(items => [...items, { id, name, color: '#647CAB', subcategories: [] }]);
    return id;
  }
  function addSubcategory(id: string, name: string) {
    setCategories(items => items.map(item => item.id === id ? { ...item, subcategories: [...item.subcategories, name] } : item));
  }
  const [tab, setTab] = useState<Tab>('Resumo');
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [expenses, setExpenses] = useState<Expense[]>(initialExpenses);
  const [detail, setDetail] = useState<string | null>(null);
  const [form, setForm] = useState(false);
  const [notice, setNotice] = useState('');
  const category = categories.find(item => item.id === detail);
  const filtered = expenses.filter(item => item.date.slice(3) === monthKey(month));
  const total = filtered.reduce((sum, item) => sum + item.cents, 0);
  const monthTitle = month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  useEffect(() => {
    const listener = BackHandler.addEventListener('hardwareBackPress', () => {
      if (detail) { setDetail(null); return true; }
      if (tab !== 'Resumo') { setTab('Resumo'); return true; }
      return false;
    });
    return () => listener.remove();
  }, [detail, tab]);
  function changeMonth(delta: number) { setMonth(value => new Date(value.getFullYear(), value.getMonth() + delta, 1)); setNotice(''); }
  function save(expense: Expense) {
    setExpenses(value => [expense, ...value]);
    const [, m, y] = expense.date.split('/').map(Number);
    setMonth(new Date(y, m - 1, 1)); setDetail(null); setTab('Resumo'); setForm(false);
    setNotice('Despesa adicionada à simulação. Ao reiniciar, os exemplos são restaurados.');
  }
  return <SafeAreaView style={s.safe}>
    <StatusBar style="dark" />
    <View style={s.shell}>
      <View style={s.header}><View><Text style={s.brand}>financeiro<Text style={{ color: '#A9B883' }}>.</Text></Text><Text style={s.small}>Seu dinheiro, com clareza.</Text></View><View style={s.avatar}><Text style={s.avatarText}>F</Text></View></View>
      <View style={s.demo}><View style={s.dot} /><Text style={s.demoText}>E04 · CONTAS REAIS, GASTOS DE EXEMPLO</Text></View>
      <ScrollView contentContainerStyle={s.content}>
        {tab === 'Resumo' ? <>
          <ApiStatus />
          <View style={s.month}><Pressable accessibilityRole="button" accessibilityLabel="Mês anterior" onPress={() => changeMonth(-1)} style={s.arrow}><Text style={s.arrowText}>‹</Text></Pressable><Text style={s.monthText}>{monthTitle}</Text><Pressable accessibilityRole="button" accessibilityLabel="Próximo mês" onPress={() => changeMonth(1)} style={s.arrow}><Text style={s.arrowText}>›</Text></Pressable></View>
          {!!notice && <Pressable accessibilityRole="button" accessibilityLabel="Dispensar confirmação" onPress={() => setNotice('')} style={s.notice}><Text accessibilityLiveRegion="polite" style={s.small}>{notice}</Text></Pressable>}
          <View style={s.hero}><Text style={s.heroLabel}>GASTOS DO MÊS</Text><Text style={s.heroValue}>{money(total)}</Text><View style={s.heroDivider} /><Text style={s.heroCaption}>Um olhar simples para onde seu dinheiro vai.</Text><Text style={s.heroFoot}>Prévia visual • sem cálculo de faturas ou projeções</Text></View>
          <View style={s.section}><Text style={s.sectionTitle}>{category ? category.name : 'Por categoria'}</Text><Text style={s.small}>{category ? 'Subcategorias' : 'Toque para explorar'}</Text></View>
          <Button label="Gerenciar categorias e subcategorias" secondary onPress={() => setManageCategories(true)} />
          <Card>
            {category && <Button label="← Todas as categorias" secondary onPress={() => setDetail(null)} />}
            {total === 0 ? <View style={s.empty}><Text style={s.sectionTitle}>Um mês em branco</Text><Text style={s.small}>Use o + para simular sua primeira despesa.</Text></View> : category ? category.subcategories.map(sub => {
              const value = filtered.filter(item => item.category === category.id && item.subcategory === sub).reduce((sum, item) => sum + item.cents, 0);
              return <Bar key={sub} label={sub} value={value} total={total} color={category.color} />;
            }) : categories.map(item => {
              const value = filtered.filter(expense => expense.category === item.id).reduce((sum, expense) => sum + expense.cents, 0);
              return <Bar key={item.id} label={item.name} value={value} total={total} color={item.color} onPress={() => setDetail(item.id)} />;
            })}
          </Card>
          <View style={s.section}><Text style={s.sectionTitle}>Movimentações</Text><Text style={s.small}>{filtered.filter(item => !detail || item.category === detail).length} itens</Text></View>
          <Card>{filtered.filter(item => !detail || item.category === detail).length ? filtered.filter(item => !detail || item.category === detail).map(item => <View key={item.id} style={s.transaction}>
            <View style={[s.transactionDot, { backgroundColor: categories.find(cat => cat.id === item.category)?.color }]} />
            <View style={{ flex: 1, gap: 4 }}><Text style={s.itemTitle}>{item.note || item.subcategory}</Text><Text style={s.small}>{item.subcategory} · {item.date.slice(0, 5)}</Text><Text style={s.small}>{item.payment} · {item.source}</Text></View><Text style={s.itemValue}>{money(item.cents)}</Text>
          </View>) : <Text style={s.small}>Nenhuma despesa nesta seleção.</Text>}</Card>
          <Text style={s.footerNote}>Tudo aqui é uma simulação em memória. Seus dados reais ainda não são solicitados.</Text>
        </> : tab === 'Contas' ? <>
          <AccountsPanel workspace={workspace} token={token} />
        </> : <>
          <Text style={s.pageTitle}>Seus cartões</Text><Text style={s.description}>Compras organizadas, mês a mês.</Text>
          {cards.map((card, index) => <View key={card} style={[s.bankCard, index === 1 && { backgroundColor: '#45566E' }]}><Text style={s.heroLabel}>CRÉDITO · EXEMPLO</Text><Text style={s.bankName}>{card}</Text><View style={s.bankDates}><View><Text style={s.heroCaption}>Fechamento</Text><Text style={s.bankDate}>Dia {index ? 20 : 10}</Text></View><View><Text style={s.heroCaption}>Vencimento</Text><Text style={s.bankDate}>Dia {index ? 28 : 18}</Text></View></View></View>)}
          <Card><Text style={s.sectionTitle}>Uma prévia da organização</Text><Text style={s.description}>Faturas, parcelamentos e pagamento serão implementados na E06. Esta tela apresenta apenas cartões fictícios.</Text></Card>
        </>}
      </ScrollView>
      <Pressable accessibilityRole="button" accessibilityLabel="Adicionar despesa" onPress={() => setForm(true)} style={({ pressed }) => [s.fab, pressed && { opacity: 0.8 }]}><Text style={s.fabText}>+</Text></Pressable>
      <View style={s.nav}>{(['Resumo', 'Contas', 'Cartões'] as Tab[]).map((item, index) => <Pressable key={item} accessibilityRole="tab" accessibilityState={{ selected: tab === item }} onPress={() => { setTab(item); setDetail(null); }} style={s.navItem}><View style={[s.navIcon, tab === item && s.navActive]}><Text style={[s.navSymbol, tab === item && { color: palette.green }]}>{['▥', '▤', '▱'][index]}</Text></View><Text style={[s.navLabel, tab === item && { color: palette.green, fontWeight: '700' }]}>{item}</Text></Pressable>)}</View>
    </View>
    {form && <Modal visible animationType="slide" onRequestClose={() => setForm(false)}><SafeAreaView style={s.safe}><View style={s.formShell}><ExpenseForm categories={categories} onCategory={addCategory} onSubcategory={addSubcategory} onSave={save} onCancel={() => setForm(false)} /></View></SafeAreaView></Modal>}
    {manageCategories && <Modal visible animationType="slide" onRequestClose={() => setManageCategories(false)}><SafeAreaView style={s.safe}><View style={s.formShell}><ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <Text style={s.pageTitle}>Categorias e subcategorias</Text>
      <Text style={s.description}>Comece com esta base e adicione suas próprias opções. Na prévia, os cadastros duram apenas nesta sessão.</Text>
      <Button label="Voltar ao resumo" secondary onPress={() => setManageCategories(false)} />
      <CategoryCreator kind="categoria" existing={categories.map(item => item.name)} onCreate={addCategory} />
      {categories.map(item => <Card key={item.id}><Text style={s.sectionTitle}>{item.name}</Text><Text style={s.description}>{item.subcategories.length ? item.subcategories.join(' · ') : 'Nenhuma subcategoria cadastrada.'}</Text><CategoryCreator kind="subcategoria" existing={item.subcategories} onCreate={name => addSubcategory(item.id, name)} /></Card>)}
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
  content: { padding: 24, gap: 18, paddingBottom: 105 }, month: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, monthText: { textTransform: 'capitalize', fontWeight: '600', fontSize: 16, color: palette.ink },
  arrow: { width: 44, height: 44, borderWidth: 1, borderColor: palette.line, borderRadius: 14, justifyContent: 'center', alignItems: 'center', backgroundColor: 'white' }, arrowText: { fontSize: 26, color: palette.green },
  hero: { borderRadius: 24, backgroundColor: palette.green, padding: 24, gap: 10 }, heroLabel: { fontSize: 11, fontWeight: '700', letterSpacing: 1.8, color: '#D5E2C4' }, heroValue: { fontSize: 38, fontWeight: '700', color: 'white', letterSpacing: -1 }, heroDivider: { height: 1, backgroundColor: '#4C7766', marginVertical: 4 }, heroCaption: { fontSize: 13, lineHeight: 20, color: '#E6EEE1' }, heroFoot: { color: '#DAE6D0', fontSize: 10, lineHeight: 16 },
  section: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }, sectionTitle: { color: palette.ink, fontSize: 17, fontWeight: '700' },
  bar: { paddingVertical: 10, gap: 10, minHeight: 58 }, barHeading: { flexDirection: 'row', justifyContent: 'space-between', gap: 10 }, track: { height: 9, borderRadius: 5, backgroundColor: '#F0F1EB', overflow: 'hidden' }, itemTitle: { color: palette.ink, fontWeight: '600', fontSize: 14 }, itemValue: { color: palette.ink, fontWeight: '600', fontSize: 13 },
  transaction: { flexDirection: 'row', alignItems: 'center', gap: 10, borderBottomWidth: 1, borderBottomColor: '#F0F1EB', paddingVertical: 10 }, transactionDot: { width: 8, height: 8, borderRadius: 4 },
  footerNote: { fontSize: 12, color: palette.muted, textAlign: 'center', lineHeight: 19 }, fab: { position: 'absolute', right: 24, bottom: 100, width: 58, height: 58, borderRadius: 19, backgroundColor: palette.green, alignItems: 'center', justifyContent: 'center', elevation: 5, boxShadow: '0 4px 12px #20362f25' }, fabText: { fontSize: 34, lineHeight: 40, color: 'white' },
  nav: { flexDirection: 'row', borderTopWidth: 1, borderColor: palette.line, backgroundColor: palette.bg, paddingVertical: 8 }, navItem: { flex: 1, alignItems: 'center', gap: 4, minHeight: 62 }, navIcon: { width: 58, height: 34, alignItems: 'center', justifyContent: 'center', borderRadius: 14 }, navActive: { backgroundColor: '#E4EBDC' }, navSymbol: { fontSize: 23, color: palette.muted }, navLabel: { fontSize: 12, color: palette.muted },
  pageTitle: { fontSize: 28, color: palette.ink, fontWeight: '700' }, description: { fontSize: 14, lineHeight: 23, color: palette.muted }, bankCard: { padding: 24, gap: 24, backgroundColor: palette.ink, borderRadius: 24 }, bankName: { fontSize: 24, color: 'white', fontWeight: '600' }, bankDates: { flexDirection: 'row', justifyContent: 'space-between' }, bankDate: { color: 'white', fontWeight: '600', marginTop: 5 }, empty: { paddingVertical: 18, gap: 12 }, notice: { backgroundColor: '#E7EDDF', padding: 14, borderRadius: 14 },
});
