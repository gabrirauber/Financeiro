# Revisão da E07 — pagamento parcial e faturas parceladas

Branch local: `etapa/07-pagamento-parcial`. Base: E06 (`b55a685`). Sem push da E07 antes do code review.

## Como conferir

1. Abra http://localhost:8081/, entre no seu espaço e acesse **Cartões**. Escolha uma fatura já fechada. Uma fatura aberta ainda não pode ser paga.
2. Toque em **Pagar parcialmente e parcelar restante**. Escolha a conta bancária, informe quanto será pago agora, os juros e encargos totais e o número de parcelas futuras. A tela mostra a composição antes de confirmar.
3. Cancele o formulário e confira que saldo e fatura não mudaram. Reabra e confirme. Exemplo: fatura de R$ 1.000, pagamento de R$ 600, encargos de R$ 40 em duas parcelas: sai R$ 600 agora e entram duas parcelas de R$ 220 nas faturas seguintes.
4. A fatura original passa a indicar pagamento parcial e mostra o valor pago, o principal financiado e os encargos. As compras originais permanecem no histórico.
5. Navegue pelos próximos meses no **Resumo**. **Faturas parceladas** aparece separadamente, com principal e encargos. A seção de consumo mostra compras e despesas novas; principal refinanciado não é nova compra.
6. Nas faturas futuras, as parcelas financiadas entram no total a pagar. Pagar integralmente uma dessas faturas reduz o caixa uma vez.

Um segundo envio do mesmo pagamento parcial devolve a operação existente sem outro débito ou novas parcelas. Um envio diferente para a mesma fatura é rejeitado. O pagamento parcial, a saída de caixa e as parcelas futuras são gravados juntos.

## Limites desta etapa

O gráfico mostra compromissos mensais e consumo novo em linhas distintas. A fórmula do resultado e provisionamento segue pendente em DEC-02 para E09; ela não foi alterada nesta etapa. Recorrências e rendas previstas ficam para E08; PDF fica para etapa posterior. A API e a migração `e07_financing` estão locais; Railway não recebeu deploy.

Validações: 38 testes da API com PostgreSQL descartável, Ruff, TypeScript e exportação do bundle Android. Android físico ainda precisa de validação.
