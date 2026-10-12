# Revisão da E10 — relatório mensal

No **Resumo**, escolha o mês com as setas e abra **Relatório do mês**. Marque **Incluir lançamentos detalhados** se quiser a lista de despesas, compras no cartão e fixas pendentes. Na prévia web, **Baixar PDF** salva o arquivo; no Android, **Gerar e compartilhar PDF** abre a lista de aplicativos de destino.

O arquivo traz renda recebida e prevista, resultado do mês, saldo final previsto, gastos por categoria, faturas, principal refinanciado, parcelas com encargos e saldos por conta. Meses anteriores usam o saldo da data final daquele mês. Os números da visão geral vêm do mesmo cálculo do painel. O relatório é gerado quando solicitado e não é armazenado no servidor.

Para conferir a leitura, veja [um PDF com dados fictícios](../output/pdf/exemplo-e10.pdf). No app, compare o resultado e o saldo do PDF com **Saúde do mês** no período selecionado. Teste também um mês sem lançamentos, um mês passado e um relatório detalhado com muitas despesas.

O compartilhamento nativo precisa ser conferido em um aparelho Android. Nenhum push da E10 foi feito; os commits locais ficam disponíveis para code review.

Verificação local: 60 testes da API passaram, incluindo arquivo vazio, isolamento entre usuários, saldos históricos, refinanciamento, acentos e múltiplas páginas. A análise do código Python, a checagem TypeScript e os pacotes web e Android passaram. O PDF de exemplo foi renderizado e conferido visualmente. A API local responde como E10 e a prévia web está em http://localhost:8081/.
