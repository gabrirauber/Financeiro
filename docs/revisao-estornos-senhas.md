# Revisão — estornos e campos de senha

Alterações locais para revisão. Envio ao GitHub, publicação da API e instalação de um novo APK aguardam autorização após o review.

## Estorno de uma cobrança antiga

Em Cartões, abra a fatura atual ou de um mês anterior e use **Registrar estorno** na parcela original. Informe o valor (integral ou parcial), a data em que recebeu o crédito e a fatura que recebeu o crédito, atual ou próxima. A data do recebimento deve estar no mês corrente e não pode ser futura.

A compra, a fatura e o pagamento originais permanecem no histórico. O novo registro é um crédito no mesmo cartão, vinculado à parcela original. O saldo bancário não muda e o crédito não é receita. Outras parcelas de uma compra parcelada não são canceladas automaticamente: cada cobrança efetivamente devolvida tem seu próprio estorno.

O saldo a pagar da fatura considera o crédito. Se ele exceder o saldo, a sobra permanece no cartão e abate faturas seguintes, inclusive na projeção. O relatório PDF identifica estornos, crédito anterior e saldo de crédito. O gráfico de categorias preserva o consumo original.

O servidor limita a soma dos estornos ao valor da parcela, verifica o espaço financeiro, impede destino já pago e torna a repetição da mesma solicitação idempotente. Compras com estorno registrado ficam protegidas contra edição/exclusão. Alterações que afetariam créditos anteriores a faturas posteriores já pagas exigem desfazer primeiro esses pagamentos.

A migração `e15_card_refunds` cria somente a tabela de estornos e atualiza a versão esperada pelo diagnóstico. A atualização deve executar `alembic upgrade head` antes de iniciar a API nova.

## Senhas

Cadastro: confirmação obrigatória e comparação antes do envio. Cadastro, login e definição de nova senha: botão de olho para mostrar/ocultar cada campo, inicialmente oculto. Trocar entre cadastro e login limpa os campos.

## Roteiro de revisão

1. No cadastro, preencher senhas diferentes e confirmar a mensagem de divergência. Testar mostrar/ocultar nos dois campos e no login.
2. Em uma fatura anterior, registrar estorno parcial e conferir que o pagamento original foi preservado.
3. Conferir o crédito na fatura de destino e o novo saldo a pagar.
4. Conferir sobra de crédito em faturas seguintes, sem aumento no saldo bancário.
5. Gerar o relatório e conferir os créditos discriminados.

## Recuperação por e-mail

O mecanismo SMTP existente permanece aguardando a escolha do remetente pelo usuário. Nenhuma credencial foi configurada e nenhum e-mail real foi enviado nesta alteração.

## Validação

Suíte completa: **76 testes passaram**, incluindo a migração em PostgreSQL. TypeScript e Ruff aprovados. Testes de API incluem histórico pago, estornos parciais, repetição de solicitação, limite por parcela, isolamento de espaços, crédito excedente, quitação pelo valor líquido, proteção de faturas pagas, preservação de outras parcelas e relatório PDF. A suíte completa também valida upgrade/downgrade e comparação do esquema com os modelos em PostgreSQL local descartável.

Correção de acesso: Registrar estorno também aparece no formulário de correção da compra. Compras antigas na fatura atual podem receber crédito nessa mesma fatura, se não estiver paga.
