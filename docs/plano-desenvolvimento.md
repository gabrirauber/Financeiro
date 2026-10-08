# Plano de desenvolvimento e commits

Data: 07/10/2026. Status: E00 autorizada e preparada para revisão; implementação do aplicativo não iniciada.

## Objetivo e forma de acompanhamento

Construir o aplicativo em entregas pequenas, demonstráveis e vinculadas à [modelagem](modelagem.md). O cliente deve conseguir acompanhar o que está sendo construído antes de autorizar a etapa seguinte.

**A autorização para executar uma etapa vale somente para aquela etapa.** Ao concluir a entrega, apresentar o resultado e aguardar a revisão do cliente. Não iniciar automaticamente outra etapa. Se uma etapa ficar grande, dividir antes de executá-la. Correções solicitadas na revisão pertencem à mesma etapa.

Cada etapa seguirá este ciclo:

1. Apresentar escopo, critérios de aceite e commits previstos; esclarecer decisões de negócio pendentes que afetem a entrega.
2. Implementar a menor entrega completa, incluindo interface, API e persistência quando aplicável.
3. Executar verificações proporcionais à mudança e conferir as regras financeiras relevantes.
4. Criar commits pequenos e coerentes, incluindo testes e migrações da funcionalidade correspondente.
5. Entregar um roteiro de teste no Android, telas ou demonstração, resultados das verificações e relação dos commits reais.
6. Aguardar o code review do cliente antes de qualquer push. Envio ao remoto exige autorização explícita após a revisão; aprovação de uma etapa não autoriza automaticamente push nem publicação.
7. Aguardar o cliente testar e solicitar ajustes ou autorizar expressamente a próxima etapa.

A demonstração não deve depender de ler código. Na fase de protótipo, identificar dados fictícios; nas entregas integradas, demonstrar persistência ao fechar e reabrir o aplicativo. Funcionalidades ainda não implementadas devem estar claramente identificadas.

## Tecnologias aprovadas

| Camada | Tecnologia |
|---|---|
| Aplicativo Android | React Native, Expo e TypeScript |
| API | Python e FastAPI |
| Banco de dados | PostgreSQL |
| Persistência e migrações | SQLAlchemy e Alembic |
| Hospedagem da API e banco | Railway |

Uma única API organizada por módulos. Estrutura proposta: `apps/api`, `apps/mobile` e `docs`. Versões e bibliotecas complementares serão fixadas na preparação técnica, depois de conferir compatibilidade. O aplicativo é instalado no Android; não é hospedado como página web no Railway.

## Etapas e entregas

### E00 — Especificações verificáveis

**Entrega:** requisitos identificados, exemplos de cálculo aprovados e lista clara do que pertence à primeira versão.

**Commits previstos:**

- `docs: registrar modelagem e plano de desenvolvimento`
- `docs: definir criterios de aceite e decisoes de arquitetura`

**Aceite:** cada funcionalidade da modelagem tem um identificador e ao menos um cenário verificável. Regras ambíguas são resolvidas antes da implementação correspondente. As tecnologias aprovadas ficam registradas em uma decisão de arquitetura.

**Revisão do cliente:** conferir os exemplos e aprovar as regras. Não há código de aplicativo nesta etapa.

### E01 — Protótipo navegável no Android

**Entrega:** interface com dados fictícios para revisar a experiência antes de construir os cálculos. Incluir painel, categoria/subcategoria, nova despesa e navegação para contas e cartões.

**Commits previstos:**

- `chore(mobile): iniciar aplicativo Expo com TypeScript`
- `feat(mobile): criar prototipo do painel e fluxo de despesa`

**Aceite:** abrir no Android, navegar pelo gráfico e preencher a despesa com categoria e subcategoria obrigatórias e data atual preenchida. Simulações devem ser identificadas e não prometer salvamento real.

**Revisão do cliente:** testar disposição, tamanho dos elementos, campos e quantidade de toques. Ajustar o visual nesta etapa.

### E02 — Base técnica e primeira conexão

**Entrega:** API, PostgreSQL local/de desenvolvimento, primeira migração, configuração de ambientes e aplicativo conectado a um endpoint de diagnóstico. Com autorização para publicar o ambiente de teste, disponibilizar a API no Railway.

**Commits previstos:**

- `chore(api): iniciar FastAPI PostgreSQL e migracoes`
- `chore: configurar verificacoes e ambientes de desenvolvimento`
- `feat(mobile): conectar aplicativo a API de teste`
- `chore(deploy): preparar publicacao de teste no Railway`

**Aceite:** configuração reproduzível documentada; migração aplicada em banco vazio; Android alcança a API; ausência de internet ou falha do servidor resulta em mensagem compreensível; segredos não entram no repositório. Registrar o que foi efetivamente publicado e o que depende de acesso ao Railway.

**Revisão do cliente:** abrir o app conectado e conferir o endereço do ambiente de teste. Acesso à conta de hospedagem e eventuais custos precisam estar resolvidos antes da publicação.

### E03 — Login e espaço compartilhado

**Entrega:** cadastro, login, saída, sessão persistida, criação do espaço, entrada por código e administração dos participantes.

**Commits previstos:**

- `feat(auth): implementar cadastro login e sessao`
- `feat(espacos): criar espaco e controlar participacoes`
- `feat(convites): compartilhar espaco por codigo`

**Aceite:** duas pessoas com logins próprios acessam o mesmo espaço por convite; uma terceira pessoa sem participação não consegue consultar nem alterar seus dados. Participante não administra convites ou membros; remoção revoga acesso. Testar código inválido, expirado e reutilizado conforme a política aprovada. Definir recuperação de senha antes da liberação para uso real.

**Revisão do cliente:** testar entrada com dois usuários e compartilhamento por código.

### E04 — Contas, receitas e transferências

**Entrega:** contas bancárias/dinheiro, saldo inicial, receita recebida, transferência e extrato simples.

**Commits previstos:**

- `feat(contas): cadastrar contas com saldo inicial`
- `feat(receitas): registrar recebimentos e atualizar saldo`
- `feat(transferencias): movimentar valores entre contas`

**Aceite:** conta A com R$ 1.000 recebe R$ 500 e transfere R$ 200 à conta B inicialmente zerada: A termina com R$ 1.300, B com R$ 200 e o consolidado com R$ 1.500. Falha na transferência não pode salvar apenas um lado. Aplicar e testar as restrições do mês corrente e o isolamento por espaço desde esta entrega.

**Revisão do cliente:** cadastrar suas contas de teste, lançar receita e conferir os saldos ao reabrir o app.

### E05 — Despesas pagas e gráfico real

**Entrega:** categorias e subcategorias pré-cadastradas e personalizáveis, despesa paga, consulta mensal e gráfico conectado aos dados reais.

**Commits previstos:**

- `feat(categorias): cadastrar categorias e subcategorias do espaco`
- `feat(despesas): registrar editar e excluir despesas pagas`
- `feat(painel): exibir gastos reais por categoria e subcategoria`

**Aceite:** despesa de R$ 80 reduz o saldo da conta em R$ 80 e aparece uma vez no gráfico; edição para R$ 90 altera somente a diferença; exclusão recompõe o saldo. Bloquear edição e exclusão de mês anterior. Categoria e subcategoria obrigatórias; observação opcional. Categoria usada no histórico não pode apagar lançamentos existentes.

**Revisão do cliente:** validar a agilidade do lançamento. Este é o primeiro marco utilizável para controle de dinheiro e débito, ainda sem cartão e provisionamento completo.

### E06 — Cartões, parcelas e pagamento integral

**Entrega:** cadastro do cartão, fechamento configurável, compras à vista e parceladas, parcelamentos antigos, faturas e pagamento integral.

**Commits previstos:**

- `feat(cartoes): cadastrar cartoes e calcular ciclos de fatura`
- `feat(parcelas): distribuir compras e cadastrar parcelas restantes`
- `feat(faturas): consultar e pagar fatura integral`

**Aceite:** R$ 600 em três vezes gera R$ 200 em cada fatura; testar compras antes, no dia e depois do fechamento, ambas as opções do checkbox, fevereiro e virada do ano. R$ 100 em três vezes soma exatamente R$ 100. Compra não reduz caixa; pagamento reduz caixa sem duplicar despesa. Parcelamento antigo registra somente o restante e não altera o saldo inicial por pagamentos passados.

**Revisão do cliente:** simular um cartão seu, conferir datas e pagar uma fatura de teste.

### E07 — Pagamento parcial e financiamento da fatura

**Entrega:** pagamento parcial com lançamento guiado do restante, juros informados manualmente, parcelas futuras e identificação “Faturas parceladas”.

**Commits previstos:**

- `feat(faturas): registrar pagamento parcial com refinanciamento`
- `feat(painel): identificar parcelas de faturas financiadas`

**Aceite:** fatura de R$ 1.000 paga em R$ 600, com R$ 40 de encargos sobre os R$ 400 restantes, gera duas parcelas futuras de R$ 220. Saída atual é R$ 600. Cancelar antes da confirmação não modifica caixa nem encerra fatura. Repetir a mesma confirmação não duplica o pagamento. Histórico preserva compras originais e relatórios distinguem principal refinanciado de consumo novo.

**Revisão do cliente:** testar o fluxo e conferir o gráfico nos meses seguintes.

### E08 — Recorrências e receitas previstas

**Entrega:** despesas fixas fora do cartão, recorrências no cartão, renda prevista por pessoa e lembrete de recebimento.

**Commits previstos:**

- `feat(recorrencias): gerar despesas fixas e compras recorrentes`
- `feat(previsoes): cadastrar rendas e vincular recebimentos`
- `feat(lembretes): solicitar receita na data prevista`

**Aceite:** despesa fixa prevista de R$ 100 paga por R$ 110 passa a contribuir com R$ 110, uma única vez. Executar geração mensal duas vezes não duplica registros; geração independe do app aberto. Receita registrada pelo lembrete reduz a previsão vinculada e aumenta o saldo uma única vez. “Ainda não recebi” retorna no dia seguinte. Alterações em séries preservam meses anteriores.

**Revisão do cliente:** simular as datas com dados de teste e validar a cobrança da receita e os ajustes de valor.

### E09 — Provisionamento e saúde do mês

**Entrega:** resultado mensal, saldo final previsto, renda comprometida e navegação por mês, explicando quais valores compõem cada cálculo.

**Commits previstos:**

- `feat(provisionamento): calcular resultado e saldo final previsto`
- `feat(painel): apresentar saude financeira e composicao dos valores`

**Aceite:** cenário simples: renda mensal prevista de R$ 3.000, despesas pagas de R$ 400, fixas pendentes de R$ 800 e fatura pendente de R$ 600 produzem resultado de R$ 1.200. Se o saldo atual é R$ 1.100 e ainda faltam receber R$ 1.500 vinculados à previsão, o saldo final previsto é R$ 1.200. Testar também renda zero, déficit, receita extra, recebimento diferente da previsão e refinanciamento conforme as decisões de E00. Não descontar novamente pagamentos já refletidos no saldo.

**Revisão do cliente:** conferir os números com exemplos próprios. Este é o marco de conclusão das funcionalidades financeiras centrais.

### E10 — Relatório PDF e compartilhamento

**Entrega:** PDF mensal com resumo, categorias, faturas, financiamento, contas e detalhamento opcional; compartilhamento pelo Android.

**Commits previstos:**

- `feat(relatorios): gerar PDF mensal com resumo e detalhamento`
- `feat(mobile): compartilhar relatorio PDF no Android`

**Aceite:** valores do PDF coincidem com a consulta do mesmo período; mês passado usa saldo histórico; conferir visualmente páginas, textos longos, acentos, relatório vazio e relatório extenso. Testar geração e compartilhamento no aparelho. O usuário escolhe o destino do compartilhamento.

**Revisão do cliente:** abrir o PDF e avaliar utilidade, legibilidade e nível de detalhe.

### E11 — Validação integrada e primeira versão para uso

**Entrega:** versão candidata Android, ambiente de produção no Railway, instruções operacionais e registro de limitações conhecidas.

**Commits previstos:**

- `test: validar jornadas financeiras integradas`
- `chore(release): preparar Android e ambiente de producao`
- `docs: documentar instalacao operacao e recuperacao de dados`

**Aceite:** testar as jornadas completas com dois usuários, mês corrente/anterior, perda de conexão e reenvio de operações. Conferir migrações, logs sem dados sensíveis, armazenamento da sessão, recuperação de acesso e procedimento de backup/restauração demonstrado em ambiente de teste. Validar desempenho das telas principais no Android. Produção deve ter dados separados dos testes.

**Revisão do cliente:** testar a versão candidata e autorizar a liberação para uso. Publicação na Play Store, domínio e contratação de serviços não estão implícitos: APK de teste já atende à validação inicial.

## Regras de commits e acompanhamento

- Usar `docs`, `chore`, `feat`, `fix` e `test`, com escopo quando ajudar a identificar a mudança.
- Cada commit deve ter uma responsabilidade compreensível. Um commit pode incluir código, testes e migração da mesma funcionalidade; não adiar testes financeiros para a última etapa.
- As mensagens acima são uma previsão. Podem ser divididas conforme necessário, sem ampliar a etapa autorizada. Evitar um único commit para todo o aplicativo.
- Manter cada commit consistente e verificável; não incluir segredos, arquivos temporários ou alterações alheias à entrega.
- Quando Git estiver configurado, trabalhar em uma branch por etapa, como `etapa/05-despesas`. Revisar o diff antes do commit e apresentar hashes reais na entrega.
- Commit local, envio ao remoto e publicação são ações distintas. **O cliente deve fazer code review local antes de qualquer push.** Não enviar sequer a branch para abrir PR antes dessa revisão e autorização. Remoto ainda não informado; não criar nem associar um automaticamente. Depois de autorizado o push, usar PR se esse fluxo for adotado.
- Ao corrigir uma entrega já revisada, preferir um commit novo que deixe a alteração visível.

Modelo do relatório ao fim de cada etapa:

```text
Etapa:
O que mudou:
Como testar no Android:
Verificações executadas e resultados:
Commits criados:
Limitações ou decisões pendentes:
Status: aguardando revisão do cliente.
```

## Decisões a resolver na especificação, sem bloquear este plano

Antes de implementar as partes afetadas, documentar respostas e exemplos para:

- Receitas extras e valores recebidos diferentes da previsão: como atualizam o resultado mensal e quando uma previsão é considerada encerrada.
- Refinanciamento: reconciliar resultado por competência com saldo de caixa quando parte da fatura é transferida para meses futuros; explicitar a leitura do gráfico e do total entre meses.
- Edição no mês corrente: qual data rege a permissão em compras antigas com parcela atual, pagamentos e séries; como tratar correção de fatura já paga e dívidas pendentes de meses anteriores.
- Convites: validade, uso único, transferência da administração e saída do último administrador.
- Recuperação de senha e eventual serviço de e-mail para a versão de uso real.

Esses itens são detalhes de execução ainda não aprovados; não devem receber regras silenciosamente no código. As propostas e exemplos estão em [decisões pendentes](decisoes-pendentes.md), e sua cobertura em [critérios de aceite](criterios-aceite.md).

## Situação atual

- Modelagem inicial: documentada.
- Tecnologias: aprovadas pelo cliente.
- Plano: E00 autorizada; demais etapas aguardam autorização própria.
- Implementação: não iniciada.
- Git: inicializado localmente em 07/10/2026. Documentação original preservada no commit inicial; E00 na branch `etapa/00-especificacoes`. Sem remoto configurado e sem push.

A E00 está preparada para revisão documental e respostas às decisões pendentes. Ver [roteiro de revisão](revisao-e00.md). A E01 não foi iniciada.
