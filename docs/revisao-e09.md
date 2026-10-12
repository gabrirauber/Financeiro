# Revisão da E09 — saúde do mês

A E09 acrescenta **Saúde do mês** ao Resumo. Use as setas de mês para comparar passado, presente e futuro. **Resultado do mês** considera renda recebida e ainda prevista menos despesas pagas, fixas pendentes e faturas daquele mês. **Saldo final previsto** parte do dinheiro que está nas contas agora e acrescenta apenas o que falta receber, descontando apenas o que falta pagar. Toque em **Como calculamos** para ver cada parcela.

Exemplo para conferir: previsão de renda de R$ 3.000, recebimento parcial de R$ 1.500, despesa paga de R$ 400, fixa pendente de R$ 800 e fatura pendente de R$ 600. O resultado do mês é R$ 1.200. Com conta iniciada em zero, o saldo atual é R$ 1.100; faltam R$ 1.500 a receber e R$ 1.400 a pagar, então o saldo final previsto também é R$ 1.200.

Outros pontos para a revisão:

1. Sem renda, o percentual comprometido aparece como “Não se aplica sem renda”; um resultado negativo continua visível.
2. Renda extra aumenta o resultado. Um recebimento parcial vinculado mantém só a diferença como previsão; se for marcado como concluído, a diferença deixa de entrar no cálculo.
3. Ao refinanciar R$ 400 de uma fatura de R$ 1.000 após pagar R$ 600, o resultado do mês original considera R$ 600 da fatura. O gráfico continua mostrando R$ 1.000 em compras; as parcelas e encargos entram nos meses futuros.
4. Fixas e faturas antigas ainda não pagas aparecem como **Pendências de meses anteriores** no saldo final previsto, sem serem lançadas como novo gasto do mês.
5. No mês passado, o saldo exibido é o saldo histórico ao fim daquele mês. Nos meses futuros, o saldo previsto acumula recebimentos e pagamentos pendentes desde o mês atual; despesas avulsas futuras ainda não lançadas não entram.

Esta revisão é local. A E08 foi enviada ao GitHub, mas nenhum push da E09 foi feito.

Verificação: 55 testes da API aprovados; análise do código Python, checagem TypeScript e exportação web aprovadas. A prévia local está em http://localhost:8081/ com a API E09 ativa.
