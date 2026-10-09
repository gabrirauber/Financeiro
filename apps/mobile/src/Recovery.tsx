import React, { useState } from 'react';
import { ScrollView, Text, TextInput } from 'react-native';
import { request } from './api';
import { Button, Card, palette } from './ui';

export function Recovery({ token, onDone }: { token?: string; onDone: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const style = { padding: 14, borderWidth: 1, borderColor: palette.line, borderRadius: 12, fontSize: 16 };
  async function submit() {
    setMessage('');
    if (token && password !== confirmation) { setMessage('As senhas não coincidem.'); return; }
    setBusy(true);
    try {
      if (token) {
        await request('/auth/password-reset/confirm', undefined, 'POST', { token, password });
        setPassword(''); setConfirmation(''); setSuccess(true);
        setMessage('Senha alterada. Entre novamente com sua nova senha.');
      } else {
        const result = await request<{message: string}>('/auth/password-reset/request', undefined, 'POST', { email: email.trim() });
        setMessage(result.message);
      }
    } catch(e) { setMessage(e instanceof Error ? e.message : 'Não foi possível concluir.'); }
    finally { setBusy(false); }
  }
  return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:24,gap:16,maxWidth:560,width:'100%',alignSelf:'center'}}>
    <Card><Text style={{fontSize:24,color:palette.ink}}>{token ? 'Definir nova senha' : 'Recuperar acesso'}</Text>
      {!success && (token ? <>
        <TextInput accessibilityLabel="Nova senha" placeholder="Nova senha (mínimo 10 caracteres)" secureTextEntry style={style} value={password} onChangeText={setPassword} maxLength={128} />
        <TextInput accessibilityLabel="Confirmar nova senha" placeholder="Confirme a nova senha" secureTextEntry style={style} value={confirmation} onChangeText={setConfirmation} maxLength={128} />
      </> : <TextInput accessibilityLabel="E-mail de recuperação" placeholder="Seu e-mail" autoCapitalize="none" keyboardType="email-address" style={style} value={email} onChangeText={setEmail} />)}
      {!!message && <Text accessibilityLiveRegion="polite">{message}</Text>}
      {busy ? <Text>Aguarde…</Text> : <>
        {!success && <Button label={token ? 'Alterar senha' : 'Enviar link de recuperação'} onPress={() => void submit()} />}
        <Button label="Voltar para entrada" secondary onPress={onDone} />
      </>}
    </Card>
  </ScrollView>;
}
