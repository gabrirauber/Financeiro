# Revisão da E07 — pagamento parcial e faturas parceladas

Branch local: `etapa/07-pagamento-parcial`. Base: E06 (`b55a685`). Sem push da E07 antes do code review.

## Como conferir

1. Abra http://localhost:8081/, entre no seu espaço e acesse **Cartões**. Escolha uma fatura aberta e toque em **Antecipar pagamento**. Selecione a conta bancária e informe um valor até o saldo atual da fatura. O valor sai da conta e reduz o saldo da fatura imediatamente.
2. Confira que a fatura permanece aberta até o fechamento. Novas compras do ciclo ainda entram nela e aumentam o saldo. Exemplo: fatura de R$ 1.000, antecipação de R$ 600 e nova compra de R$ 100 deixam R$ 500 a pagar. Repetir o mesmo envio não duplica o débito. Uma correção de compra não pode reduzir o total da fatura abaixo do que já foi antecipado.
3. Se a antecipação quitar o total, a fatura continua aberta para novas compras; quando fechar sem saldo, aparecerá **Quitada por antecipações**. Depois do fechamento, novas compras e correções nela ficam bloqueadas.
4. Para uma fatura fechada ainda com saldo, use **Pagar saldo** ou **Pagar parcialmente e parcelar restante**. Apenas o saldo após as antecipações é cobrado ou financiado. Informe os juros e encargos totais e o número de parcelas futuras; a tela mostra a composição antes de confirmar.
5. Cancele o formulário e confira que saldo e fatura não mudaram. Reabra e confirme. Exemplo sem antecipação: fatura de R$ 1.000, pagamento de R$ 600, encargos de R$ 40 em duas parcelas: sai R$ 600 agora e entram duas parcelas de R$ 220 nas faturas seguintes.
6. A fatura original passa a indicar pagamento parcial e mostra o valor pago, o principal financiado e os encargos. As compras originais permanecem no histórico. Navegue pelos próximos meses no **Resumo**: **Faturas parceladas** aparece separadamente, com principal e encargos. A seção de consumo mostra compras e despesas novas; principal refinanciado não é nova compra.
7. Nas faturas futuras, as parcelas financiadas entram no total a pagar. Pagar integralmente uma dessas faturas reduz o caixa uma vez.

Um segundo envio do mesmo pagamento parcial devolve a operação existente sem outro débito ou novas parcelas. Um envio diferente para a mesma fatura é rejeitado. O pagamento parcial, a saída de caixa e as parcelas futuras são gravados juntos.

## Limites desta etapa

O gráfico mostra compromissos mensais e consumo novo em linhas distintas. A fórmula do resultado e provisionamento segue pendente em DEC-02 para E09; ela não foi alterada nesta etapa. Recorrências e rendas previstas ficam para E08; PDF fica para etapa posterior. A API e as migrações `e07_financing` e `e07_invoice_advances` estão locais; Railway não recebeu deploy.

Validações: 41 testes da API com PostgreSQL descartável, Ruff, TypeScript e exportação do bundle Android. Android físico ainda precisa de validação.
