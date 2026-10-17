import React, { useEffect, useState } from 'react';
import { Share, Text, View } from 'react-native';
import { Member, request, Workspace } from './api';
import { Button, Card, palette } from './ui';
import { useToastSetter } from './Toast';

type Invite = { id: string; expires_at: string };
type AccessUser = { id: string; email: string; status: 'pending' | 'approved' | 'rejected' | 'revoked'; requested_at: string; access_admin: boolean; demo: boolean };
const accessLabel = { pending: 'Aguardando aprovação', approved: 'Acesso ativo', rejected: 'Pedido recusado', revoked: 'Acesso revogado' };
export function MembersPanel({ workspace, token, accessAdmin, onClose, onChanged }: { workspace: Workspace; token: string; accessAdmin: boolean; onClose: () => void; onChanged: () => Promise<void> }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [accessUsers, setAccessUsers] = useState<AccessUser[]>([]);
  const [created, setCreated] = useState<{id: string; code: string}>();
  const setError = useToastSetter('error');
  const setSuccess = useToastSetter('success');
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<string>();
  async function load() {
    setMembers(await request<Member[]>(`/workspaces/${workspace.id}/members`, token));
    setInvites(workspace.role === 'admin' ? await request<Invite[]>(`/workspaces/${workspace.id}/invites`, token) : []);
    if (accessAdmin) setAccessUsers(await request<AccessUser[]>('/admin/users', token));
  }
  useEffect(() => { void load().catch(e => setError(e.message)); }, [workspace.id, workspace.role, accessAdmin]);
  async function action(callback: () => Promise<void>) {
    setBusy(true); setError('');
    try { await callback(); setConfirm(undefined); }
    catch(e) { setError(e instanceof Error ? e.message : 'Não foi possível concluir.'); }
    finally { setBusy(false); }
  }
  async function remove(id: string) {
    await request(`/workspaces/${workspace.id}/members/${id}`, token, 'DELETE'); await load();
  }
  async function decideAccess(id: string, status: 'approved' | 'rejected' | 'revoked') {
    await request(`/admin/users/${id}/access`, token, 'PATCH', { status });
    await load();
  }
  async function deleteAccess(id: string) {
    await request(`/admin/users/${id}`, token, 'DELETE');
    await load();
    setSuccess('Cadastro excluído.');
  }
  return <>
    {accessAdmin && <Card>
      <Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Acesso ao Rautto</Text>
      <Text style={{ color: palette.muted }}>Novos cadastros só podem entrar depois da sua aprovação. Participar de um espaço é uma permissão separada.</Text>
      {!accessUsers.some(item => item.status === 'pending') && <Text style={{ color: palette.muted }}>Nenhum pedido aguardando aprovação.</Text>}
      {accessUsers.filter(item => !item.access_admin).map(item => <View key={item.id} style={{ gap: 8, paddingVertical: 12, borderTopWidth: 1, borderColor: palette.line }}>
        <Text style={{ color: palette.ink, fontWeight: '700' }}>{item.email}</Text>
        {item.demo && <Text style={{ color: palette.muted }}>Demonstração · consulta o seu espaço real sem poder salvar alterações</Text>}
        <Text style={{ color: item.status === 'pending' ? palette.accent : palette.muted }}>{accessLabel[item.status]}</Text>
        {item.status !== 'approved' && !busy && <Button label={`Aprovar ${item.email}`} onPress={() => void action(() => decideAccess(item.id, 'approved'))} />}
        {item.status === 'pending' && !busy && <Button label={`Recusar ${item.email}`} secondary onPress={() => void action(() => decideAccess(item.id, 'rejected'))} />}
        {item.status === 'approved' && !busy && (confirm === `revoke-${item.id}` ? <>
          <Text style={{ color: palette.ink }}>O acesso desta pessoa ao aplicativo será encerrado, inclusive nas sessões abertas.</Text>
          <Button label="Confirmar revogação" onPress={() => void action(() => decideAccess(item.id, 'revoked'))} />
          <Button label="Cancelar" secondary onPress={() => setConfirm(undefined)} />
        </> : <Button label={`Revogar acesso de ${item.email}`} secondary onPress={() => setConfirm(`revoke-${item.id}`)} />)}
        {item.status === 'revoked' && !item.demo && !busy && (confirm === `delete-${item.id}` ? <>
          <Text style={{ color: palette.ink }}>Excluir definitivamente o cadastro de {item.email}? Se a pessoa for a única participante do próprio espaço, esse espaço e seus dados financeiros também serão apagados. Os dados de espaços compartilhados serão preservados.</Text>
          <Button label="Confirmar exclusão" onPress={() => void action(() => deleteAccess(item.id))} />
          <Button label="Cancelar" secondary onPress={() => setConfirm(undefined)} />
        </> : <Button label={`Excluir cadastro de ${item.email}`} secondary onPress={() => setConfirm(`delete-${item.id}`)} />)}
      </View>)}
    </Card>}
    <Card><Text style={{ fontSize: 20, color: palette.ink }}>Participantes · {workspace.name}</Text>
    {workspace.role === 'admin' && <>
      <Text style={{ color: palette.ink }}>Convite de uso único, válido por 24 horas.</Text>
      {!!created && <View style={{gap:8}}><Text selectable accessibilityLabel="Código gerado" style={{fontSize:22,fontWeight:'700'}}>{created.code}</Text>
        <Button label="Compartilhar código" secondary onPress={() => void action(async () => { await Share.share({message: `Ao criar seu cadastro no Rautto, informe o código ${created.code} para entrar no nosso espaço. Válido por 24 horas, para uma pessoa.`}); })} />
      </View>}
      {!busy && <Button label="Gerar código de convite" onPress={() => void action(async () => {
        const result = await request<{id:string;code:string}>(`/workspaces/${workspace.id}/invites`, token, 'POST'); setCreated(result); await load();
      })} />}
      {invites.map((invite, index) => <View key={invite.id} style={{gap:8}}>
        <Text style={{ color: palette.ink }}>Convite {index+1} · expira {new Date(invite.expires_at).toLocaleString('pt-BR')}</Text>
        {!busy && <Button label={`Invalidar convite ${index+1}`} secondary onPress={() => void action(async () => {
          await request(`/workspaces/${workspace.id}/invites/${invite.id}`,token,'DELETE');
          if(created?.id===invite.id) setCreated(undefined); await load();
        })} />}
      </View>)}
    </>}
    {members.map(member => <View key={member.id} style={{ gap: 8, paddingVertical: 10 }}>
      <Text style={{ color: palette.ink }}>{member.email}</Text><Text style={{ color: palette.ink }}>{member.role === 'admin' ? 'Administrador' : 'Participante'}</Text>
      {workspace.role === 'admin' && member.role !== 'admin' && !busy && (confirm === member.id ? <>
        <Text style={{ color: palette.ink }}>Esta pessoa perderá o acesso a este espaço.</Text>
        <Button label="Confirmar remoção" onPress={() => void action(() => remove(member.id))} />
        <Button label="Cancelar remoção" secondary onPress={() => setConfirm(undefined)} />
      </> : confirm === 'transfer-'+member.id ? <>
        <Text style={{ color: palette.ink }}>Você deixará de ser administrador e esta pessoa assumirá a administração.</Text>
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
    {workspace.role === 'admin' ? <Text style={{ color: palette.ink }}>Para sair deste espaço, transfira a administração a outro participante.</Text> : !busy && (confirm === 'leave' ? <>
      <Text style={{ color: palette.ink }}>Você perderá o acesso e precisará de outro convite para voltar.</Text>
      <Button label="Confirmar saída do espaço" onPress={() => void action(async () => { await request(`/workspaces/${workspace.id}/leave`, token, 'POST'); await onChanged(); onClose(); })} />
      <Button label="Cancelar saída" secondary onPress={() => setConfirm(undefined)} />
    </> : <Button label="Sair deste espaço" secondary onPress={() => setConfirm('leave')} />)}
    <Button label="Fechar participantes" secondary onPress={onClose} />
    </Card>
  </>;
}
