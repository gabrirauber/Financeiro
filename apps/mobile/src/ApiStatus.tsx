import React, { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { Button, Card, palette } from './ui';

type State = 'checking' | 'ready' | 'unavailable' | 'unconfigured';

export function ApiStatus() {
  const [state, setState] = useState<State>('checking');
  const [attempt, setAttempt] = useState(0);
  const baseUrl = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');

  useEffect(() => {
    if (!baseUrl || !/^https?:\/\//i.test(baseUrl)) {
      setState('unconfigured');
      return;
    }
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    setState('checking');
    async function check() {
      try {
        const response = await fetch(`${baseUrl}/health/ready`, {
          signal: controller.signal,
          headers: { Accept: 'application/json' },
        });
        const body = await response.json();
        const healthy = response.ok && body.status === 'ok' && body.database === 'ready' && body.stage === 'E05';
        if (active) setState(healthy ? 'ready' : 'unavailable');
      } catch {
        if (active) setState('unavailable');
      } finally { clearTimeout(timeout); }
    }
    void check();
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [baseUrl, attempt]);

  const messages: Record<State, { title: string; text: string }> = {
    checking: { title: 'Verificando conexão…', text: 'Consultando o servidor e o banco de dados.' },
    ready: { title: 'Servidor conectado', text: 'Contas, receitas e despesas pagas salvas no servidor. Cartões ainda são exemplos.' },
    unavailable: { title: 'Não foi possível conectar', text: 'Verifique a internet ou tente novamente. Os saldos reais não podem ser consultados agora. Tente novamente.' },
    unconfigured: { title: 'Conexão ainda não configurada', text: 'Configure o endereço do servidor para consultar seus dados.' },
  };

  return <Card><View accessibilityLiveRegion="polite" style={{ gap: 8 }}>
    <Text style={{ color: palette.ink, fontWeight: '700', fontSize: 15 }}>{messages[state].title}</Text>
    <Text style={{ color: palette.muted, lineHeight: 20, fontSize: 13 }}>{messages[state].text}</Text>
  </View>{state !== 'checking' && state !== 'unconfigured' && <Button label={state === 'ready' ? 'Verificar conexão' : 'Tentar novamente'} secondary onPress={() => setAttempt(value => value + 1)} />}</Card>;
}
