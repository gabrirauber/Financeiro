import React, { useEffect, useState } from 'react';
import { Modal, ScrollView, Text, TextInput, View } from 'react-native';
import { request, Workspace } from './api';
import { Account } from './finance';
import { localDate, money, parseCents } from './prototype';
import { Button, Card, Chip, palette } from './ui';
import { ToastViewport, useToastSetter } from './Toast';

type Reminder = { id: string; description: string; due_on: string; remaining_cents: number; received_cents: number };
const input = () => ({ backgroundColor: palette.white, borderWidth: 1, borderColor: palette.line, borderRadius: 12, padding: 14, fontSize: 16, color: palette.ink });

export function IncomeReminder({workspace, token, refresh, onChanged}: {workspace: Workspace; token: string; refresh: number; onChanged: () => void}) {
  const root = `/workspaces/${workspace.id}`;
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [receiving, setReceiving] = useState(false);
  const [accountId, setAccountId] = useState('');
  const [amount, setAmount] = useState('');
  const [complete, setComplete] = useState(true);
  const [busy, setBusy] = useState(false);
  const setError = useToastSetter('error');
  const current = reminders[0];
  async function load() {
    const [due, all] = await Promise.all([
      request<Reminder[]>(`${root}/income-reminders`, token),
      request<Account[]>(`${root}/accounts`, token),
    ]);
    setReminders(due); setAccounts(all);
    if (due[0]) { setAmount((due[0].remaining_cents / 100).toFixed(2).replace('.', ',')); setAccountId(all[0]?.id || ''); }
  }
  useEffect(() => { void load().catch(() => {}); }, [workspace.id, token, refresh]);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError('');
    try { await work(); setReceiving(false); await load(); onChanged(); }
    catch(e) { setError(e instanceof Error ? e.message : 'Não foi possível concluir.'); }
    finally { setBusy(false); }
  }
  return <Modal visible={!!current} animationType="slide" onRequestClose={() => {}}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{flexGrow:1,justifyContent:'center',padding:24,backgroundColor:palette.bg}}>
      <Card>
        <Text style={{fontSize:24,fontWeight:'700',color:palette.ink}}>Receita prevista para hoje</Text>
        {current && <>
          <Text style={{color:palette.ink}}>{current.description} · {money(current.remaining_cents)} a receber</Text>
          <Text style={{color:palette.muted}}>Previsão em {current.due_on.split('-').reverse().join('/')}. Informe se recebeu ou deixe o lembrete para amanhã.</Text>
          {!receiving ? <>
            <Button label="Recebi" onPress={() => setReceiving(true)} />
            <Button label="Ainda não recebi" secondary onPress={() => void act(async () => { await request(`${root}/income-occurrences/${current.id}/defer`, token, 'POST'); })} />
          </> : <>
            <Text style={{ color: palette.ink }}>Conta de recebimento</Text>
            <ScrollView horizontal contentContainerStyle={{gap:8}}>{accounts.map(a => <Chip key={a.id} label={a.name} selected={accountId === a.id} onPress={() => setAccountId(a.id)} />)}</ScrollView>
            {!accounts.length && <Text style={{ color: palette.ink }}>Cadastre uma conta antes de registrar o recebimento. Você pode escolher “Ainda não recebi” e voltar depois.</Text>}
            <Text style={{ color: palette.ink }}>Valor recebido (R$)</Text>
            <TextInput accessibilityLabel="Valor recebido" style={input()} keyboardType="decimal-pad" value={amount} onChangeText={setAmount} />
            <Text style={{ color: palette.ink }}>Depois deste recebimento</Text>
            <View style={{flexDirection:'row',gap:8}}><Chip label="Concluir previsão" selected={complete} onPress={() => setComplete(true)} /><Chip label="Manter diferença" selected={!complete} onPress={() => setComplete(false)} /></View>
            <Button label={busy ? 'Salvando…' : 'Confirmar recebimento'} onPress={() => { const cents = parseCents(amount); if (!accountId || cents === null) { setError('Informe uma conta e um valor válido.'); return; } void act(async () => { await request(`${root}/income-occurrences/${current.id}/receive`, token, 'POST', {account_id:accountId,amount_cents:cents,occurred_on:localDate().split('/').reverse().join('-'),complete,request_id:`${Date.now()}-${Math.random().toString(36).slice(2)}`}); }); }} />
            <Button label="Voltar" secondary onPress={() => setReceiving(false)} />
          </>}
        </>}
      </Card>
    </ScrollView><ToastViewport bottom={24} />
  </Modal>;
}
