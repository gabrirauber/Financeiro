# Correção — consultas simultâneas e falhas temporárias

## Diagnóstico confirmado em produção

Em 22/10/2026, os logs da API mostraram HTTP 503 na projeção mensal. O PostgreSQL registrou `canceling statement due to statement timeout`, com contexto `while locking tuple ... in relation "workspaces"`, na instrução `SELECT ... FROM workspaces ... FOR UPDATE`. A consulta aguardava o bloqueio do espaço financeiro usado pela geração de ocorrências.

## Alterações

- A geração mensal continua protegida pelo bloqueio e pelas chaves únicas. Cada mês é confirmado antes de começar o próximo.
- O cálculo da projeção começa depois da liberação do bloqueio, em uma transação PostgreSQL somente de leitura, com isolamento REPEATABLE READ. Assim, receitas, despesas e saldos pertencem à mesma visão dos dados mesmo quando outra requisição grava uma alteração.
- A busca das ocorrências existentes é feita em lote, evitando uma consulta por regra/renda. Contas fixas são inseridas em lote quando não há lançamento de cartão exigindo flush.
- Uma falha temporária na atualização da sessão preserva o espaço já carregado. Sessão inválida continua encerrando o acesso; uma atualização bem-sucedida sem participação continua retirando o espaço.
- Somente consultas GET podem repetir uma vez após falha de conexão ou HTTP 502/503/504. Operações de escrita e login nunca são reenviados automaticamente. Erros de gateway com corpo HTML preservam o código HTTP e a mensagem de indisponibilidade.

O limite de três segundos por instrução SQL foi preservado. Não há migração de esquema.

## Verificação

Dois testes novos usam PostgreSQL real e requisições concorrentes: liberação do bloqueio durante o cálculo, consistência do snapshot com gravação concorrente, e geração mensal sem duplicidade. Testes do cliente cobrem repetição limitada de consultas, ausência de repetição nas escritas, sessão expirada e respostas HTML do gateway.

Validação concluída: **78 testes da API** passaram no PostgreSQL local descartável; **9 testes do cliente** passaram. TypeScript e Ruff aprovados.

## Publicação

Alterações locais para revisão. A correção principal exige publicar a API. O tratamento das falhas temporárias no cliente exige também um novo APK. A alteração anterior que move Registrar estorno para as opções da compra permanece no mesmo arquivo de trabalho.
