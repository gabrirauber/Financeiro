# Financeiro API — E07

Python 3.13, FastAPI, SQLAlchemy, PostgreSQL e Alembic. A API mantém usuários, espaços compartilhados, contas, receitas, transferências, categorias, subcategorias, despesas pagas, cartões, parcelas, faturas, antecipações e pagamentos parciais.

## Desenvolvimento local

1. Na raiz, copie `.env.example` para `.env` e escolha a senha local.
2. Com Docker disponível, execute `docker compose up -d postgres`. Porta local: 55432. Alternativamente use PostgreSQL 17 instalado, em banco dedicado ao projeto; não use banco de outro sistema.
3. Em `apps/api`, execute:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Ajuste DATABASE_URL se alterou a senha ou porta do PostgreSQL.
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Linux: usar `.venv/bin/python` em lugar de `.venv/Scripts/python.exe`. Executar comandos a partir de `apps/api` para localizar `.env` e `alembic.ini`. `requirements.txt` fixa todas as dependências de execução; `requirements-dev.txt` inclui também as ferramentas de verificação, com as mesmas versões de runtime.

No navegador, `/docs` expõe o contrato em desenvolvimento. `/health/live` verifica o processo; `/health/ready` consulta PostgreSQL e exige a migração inicial. Retorna HTTP 200 quando pronto ou 503 com resposta genérica quando indisponível. A API não cria tabelas automaticamente na inicialização.

## Testes

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -q
```

Para incluir a integração real de migrações, crie um **banco descartável exclusivo**, com nome terminado em `_test` e sem tabelas de outros sistemas:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://financeiro:financeiro_local@127.0.0.1:55432/financeiro_test'
.venv/Scripts/python.exe -m pytest -q
```

O teste faz upgrade, repetição, comparação com os modelos, downgrade e upgrade novamente. Sem `TEST_DATABASE_URL`, o teste de integração fica marcado como ignorado; isso não comprova a migração. Não apontar essa variável para desenvolvimento compartilhado ou produção.

## Instância usada nesta sessão

PostgreSQL 17 local isolado em `.cache/postgres-e02`, bind exclusivo `127.0.0.1:55432`, bancos `financeiro` e `financeiro_test`. Autenticação `trust` apenas nessa instância de teste local, sem dados reais; não é configuração de produção. Os serviços PostgreSQL existentes não foram alterados. Compose é alternativa e não deve usar a mesma porta simultaneamente.

Parar a instância criada nesta sessão (PowerShell na raiz):

```powershell
& 'C:/Program Files/PostgreSQL/17/bin/pg_ctl.exe' -D "$PWD/.cache/postgres-e02" stop -m fast
```

Não remover o volume/pasta para reiniciar a API. Publicação e variáveis do Railway estão descritas em `docs/railway-e02.md`, na raiz do repositório.

## Histórico: E03 — identidade

A API agora inclui /auth/register, /auth/login, /auth/me, /auth/logout, /workspaces e rotas de convites/participantes. Execute alembic upgrade head antes de iniciar. O diagnóstico exige o esquema E03. Para revisar, consulte docs/revisao-e03.md na raiz.

Os testes de identidade removem registros de tabelas de identidade no banco TEST_DATABASE_URL: use exclusivamente banco descartável terminado em _test. Nunca use uma base compartilhada ou com dados reais.

### Recuperação por e-mail

Configurar SMTP_HOST, SMTP_PORT (padrão 465), SMTP_FROM, SMTP_USER, SMTP_PASSWORD e PASSWORD_RESET_URL no ambiente do servidor. O transporte usa SMTP_SSL. Sem provedor configurado, o endpoint informa indisponibilidade; não imprime links/tokens nos logs.

Desenvolvimento web: PASSWORD_RESET_URL=http://localhost:8081/. Android instalado: PASSWORD_RESET_URL=financeiro://reset. Também é possível URL HTTPS pública que hospede a interface de recuperação. O esquema nativo exige build instalado; Expo Go e Android físico ainda precisam de validação. Nenhuma mensagem real foi enviada na implementação.
