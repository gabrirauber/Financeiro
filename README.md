# Financeiro

Aplicativo Android para controle financeiro pessoal e compartilhado. Na E07, acesso, espaços, contas, receitas, despesas, cartões, faturas e pagamentos parciais usam PostgreSQL. A E07 está local para revisão antes do push.

## Documentação

- [Modelagem e diagramas](docs/modelagem.md)
- [Plano de desenvolvimento e commits](docs/plano-desenvolvimento.md)
- [Requisitos e critérios de aceite](docs/criterios-aceite.md)
- [Decisão de arquitetura](docs/adr/0001-arquitetura-inicial.md)
- [Decisões pendentes](docs/decisoes-pendentes.md)
- [Revisão da E00](docs/revisao-e00.md)
- [Executar o protótipo](apps/mobile/README.md)
- [Revisão da E05](docs/revisao-e05.md)
- [Revisão da E06](docs/revisao-e06.md)
- [Revisão da E07](docs/revisao-e07.md)
- [Revisão da E01](docs/revisao-e01.md)

## Fluxo de trabalho

Uma etapa autorizada por vez, com commits locais pequenos. **O cliente faz code review antes de qualquer push.** Aprovar uma etapa ou criar um commit não autoriza envio ao remoto, publicação nem início da próxima etapa.

Instruções de execução e verificações estão nos READMEs do aplicativo e da API. A E07 permanece local até o review e autorização de push.

## Histórico: E02 — base técnica

API e conexão local preparadas para review. Consulte [revisão E02](docs/revisao-e02.md), [API](apps/api/README.md) e [Railway](docs/railway-e02.md). Sem push ou publicação; Android físico pendente.

## E03 — acesso e compartilhamento

Implementação local pronta para revisão: [roteiro E03](docs/revisao-e03.md) e [decisão de sessões](docs/adr/0002-identidade-sessoes.md). Cadastro, login e espaços são reais; dados financeiros ainda simulados. E03 sem push, aguardando review. Os status anteriores descrevem as entregas históricas.
