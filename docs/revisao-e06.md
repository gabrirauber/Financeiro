# Revisão da E06 — cartões, parcelas e faturas

Branch local: `etapa/06-cartoes-faturas-parcelas`. Base: E05 (`9119e13`). **Não enviar ao GitHub antes do code review.**

## Conferir no aplicativo

1. Abra a prévia em http://localhost:8081/, entre no espaço e cadastre uma conta bancária na aba **Contas**.
2. Em **Cartões**, cadastre um cartão com dia de fechamento e vencimento. O checkbox decide se uma compra no próprio dia do fechamento vai para a próxima fatura.
3. Use **+** e escolha **Crédito**. Selecione cartão, categoria e subcategoria, informe o valor e a quantidade de parcelas. A primeira fatura é calculada automaticamente; pode ser informada manualmente para adiar o início.
4. Confira as faturas na aba **Cartões** e navegue pelos meses no **Resumo**. Cada parcela aparece no mês da respectiva fatura, inclusive aberta e depois de paga. A compra não reduz o saldo bancário nesse momento.
5. Para uma compra antiga, ative **Lançar somente parcelas restantes**, informe o mês da primeira fatura restante e o número dessa parcela. Nenhuma parcela passada é recriada.
6. Uma fatura fechada pode ser paga integralmente por conta bancária. O extrato registra uma única saída e o resumo não duplica a despesa.
7. Abra uma parcela não paga e corrija o valor total restante e a observação. O valor é redistribuído entre parcelas atuais e futuras ainda não pagas. Faturas pagas e meses anteriores ficam intactos.

Exemplo de ciclo: fechamento dia 10, vencimento dia 20. Compra dia 9 entra na fatura de outubro; dia 11, na de novembro. No dia 10, o checkbox define outubro ou novembro. Em meses curtos, dias 29–31 são ajustados ao último dia real.

## Estado e limites

O pagamento parcial com financiamento fica para E07; recorrências, renda prevista e provisionamento para as etapas seguintes. A fatura só pode ser paga depois do fechamento. Correção em série mantém a quantidade de parcelas; mudança individual e exclusão de compra no crédito ainda não fazem parte desta etapa. A API e a migração `e06_cards` estão locais; Railway não recebeu deploy.

Validações: 34 testes da API com PostgreSQL de testes, Ruff, TypeScript e exportação do bundle Android. A experiência em Android físico ainda precisa de validação antes de publicar.
