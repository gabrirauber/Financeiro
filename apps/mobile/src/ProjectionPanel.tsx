import React, { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { request, Workspace } from './api';
import { money } from './prototype';
import { Card, palette } from './ui';
import { useToastSetter } from './Toast';

type Projection = {
  kind: 'historical' | 'current' | 'future';
  received_income_cents: number;
  expected_income_cents: number;
  income_cents: number;
  paid_expenses_cents: number;
  pending_fixed_cents: number;
  card_commitment_cents: number;
  card_refinanced_cents: number;
  committed_cents: number;
  result_cents: number;
  commitment_percent: number | null;
  cash_balance_cents: number;
  expected_through_month_cents: number;
  fixed_through_month_cents: number;
  card_through_month_cents: number;
  overdue_cents: number;
  projected_balance_cents: number;
};

function Line({ label, value }: { label: string; value: number }) {
  return <View style={{flexDirection:'row',justifyContent:'space-between',gap:12}}>
    <Text style={{color:palette.muted,flex:1}}>{label}</Text>
    <Text style={{color:palette.ink,fontWeight:'600'}}>{money(value)}</Text>
  </View>;
}

export function ProjectionPanel({ workspace, token, period, refresh }: {
  workspace: Workspace; token: string; period: string; refresh: number;
}) {
  const [data, setData] = useState<Projection>();
  const [details, setDetails] = useState(false);
  const setError = useToastSetter('error');
  useEffect(() => {
    let active = true;
    setData(undefined);
    request<Projection>(`/workspaces/${workspace.id}/projection?month=${period}`, token)
      .then(value => { if (active) setData(value); })
      .catch(error => { if (active) setError(error instanceof Error ? error.message : 'Não foi possível calcular o planejamento.'); });
    return () => { active = false; };
  }, [workspace.id, token, period, refresh]);
  if (!data) return <Card><Text style={{color:palette.muted}}>Calculando a saúde do mês…</Text></Card>;
  const historical = data.kind === 'historical';
  const negative = data.result_cents < 0;
  const balanceNegative = data.projected_balance_cents < 0;
  return <Card>
    <Text style={{fontSize:19,fontWeight:'700',color:palette.ink}}>Saúde do mês</Text>
    <Text style={{color:palette.muted}}>{historical ? 'Valores realizados no mês consultado' : data.kind === 'future' ? 'Projeção para este mês' : 'Realizado e ainda previsto para este mês'}</Text>
    <View style={{gap:4,paddingVertical:6}}>
      <Text style={{color:palette.muted}}>Resultado do mês</Text>
      <Text style={{fontSize:30,fontWeight:'800',color:negative ? '#AA422E' : palette.green}}>{money(data.result_cents)}</Text>
      <Text style={{color:palette.muted}}>{negative ? 'As despesas e faturas superam a renda considerada.' : 'Renda considerada menos despesas e faturas do mês.'}</Text>
    </View>
    <View style={{borderTopWidth:1,borderColor:palette.line,paddingTop:14,gap:5}}>
      <Text style={{color:palette.muted}}>{historical ? 'Saldo no fim daquele mês' : 'Saldo final previsto'}</Text>
      <Text style={{fontSize:25,fontWeight:'700',color:balanceNegative ? '#AA422E' : palette.ink}}>{money(data.projected_balance_cents)}</Text>
      <Text style={{color:palette.muted}}>{historical ? 'Saldo das contas naquela data.' : 'Parte do saldo em caixa e considera apenas o que ainda falta receber e pagar.'}</Text>
    </View>
    <View style={{borderTopWidth:1,borderColor:palette.line,paddingTop:14,gap:4}}>
      <Text style={{color:palette.muted}}>Renda comprometida</Text>
      <Text style={{fontSize:20,fontWeight:'700',color:palette.ink}}>{data.commitment_percent === null ? 'Não se aplica sem renda' : `${data.commitment_percent.toLocaleString('pt-BR', {maximumFractionDigits:1})}%`}</Text>
      <Text style={{color:palette.muted}}>{money(data.committed_cents)} de {money(data.income_cents)} de renda considerada</Text>
    </View>
    <Pressable accessibilityRole="button" accessibilityState={{expanded:details}} onPress={() => setDetails(value => !value)} style={{paddingVertical:10}}>
      <Text style={{color:palette.green,fontWeight:'700'}}>{details ? 'Ocultar cálculo ↑' : 'Como calculamos ↓'}</Text>
    </Pressable>
    {details && <View style={{gap:10,borderTopWidth:1,borderColor:palette.line,paddingTop:12}}>
      <Text style={{color:palette.ink,fontWeight:'700'}}>Resultado deste mês</Text>
      <Line label="Receitas recebidas" value={data.received_income_cents} />
      {!historical && <Line label="Rendas ainda esperadas" value={data.expected_income_cents} />}
      <Line label="Despesas já pagas" value={data.paid_expenses_cents} />
      {!historical && <Line label="Despesas fixas pendentes" value={data.pending_fixed_cents} />}
      <Line label="Faturas do mês" value={data.card_commitment_cents} />
      {!!data.card_refinanced_cents && <Text style={{color:palette.muted}}>O principal refinanciado, {money(data.card_refinanced_cents)}, saiu do resultado deste mês e entra nas parcelas futuras. As compras continuam no gráfico do mês original.</Text>}
      {!historical && <>
        <Text style={{color:palette.ink,fontWeight:'700',marginTop:6}}>Saldo final previsto</Text>
        <Line label="Saldo atual das contas" value={data.cash_balance_cents} />
        <Line label={data.kind === 'future' ? 'A receber até este mês' : 'Ainda a receber'} value={data.expected_through_month_cents} />
        <Line label={data.kind === 'future' ? 'Fixas pendentes até este mês' : 'Fixas pendentes'} value={data.fixed_through_month_cents} />
        <Line label={data.kind === 'future' ? 'Faturas pendentes até este mês' : 'Faturas pendentes'} value={data.card_through_month_cents} />
        {!!data.overdue_cents && <Line label="Pendências de meses anteriores" value={data.overdue_cents} />}
        <Text style={{color:palette.muted}}>Pagamentos já feitos estão no saldo atual e não são descontados outra vez. Despesas avulsas futuras ainda não lançadas não entram na projeção.</Text>
      </>}
    </View>}
  </Card>;
}
