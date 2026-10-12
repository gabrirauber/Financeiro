import React, { useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';
import { fetch as expoFetch } from 'expo/fetch';
import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { Workspace } from './api';
import { useToastSetter } from './Toast';
import { Button, Card, palette } from './ui';

async function reportResponse(workspace: Workspace, token: string, period: string, detail: boolean) {
  const base = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');
  if (!base) throw new Error('Configure o endereço do servidor para gerar o relatório.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await expoFetch(`${base}/workspaces/${workspace.id}/reports/monthly.pdf?month=${period}&detail=${detail}`, {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/pdf' },
      signal: controller.signal,
    });
    if (!response.ok) {
      const problem = await response.json().catch(() => null) as { detail?: string } | null;
      throw new Error(problem?.detail || 'Não foi possível gerar o relatório. Tente novamente.');
    }
    return response;
  } finally { clearTimeout(timeout); }
}

export function MonthlyReport({ workspace, token, period }: {
  workspace: Workspace; token: string; period: string;
}) {
  const [detail, setDetail] = useState(false);
  const [busy, setBusy] = useState(false);
  const showError = useToastSetter('error');
  const showSuccess = useToastSetter('success');

  async function generate() {
    if (busy) return;
    setBusy(true);
    try {
      const response = await reportResponse(workspace, token, period, detail);
      const filename = `financeiro-${period}${detail ? '-detalhado' : ''}.pdf`;
      if (Platform.OS === 'web') {
        const url = URL.createObjectURL(await response.blob());
        const anchor = document.createElement('a');
        anchor.href = url; anchor.download = filename;
        document.body.appendChild(anchor); anchor.click(); anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
        showSuccess('PDF gerado. Confira seus downloads.');
      } else {
        const file = new File(Paths.cache, filename);
        file.write(await response.bytes());
        if (!await Sharing.isAvailableAsync()) {
          throw new Error('O compartilhamento não está disponível neste aparelho.');
        }
        await Sharing.shareAsync(file.uri, {
          mimeType: 'application/pdf', dialogTitle: 'Compartilhar relatório financeiro',
        });
      }
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Não foi possível gerar o relatório.');
    } finally { setBusy(false); }
  }

  return <Card>
    <Text style={{ fontSize: 19, fontWeight: '700', color: palette.ink }}>Relatório do mês</Text>
    <Text style={{ color: palette.muted }}>
      Resumo financeiro em PDF, com categorias, faturas, saldos e previsão.
    </Text>
    <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: detail }}
      onPress={() => setDetail(value => !value)} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12 }}>
      <View style={{ width: 22, height: 22, borderWidth: 1.5, borderColor: palette.green,
        borderRadius: 5, backgroundColor: detail ? palette.green : 'transparent', alignItems: 'center' }}>
        {detail && <Text style={{ color: 'white', fontWeight: '700' }}>✓</Text>}
      </View>
      <Text style={{ color: palette.ink, flex: 1 }}>Incluir lançamentos detalhados</Text>
    </Pressable>
    <Button label={busy ? 'Gerando PDF…' : Platform.OS === 'web' ? 'Baixar PDF' : 'Gerar e compartilhar PDF'}
      onPress={() => { void generate(); }} disabled={busy} />
  </Card>;
}
