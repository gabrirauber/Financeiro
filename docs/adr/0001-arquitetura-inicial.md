# ADR-0001 — Arquitetura inicial

Data: 07/10/2026.

Status: tecnologias aprovadas pelo cliente; organização interna proposta para revisão na E00.

## Contexto

Aplicativo Android conectado à internet, com dados compartilhados por usuários autenticados, regras de cartão, recorrências, provisionamento e relatório PDF. Prioridade: lançamento ágil e desenvolvimento incremental acompanhável.

## Decisão

- Cliente: React Native, Expo e TypeScript.
- Servidor: Python com FastAPI, em uma única API organizada por módulos.
- Persistência: PostgreSQL, SQLAlchemy e migrações Alembic.
- Hospedagem: API e PostgreSQL no Railway. O aplicativo é instalado no Android.
- Repositório único com organização futura `apps/mobile`, `apps/api` e `docs`.
- Regras financeiras e autorização executadas no servidor. O cliente apresenta os dados e valida campos para melhorar a experiência, sem substituir validações do servidor.
- Rotinas recorrentes usam a mesma lógica de domínio da API e execução agendada no servidor; não dependem de o app estar aberto. O mecanismo de agendamento será escolhido em E02/E08.

## Convenções propostas

- Valores em reais, usando representação decimal exata no servidor e banco; transporte sem perda de centavos. Contrato detalhado da API será definido antes da integração.
- Um espaço financeiro é a fronteira de acesso aos dados. Cada operação exige usuário autenticado e participação ativa; o cliente não escolhe permissões.
- Datas financeiras são datas civis do espaço; eventos de auditoria têm instante registrado. Fuso inicial proposto: `America/Sao_Paulo`.
- Pagamentos, transferências e refinanciamentos devem ser atômicos. Reenvios da mesma operação não podem duplicar efeitos.
- Saldo é derivado do saldo inicial e movimentos válidos; projeção não altera o caixa realizado.
- Nenhuma senha em texto puro; mecanismo de autenticação, recuperação e armazenamento de sessão será detalhado em E03.
- Migrações e verificações acompanham a funcionalidade implementada. Ambientes de teste e produção usam dados separados.

## Consequências

O projeto usa duas linguagens e exige contrato claro entre cliente e API. A centralização das regras permite que usuários compartilhados recebam os mesmos cálculos. A primeira versão depende da disponibilidade da internet e do servidor.

Não estão escolhidos nesta etapa: versões de pacotes, biblioteca de gráficos, biblioteca de PDF, serviço de e-mail, estratégia detalhada de sessão e mecanismo de agendamento. Não há infraestrutura provisionada nem custos contratados.

## Processo aprovado

Executar apenas a etapa autorizada, registrar commits locais e apresentar alterações para code review do cliente **antes de qualquer push**. A E01 aguarda autorização própria. Remoto Git ainda não definido; não criar repositório remoto automaticamente.
