# Decisões de negócio pendentes

Data: 07/10/2026. As propostas abaixo aguardam resposta/revisão do cliente. Não substituem silenciosamente as regras já aprovadas.

## DEC-01 — Renda prevista e recebimento diferente

Aprovada pelo cliente em 12/10/2026: em cada recebimento vinculado, escolher entre concluir a previsão ou manter a diferença pendente.

Afeta RF-21/22/23/24, E08/E09.

Proposta: renda considerada = receitas recebidas no mês + valores ainda esperados das previsões do mês, sem duplicar recebimentos vinculados. Receita extra aumenta a renda considerada. Ao lançar recebimento de uma previsão, indicar se encerra a previsão ou se ainda falta receber; lançamento sempre entra imediatamente no saldo.

Exemplo: previsão de R$ 3.000, recebimento de R$ 2.800 marcado como concluído e extra de R$ 200 resultam em renda considerada de R$ 3.000 e nada a receber. Se os R$ 2.800 forem parciais, ficam R$ 200 previstos; com extra de R$ 200, renda considerada passa a R$ 3.200.

## DEC-02 — Refinanciamento e resultado mensal

Aprovada pelo cliente em 12/10/2026: o resultado do mês original considera apenas o valor efetivamente pago da fatura; o principal refinanciado entra nas parcelas futuras. O gráfico mantém as compras no mês da fatura original.

Afeta RF-17/18/23/24, E07/E09.

Proposta: separar gráfico de compras/compromissos e resultado financeiro. No mês de origem, manter compras no gráfico; no resultado financeiro, retirar do compromisso daquele mês o principal transferido às faturas futuras, explicando o ajuste. Meses futuros incluem as parcelas financiadas, com principal e encargos discriminados.

Exemplo sem outros gastos: renda R$ 1.500 e fatura R$ 1.000. Antes de refinanciar, resultado previsto R$ 500. Pagamento de R$ 600 e refinanciamento dos R$ 400 restantes mudam o resultado financeiro para R$ 900; gráfico original continua mostrando R$ 1.000 em compras. Duas parcelas de R$ 220 comprometem os dois meses seguintes. Com saldo atual de R$ 1.500 antes do pagamento, após a operação há R$ 900 em caixa; não descontar R$ 1.000 outra vez.

Esta regra refina a fórmula original da modelagem e foi aprovada para a E09.

## DEC-03 — Correções, parcelas e pendências antigas

Decisão adicional E09 aprovada em 12/10/2026: despesas fixas e faturas antigas ainda não pagas reduzem o saldo final previsto atual e futuro, em linha separada. Não são lançadas novamente como gasto do mês corrente. As demais regras de correção seguem as decisões já registradas abaixo.

Afeta RF-11/24/26/27, E04–E09.

Proposta: movimentos de caixa são editáveis conforme sua data financeira; parcelas conforme o mês de vencimento. Meses anteriores ficam protegidos. Parcela de compra antiga pode ser corrigida no mês corrente se ainda não paga, preservando as anteriores. Pendências antigas continuam no saldo final projetado como atrasadas, sem reapresentá-las como novo consumo do mês.

Decisão E06: fatura paga fica bloqueada. Correção de compra parcelada redistribui apenas parcelas do mês corrente e futuras que ainda não estejam pagas; parcelas de meses anteriores e de faturas pagas permanecem intactas. Edição individual de uma ocorrência futura permanece fora desta etapa.

## DEC-04 — Convites e administração

Aprovada pelo cliente em 08/10/2026: adotar as regras abaixo.

Afeta RF-03/04, E03.

Proposta: código de uso único válido por 24 horas; administrador pode invalidar e gerar outro. Último administrador só sai após transferir a administração. Aceitar convite mantém logins individuais e não expõe credenciais.

## DEC-05 — Recuperação de senha

Aprovada pelo cliente em 08/10/2026: link temporário de uso único por e-mail. Provedor e configuração ficam para antes da publicação.

Afeta RF-28, E03/E11.

Proposta para revisão antes da E03: link temporário de uso único enviado ao e-mail cadastrado, com mensagem neutra para endereços desconhecidos. Provedor e custos serão avaliados quando houver integração; nenhum serviço foi contratado.

## Regra de precedência

Respostas explícitas do cliente devem ser registradas aqui, com atualização dos critérios e da modelagem afetados. Uma decisão pendente pode ser documentada e revisada na E00, mas impede implementar a parte dependente até ser resolvida. Aprovar uma etapa não implica aceitar automaticamente todas as propostas deste arquivo.
