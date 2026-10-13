import React from 'react';
import { Text, View } from 'react-native';
import { Button, Card, palette } from './ui';

const steps = [
  { title: 'Cadastre sua primeira conta', detail: 'Pode ser uma conta bancária ou dinheiro. Informe o saldo atual para começar com o caixa correto.', action: 'Cadastrar conta' },
  { title: 'Adicione um cartão de crédito', detail: 'Informe os dias de fechamento e vencimento para que as compras entrem na fatura certa.', action: 'Cadastrar cartão' },
  { title: 'Planeje suas despesas fixas', detail: 'Inclua compromissos como aluguel e internet. Eles ajudam a prever como o mês vai terminar.', action: 'Cadastrar despesa fixa' },
  { title: 'Inclua recorrências no cartão', detail: 'Cadastre assinaturas e outras cobranças mensais para aparecerem automaticamente nas faturas.', action: 'Cadastrar assinatura' },
] as const;

export function FirstRunGuide({ step, exists, hasCard, onOpen, onNext, onFinish }: {
  step: number; exists: boolean; hasCard: boolean;
  onOpen: () => void; onNext: () => void; onFinish: () => void;
}) {
  const current = steps[step];
  if (!current) return null;
  const needsCard = step === 3 && !hasCard;
  return <Card>
    <Text style={{ color: palette.green, fontSize: 12, fontWeight: '700', letterSpacing: 1 }}>PRIMEIROS PASSOS · {step + 1} DE 4</Text>
    <View style={{ flexDirection: 'row', gap: 6 }}>{steps.map((_, index) =>
      <View key={index} style={{ flex: 1, height: 5, borderRadius: 3, backgroundColor: index <= step ? palette.green : palette.track }} />)}</View>
    <Text style={{ color: palette.ink, fontSize: 24, fontWeight: '700' }}>{current.title}</Text>
    <Text style={{ color: palette.muted, lineHeight: 22 }}>{current.detail}</Text>
    {exists && <Text style={{ color: palette.green }}>Esta etapa já tem um cadastro no espaço.</Text>}
    {needsCard && <Text style={{ color: palette.muted }}>Para criar uma assinatura no cartão, cadastre um cartão primeiro.</Text>}
    <Button label={exists ? 'Continuar' : needsCard ? 'Cadastrar cartão primeiro' : current.action} onPress={exists ? onNext : onOpen} />
    <Button label="Pular esta etapa" secondary onPress={onNext} />
    <Button label="Pular todo o guia" secondary onPress={onFinish} />
  </Card>;
}
