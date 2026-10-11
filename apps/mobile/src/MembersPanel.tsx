import React, { useEffect, useState } from 'react';
import { Share, Text, View } from 'react-native';
import { Member, request, Workspace } from './api';
import { Button, Card, palette } from './ui';

type Invite = { id: string; expires_at: string };
export function MembersPanel({ workspace, token, onClose, onChanged }: { workspace: Workspace; token: string; onClose: () => void; onChanged: () => Promise<void> }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [created, setCreated] = useState<{id: string; code: string}>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<string>();
  async function load() {
    setMembers(await request<Member[]>(`/workspaces/${workspace.id}/members`, token));
    setInvites(workspace.role === 'admin' ? await request<Invite[]>(`/workspaces/${workspace.id}/invites`, token) : []);
  }
  useEffect(() => { void load().catch(e => setError(e.message)); }, [workspace.id, workspace.role]);
  async function action(callback: () => Promise<void>) {
    setBusy(true); setError('');
    try { await callback(); setConfirm(undefined); }
    catch(e) { setError(e instanceof Error ? e.message : 'Não foi possível concluir.'); }
    finally { setBusy(false); }
  }
  async function remove(id: string) {
    await request(`/workspaces/${workspace.id}/members/${id}`, token, 'DELETE'); await load();
  }
  return <Card><Text style={{ fontSize: 20, color: palette.ink }}>Participantes · {workspace.name}</Text>
    {!!error && <Text accessibilityRole="alert" style={{ color: '#923D2B' }}>{error}</Text>}
    {workspace.role === 'admin' && <>
      <Text>Convite de uso único, válido por 24 horas.</Text>
      {!!created && <View style={{gap:8}}><Text selectable accessibilityLabel="Código gerado" style={{fontSize:22,fontWeight:'700'}}>{created.code}</Text>
        <Button label="Compartilhar código" secondary onPress={() => void action(async () => { await Share.share({message: `Ao criar seu cadastro no Financeiro, informe o código ${created.code} para entrar no nosso espaço. Válido por 24 horas, para uma pessoa.`}); })} />
      </View>}
      {!busy && <Button label="Gerar código de convite" onPress={() => void action(async () => {
        const result = await request<{id:string;code:string}>(`/workspaces/${workspace.id}/invites`, token, 'POST'); setCreated(result); await load();
      })} />}
      {invites.map((invite, index) => <View key={invite.id} style={{gap:8}}>
        <Text>Convite {index+1} · expira {new Date(invite.expires_at).toLocaleString('pt-BR')}</Text>
        {!busy && <Button label={`Invalidar convite ${index+1}`} secondary onPress={() => void action(async () => {
          await request(`/workspaces/${workspace.id}/invites/${invite.id}`,token,'DELETE');
          if(created?.id===invite.id) setCreated(undefined); await load();
        })} />}
      </View>)}
    </>}
    {members.map(member => <View key={member.id} style={{ gap: 8, paddingVertical: 10 }}>
      <Text>{member.email}</Text><Text>{member.role === 'admin' ? 'Administrador' : 'Participante'}</Text>
      {workspace.role === 'admin' && member.role !== 'admin' && !busy && (confirm === member.id ? <>
        <Text>Esta pessoa perderá o acesso a este espaço.</Text>
        <Button label="Confirmar remoção" onPress={() => void action(() => remove(member.id))} />
        <Button label="Cancelar remoção" secondary onPress={() => setConfirm(undefined)} />
      </> : confirm === 'transfer-'+member.id ? <>
        <Text>Você deixará de ser administrador e esta pessoa assumirá a administração.</Text>
        <Button label="Confirmar transferência" onPress={() => void action(async () => {
          await request(`/workspaces/${workspace.id}/transfer-admin/${member.id}`, token, 'POST');
          setCreated(undefined); await onChanged();
        })} />
        <Button label="Cancelar transferência" secondary onPress={() => setConfirm(undefined)} />
      </> : <>
        <Button label={`Remover ${member.email}`} secondary onPress={() => setConfirm(member.id)} />
        <Button label={`Transferir administração para ${member.email}`} secondary onPress={() => setConfirm('transfer-'+member.id)} />
      </>)}
    </View>)}
    {workspace.role === 'admin' ? <Text>Para sair deste espaço, transfira a administração a outro participante.</Text> : !busy && (confirm === 'leave' ? <>
      <Text>Você perderá o acesso e precisará de outro convite para voltar.</Text>
      <Button label="Confirmar saída do espaço" onPress={() => void action(async () => { await request(`/workspaces/${workspace.id}/leave`, token, 'POST'); await onChanged(); onClose(); })} />
      <Button label="Cancelar saída" secondary onPress={() => setConfirm(undefined)} />
    </> : <Button label="Sair deste espaço" secondary onPress={() => setConfirm('leave')} />)}
    <Button label="Fechar participantes" secondary onPress={onClose} />
  </Card>;
}
