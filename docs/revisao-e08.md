# Revisão da E08 — planejamento mensal

A E08 adiciona uma aba **Planejamento**. Nela é possível cadastrar despesas fixas, assinaturas no cartão e rendas previstas por participante. Cada regra gera uma ocorrência por mês. Despesas fixas ficam pendentes até o pagamento; o valor realmente pago substitui a previsão no resumo, sem somar os dois. Assinaturas geram uma compra no cartão e entram na fatura. O servidor gera ocorrências mesmo sem o aplicativo aberto.

Rendas previstas não alteram o saldo. No dia previsto, ao abrir o app, a pessoa escolhe “Recebi” ou “Ainda não recebi”. Ao receber, informa a conta e o valor; se vier menos que o previsto, escolhe concluir ou manter a diferença para outro recebimento. “Ainda não recebi” adia o lembrete para o dia seguinte.

Para conferir no app local:

As confirmações e os erros aparecem como avisos flutuantes na parte inferior e somem automaticamente (ou ao tocar neles). O quadro permanente de conexão não aparece mais no resumo.

1. Em **Planejamento**, cadastre uma despesa fixa de R$ 100 no dia de hoje. Confirme que o resumo a mostra como prevista e que o saldo da conta não muda. Registre o pagamento por R$ 110 e confirme que o resumo mostra apenas R$ 110 e o saldo cai R$ 110.
2. Cadastre uma assinatura de R$ 50 no cartão no dia de hoje. Confirme uma única compra na fatura. Reabra o app: a assinatura não deve duplicar.
3. Cadastre uma renda prevista de R$ 3.000 para hoje. No lembrete, registre R$ 2.800 e escolha “Manter diferença”. No Planejamento, devem restar R$ 200; o caixa deve subir apenas R$ 2.800. Um novo recebimento pode encerrar a previsão.
4. Para “Ainda não recebi”, o lembrete deve desaparecer no dia atual e voltar no dia seguinte. Para revisar sem esperar, use apenas o banco descartável de testes.

O comando do servidor `python -m app.finance.run_recurring` também executa a geração mensal. A API a executa na inicialização e a cada hora enquanto o serviço estiver ativo. O banco impede duplicações por regra e mês, inclusive se a rotina rodar mais de uma vez.

Esta revisão é local. Nenhum push da E08 ou publicação no Railway foi feito.
