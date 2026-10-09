# Revisão da E05 — despesas pagas e gráfico real

Branch local: `etapa/05-despesas-pagas-grafico-real`. Base: E04 (`6e56463`). Sem push da E05.

## Como conferir no aplicativo

1. Atualize a prévia em http://localhost:8081/, entre e abra um espaço financeiro. Crie uma conta bancária com R$ 1.000 se necessário.
2. Abra **Gerenciar categorias e subcategorias**. As opções iniciais já aparecem; toque no campo Nova categoria para abrir Criar e Cancelar; crie uma categoria e sua subcategoria pelo campo equivalente. O menu ⋯ de cada item oferece Desativar ou Reativar, conforme o estado. O outro participante do mesmo espaço verá as mesmas opções.
3. Use o botão **+**. Lance R$ 80 em Pix ou débito, escolha categoria, subcategoria e conta. A data começa em hoje; observação é opcional.
4. Confira o gráfico, toque na categoria para ver a subcategoria e abra a aba **Contas**: o saldo terá caído R$ 80.
5. Edite a despesa para R$ 90. Gráfico, lista e saldo devem refletir somente a diferença de R$ 10.
6. Exclua a despesa. O valor volta ao saldo e ela desaparece da lista e do gráfico.
7. Recarregue o aplicativo e troque o mês consultado. Os dados permanecem no servidor e meses sem despesas aparecem vazios.

Dinheiro usa conta do tipo dinheiro; Pix e débito usam conta bancária. A API bloqueia novas despesas, edições e exclusões fora do mês corrente, bem como datas anteriores ao cadastro da conta. Desativar categorias ou subcategorias usadas preserva o histórico; é possível reativá-las.

## Estado e limites

O resumo, categorias e despesas pagas agora são reais. A tela de cartões continua ilustrativa. Cartões, parcelas e faturas permanecem na E06 conforme revisão do cliente. Na E06, Gastos do mês incluirá compras no crédito pelo mês da fatura, inclusive aberta, e as manterá após o fechamento e pagamento. O pagamento não repetirá a despesa no gráfico. Provisionamento fica para as etapas seguintes. O backend local recebeu a migração `e05_expenses`, que também cadastrou categorias iniciais nos espaços já existentes. Railway não recebeu deploy nesta etapa.

Validações concluídas: 31 testes da API com PostgreSQL descartável, comparação de migração com os modelos, Ruff, TypeScript, exportação do bundle Android e jornada visual de cadastro, categoria, lançamento, correção, exclusão e persistência. O aplicativo ainda precisa de teste em Android físico antes de publicar.

Compare os arquivos por `git diff 6e56463..etapa/05-despesas-pagas-grafico-real`. A etapa aguarda code review antes do push.
