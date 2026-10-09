# Revisão da E04 — contas, receitas e transferências

Branch local: `etapa/04-contas-receitas-transferencias`. Base: E03 (`5d46197`). Nenhum push desta etapa foi feito.

## O que conferir

1. Abra a prévia em http://localhost:8081/, entre no seu usuário e abra um espaço financeiro.
2. Na aba **Contas**, cadastre a conta A com saldo inicial R$ 1.000,00 e a conta B com R$ 0,00.
3. Registre uma receita recebida de R$ 500,00 na A. O saldo da A deve ser R$ 1.500,00.
4. Transfira R$ 200,00 de A para B. Os saldos devem ficar A=R$ 1.300,00, B=R$ 200,00, total=R$ 1.500,00.
5. Toque em cada conta para ver o extrato. É possível corrigir ou excluir uma receita do mês corrente e corrigir ou desfazer uma transferência do mês corrente.
6. Recarregue a prévia: os saldos e o extrato devem permanecer.

O saldo inicial entra no caixa, mas não vira receita do mês. Transferências também não são receitas nem despesas. Os dois lados da transferência são gravados na mesma transação de banco. A API rejeita movimentos fora do mês corrente, datas anteriores ao cadastro da conta e acesso de quem não participa do espaço.

## Escopo visível

A aba **Contas** agora usa dados do servidor. O gráfico de gastos, o formulário de despesas e os cartões continuam como prévia com exemplos; essas funções entram nas etapas seguintes. Ao sair de um espaço, os dados de contas permanecem no servidor. A revisão no navegador funciona; a experiência no Android físico ainda precisa ser verificada antes da publicação. Railway não recebeu deploy.

## Validação

- API: 27 testes, incluindo migração de ida e volta, isolamento entre espaços, saldos, correções e transferência atômica.
- Ruff e TypeScript sem erros.
- Migração `e04_finance` aplicada ao PostgreSQL local; `/health/ready` responde E04.
- Prévia local disponível em http://localhost:8081/.

Para comparar o código: `git diff 5d46197..etapa/04-contas-receitas-transferencias`.

Aguardando o code review antes de qualquer push da E04.
