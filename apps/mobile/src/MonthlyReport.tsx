import React, { useState } from 'react';
import { Keyboard, Platform, Pressable, Text, TextInput, View } from 'react-native';
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

function monthInput(period: string) {
  return `${period.slice(5, 7)}/${period.slice(0, 4)}`;
}

function selectedPeriod(value: string) {
  const match = /^(\d{2})\/(\d{4})$/.exec(value);
  if (!match) return null;
  const month = Number(match[1]);
  const year = Number(match[2]);
  return month >= 1 && month <= 12 && year >= 1000 ? `${match[2]}-${match[1]}` : null;
}

export function MonthlyReport({ workspace, token, period }: {
  workspace: Workspace; token: string; period: string;
}) {
  const [detail, setDetail] = useState(false);
  const [reportMonth, setReportMonth] = useState(() => monthInput(period));
  const [busy, setBusy] = useState(false);
  const showError = useToastSetter('error');
  const showSuccess = useToastSetter('success');

  async function generate() {
    if (busy) return;
    const month = selectedPeriod(reportMonth);
    if (!month) { showError('Informe um mês válido no formato MM/AAAA.'); return; }
    Keyboard.dismiss();
    setBusy(true);
    try {
      const response = await reportResponse(workspace, token, month, detail);
      const filename = `rautto-${month}${detail ? '-detalhado' : ''}.pdf`;
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

  function moveMonth(change: number) {
    Keyboard.dismiss();
    const month = selectedPeriod(reportMonth) || period;
    const [year, number] = month.split('-').map(Number);
    const next = new Date(year, number - 1 + change, 1);
    setReportMonth(`${String(next.getMonth() + 1).padStart(2, '0')}/${next.getFullYear()}`);
  }

  return <Card>
    <Text style={{ fontSize: 19, fontWeight: '700', color: palette.ink }}>Relatório do mês</Text>
    <Text style={{ color: palette.muted }}>
      Resumo financeiro em PDF, com categorias, faturas, saldos e previsão.
    </Text>
    <Text style={{ color: palette.ink, fontWeight: '600' }}>Mês do relatório (MM/AAAA)</Text>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Pressable accessibilityRole="button" accessibilityLabel="Mês anterior do relatório" disabled={busy}
        onPress={() => moveMonth(-1)} style={{ padding: 12, borderRadius: 12, backgroundColor: palette.soft }}>
        <Text style={{ color: palette.green, fontWeight: '700', fontSize: 20 }}>‹</Text>
      </Pressable>
      <TextInput accessibilityLabel="Mês do relatório" value={reportMonth}
        onChangeText={value => { const digits = value.replace(/\D/g, '').slice(0, 6); setReportMonth(digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits); }}
        keyboardType="number-pad" maxLength={7} editable={!busy} placeholder="MM/AAAA"
        style={{ flex: 1, minHeight: 48, borderWidth: 1, borderColor: palette.line, borderRadius: 12,
          paddingHorizontal: 14, textAlign: 'center', color: palette.ink, backgroundColor: palette.white }} />
      <Pressable accessibilityRole="button" accessibilityLabel="Próximo mês do relatório" disabled={busy}
        onPress={() => moveMonth(1)} style={{ padding: 12, borderRadius: 12, backgroundColor: palette.soft }}>
        <Text style={{ color: palette.green, fontWeight: '700', fontSize: 20 }}>›</Text>
      </Pressable>
    </View>
    <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: detail }}
      onPress={() => setDetail(value => !value)} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12 }}>
      <View style={{ width: 22, height: 22, borderWidth: 1.5, borderColor: palette.green,
        borderRadius: 5, backgroundColor: detail ? palette.green : 'transparent', alignItems: 'center' }}>
        {detail && <Text style={{ color: palette.bg, fontWeight: '700' }}>✓</Text>}
      </View>
      <Text style={{ color: palette.ink, flex: 1 }}>Incluir lançamentos detalhados</Text>
    </Pressable>
    <Button label={busy ? 'Gerando PDF…' : Platform.OS === 'web' ? 'Baixar PDF' : 'Gerar e compartilhar PDF'}
      onPress={() => { void generate(); }} disabled={busy} />
  </Card>;
}
