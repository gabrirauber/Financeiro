import React, { useEffect, useRef, useState } from 'react';
import { AppState, Image, Linking, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ApiError, request, User, Workspace } from './api';
import { clearSession, readSession, saveSession } from './session';
import { MembersPanel } from './MembersPanel';
import { Recovery } from './Recovery';
import { Button, Card, palette, ThemeMode } from './ui';
import { useToastSetter } from './Toast';
import { saveOnboardingStep } from './onboardingProgress';

const input = () => ({ backgroundColor: palette.white, borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink });
export function AccessGate({ children, theme, onToggleTheme }: { children: (workspace: Workspace, token: string, userId: string, accessAdmin: boolean, demo: boolean, openMembers: () => void, logout: () => void) => React.ReactNode; theme: ThemeMode; onToggleTheme: () => void }) {
  const [token, setToken] = useState<string>();
  const tokenRef = useRef<string | undefined>(undefined);
  const wasBackgrounded = useRef(false);
  function activate(value: string) { wasBackgrounded.current = false; tokenRef.current = value; setToken(value); }
  const [user, setUser] = useState<User>();
  const [selected, setSelected] = useState<Workspace>();
  const [register, setRegister] = useState(false);
  const [pendingMessage, setPendingMessage] = useState(false);
  const [managing, setManaging] = useState(false);
  const [recover, setRecover] = useState(false);
  const [resetToken, setResetToken] = useState<string>();
  const [code, setCode] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(true);
  const setError = useToastSetter('error');

  async function load(value: string, newRegistration = false) {
    const [profile, workspaces] = await Promise.all([
      request<User>('/auth/me', value), request<Workspace[]>('/workspaces', value),
    ]);
    if (tokenRef.current !== value) return;
    if (profile.demo) await clearSession();
    if (newRegistration) await saveOnboardingStep(profile.id, 0);
    setUser(profile);
    setSelected(workspaces[0]);
    if (workspaces.length === 0) setManaging(false);
  }
  async function resetSession() {
    tokenRef.current = undefined;
    setRegister(false); setPassword('');
    await clearSession(); setToken(undefined); setUser(undefined); setSelected(undefined); setManaging(false);
  }
  async function run(action: () => Promise<void>) {
    setBusy(true); setError('');
    try { await action(); }
    catch (e) {
      if (e instanceof ApiError && e.status === 401 && token) await resetSession();
      setError(e instanceof Error ? e.message : 'Não foi possível concluir.');
    } finally { setBusy(false); }
  }
  useEffect(() => {
    void run(async () => {
      const saved = await readSession();
      if (saved) {
        activate(saved);
        try { await load(saved); }
        catch (e) { if (e instanceof ApiError && e.status === 401) await resetSession(); throw e; }
      }
    });
  }, []);
  useEffect(() => {
    if (!token || !user) return;
    const refresh = () => { void load(token).catch(async e => {
      if (tokenRef.current !== token) return;
      setSelected(undefined);
      if (e instanceof ApiError && e.status === 401) await resetSession();
      setError(e instanceof Error ? e.message : 'Conexão indisponível.');
    }); };
    const timer = setInterval(refresh, 30000);
    const subscription = AppState.addEventListener('change', state => {
      if (state === 'background') { wasBackgrounded.current = true; return; }
      if (state !== 'active') return;
      if (user.demo && wasBackgrounded.current) {
        wasBackgrounded.current = false;
        void request('/auth/logout', token, 'POST').catch(() => {});
        void resetSession();
      } else refresh();
    });
    return () => { clearInterval(timer); subscription.remove(); };
  }, [token, user?.id]);

  useEffect(() => {
    const handle = (url: string | null) => {
      const match = url?.match(/[#?]reset=([A-Za-z0-9_-]{32,128})/);
      if (match) {
        setResetToken(match[1]); setRecover(true);
        if (Platform.OS === 'web') window.history.replaceState(null, '', window.location.pathname);
      }
    };
    const handleWeb = () => handle(window.location.href);
    if (Platform.OS === 'web') { handleWeb(); window.addEventListener('hashchange', handleWeb); }
    else void Linking.getInitialURL().then(handle);
    const event = Linking.addEventListener('url', ({url}) => handle(url));
    return () => { event.remove(); if (Platform.OS === 'web') window.removeEventListener('hashchange', handleWeb); };
  }, []);
  if (recover) return <SafeAreaView style={{flex:1,backgroundColor:palette.bg}}><Recovery token={resetToken} onDone={() => { void resetSession(); setRecover(false); setResetToken(undefined); }} /></SafeAreaView>;

  async function authenticate() {
    await run(async () => {
      const result = await request<{ token?: string; status?: 'pending'; demo?: boolean }>(register ? '/auth/register' : '/auth/login', undefined, 'POST', {
        email: email.trim(), password,
        ...(register ? (code.trim() ? {invite_code: code.trim()} : {workspace_name: 'Minhas finanças'}) : {}),
      });
      if (result.status === 'pending') {
        setPendingMessage(true); setRegister(false); setPassword(''); setCode('');
        return;
      }
      if (!result.token) throw new Error('Não foi possível iniciar a sessão. Tente novamente.');
      setPendingMessage(false);
      if (!result.demo) await saveSession(result.token);
      activate(result.token); setPassword('');
      setCode('');
      await load(result.token, register);
    });
  }
  async function logout() {
    await run(async () => {
      // Só confirmar saída completa após revogar a sessão no servidor.
      await request('/auth/logout', token, 'POST'); await resetSession();
    });
  }

  if (selected && user && token) return <View style={{ flex: 1, backgroundColor: palette.bg }}>
    {children(selected, token, user.id, user.access_admin, user.demo, () => setManaging(true), () => { void logout(); })}
    <Modal visible={managing} animationType="slide" onRequestClose={() => setManaging(false)}>
      <SafeAreaView style={{ flex: 1, backgroundColor: palette.bg }}>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:20, maxWidth:560, width:'100%', alignSelf:'center', gap:16}}>
          <MembersPanel workspace={selected} token={token} accessAdmin={user.access_admin} onClose={() => setManaging(false)} onChanged={() => load(token)} />
        </ScrollView>
      </SafeAreaView>
    </Modal>
  </View>;

  return <SafeAreaView style={{ flex: 1, backgroundColor: palette.bg }}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 24, gap: 16, width: '100%', maxWidth: 560, alignSelf: 'center' }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <Image source={require('../assets/rautto-logo.png')} accessibilityLabel="Logo Rautto" resizeMode="contain" style={{ width: 62, height: 58, borderRadius: 12, backgroundColor: '#FFFFFF' }} />
        <Text style={{ flex: 1, fontSize: 26, fontWeight: '800', color: palette.ink }}>Rautto</Text>
        <Pressable accessibilityRole="switch" aria-checked={theme === 'dark'} accessibilityLabel="Modo escuro" onPress={onToggleTheme}
          style={{ minHeight: 44, paddingHorizontal: 10, borderRadius: 12, backgroundColor: palette.soft, justifyContent: 'center' }}>
          <Text style={{ color: palette.ink, fontSize: 12, fontWeight: '700' }}>{theme === 'dark' ? '☀ Claro' : '☾ Escuro'}</Text>
        </Pressable>
      </View>
      <Text style={{ color: palette.muted }}>Organize suas contas e acompanhe seu mês.</Text>
      {pendingMessage && <Card><Text style={{ color: palette.ink, fontWeight: '700' }}>Cadastro enviado para aprovação</Text><Text style={{ color: palette.muted }}>Você poderá entrar depois que o administrador liberar seu acesso. Volte aqui e use Entrar com seu e-mail e senha.</Text></Card>}
      {busy ? <Text accessibilityLiveRegion="polite">Aguarde…</Text> : null}
      {!user ? <Card>
        <Text style={{ fontSize: 22, color: palette.ink }}>{register ? 'Crie seu acesso' : 'Boas-vindas'}</Text>
        <TextInput accessibilityLabel="E-mail" placeholder="E-mail" autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} style={input()} editable={!busy} />
        <TextInput accessibilityLabel="Senha" placeholder={register ? 'Senha (mínimo 10 caracteres)' : 'Senha'} secureTextEntry value={password} onChangeText={setPassword} style={input()} editable={!busy} maxLength={128} />
        {register && <>
          <Text style={{color: palette.muted}}>Recebeu um convite? Informe o código para entrar no espaço compartilhado. Sem código, criaremos seu espaço automaticamente.</Text>
          <TextInput accessibilityLabel="Código de convite (opcional)" placeholder="Código de convite (opcional)" autoCapitalize="characters" value={code} onChangeText={setCode} style={input()} editable={!busy} maxLength={64} />
        </>}
        {!busy && <>
          <Button label={register ? 'Cadastrar' : 'Entrar'} onPress={() => void authenticate()} />
          <Button label={register ? 'Já tenho cadastro' : 'Criar cadastro'} secondary onPress={() => { setRegister(!register); setError(''); }} />
          <Button label="Esqueci minha senha" secondary onPress={() => setRecover(true)} />{token && <Button label="Tentar restaurar sessão" secondary onPress={() => void run(() => load(token))} />}
        </>}
      </Card> : <>
        <Text style={{ color: palette.muted }}>{user.email}</Text>
        <Text style={{ fontSize: 22, color: palette.ink }}>Comece seu espaço financeiro</Text>
        <Text style={{color:palette.muted}}>Entre com um convite ou crie seu próprio espaço.</Text>
        <Card><Text style={{ fontWeight: '700', color: palette.ink }}>Criar espaço</Text><TextInput accessibilityLabel="Nome do espaço" placeholder="Ex.: Finanças da casa" style={input()} value={name} onChangeText={setName} maxLength={80} />
        {!busy && <Button label="Criar espaço financeiro" onPress={() => void run(async () => {
          await request('/workspaces', token, 'POST', { name: name.trim() || 'Minhas finanças' }); setName(''); await load(token!);
        })} />}</Card>
        <Card><Text style={{fontWeight:'700',color:palette.ink}}>Entrar por código</Text><TextInput accessibilityLabel="Código de convite" placeholder="Código recebido" autoCapitalize="characters" value={code} onChangeText={setCode} style={input()} maxLength={64} />{!busy && <Button label="Entrar no espaço compartilhado" onPress={() => void run(async () => {
          await request('/invites/accept', token, 'POST', {code}); setCode(''); await load(token!);
        })} />}</Card>
        {!busy && <Button label="Sair da conta" secondary onPress={() => void logout()} />}
      </>}
    </ScrollView>
  </SafeAreaView>;
}
