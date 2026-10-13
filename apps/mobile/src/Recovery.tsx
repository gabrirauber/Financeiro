import React, { useState } from 'react';
import { ScrollView, Text, TextInput } from 'react-native';
import { request } from './api';
import { Button, Card, palette } from './ui';
import { useToast } from './Toast';

export function Recovery({ token, onDone }: { token?: string; onDone: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const { show } = useToast();
  const [success, setSuccess] = useState(false);
  const style = { padding: 14, borderWidth: 1, borderColor: palette.line, borderRadius: 12, fontSize: 16 };
  async function submit() {
    if (token && password !== confirmation) { show('As senhas não coincidem.', 'error'); return; }
    setBusy(true);
    try {
      if (token) {
        await request('/auth/password-reset/confirm', undefined, 'POST', { token, password });
        setPassword(''); setConfirmation(''); setSuccess(true);
        show('Senha alterada. Entre novamente com sua nova senha.');
      } else {
        const result = await request<{message: string}>('/auth/password-reset/request', undefined, 'POST', { email: email.trim() });
        show(result.message);
      }
    } catch(e) { show(e instanceof Error ? e.message : 'Não foi possível concluir.', 'error'); }
    finally { setBusy(false); }
  }
  return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:24,gap:16,maxWidth:560,width:'100%',alignSelf:'center'}}>
    <Card><Text style={{fontSize:24,color:palette.ink}}>{token ? 'Definir nova senha' : 'Recuperar acesso'}</Text>
      {!success && (token ? <>
        <TextInput accessibilityLabel="Nova senha" placeholder="Nova senha (mínimo 10 caracteres)" secureTextEntry style={style} value={password} onChangeText={setPassword} maxLength={128} />
        <TextInput accessibilityLabel="Confirmar nova senha" placeholder="Confirme a nova senha" secureTextEntry style={style} value={confirmation} onChangeText={setConfirmation} maxLength={128} />
      </> : <TextInput accessibilityLabel="E-mail de recuperação" placeholder="Seu e-mail" autoCapitalize="none" keyboardType="email-address" style={style} value={email} onChangeText={setEmail} />)}
      {busy ? <Text style={{ color: palette.ink }}>Aguarde…</Text> : <>
        {!success && <Button label={token ? 'Alterar senha' : 'Enviar link de recuperação'} onPress={() => void submit()} />}
        <Button label="Voltar para entrada" secondary onPress={onDone} />
      </>}
    </Card>
  </ScrollView>;
}
