# Revisão da E02

Data: 08/10/2026. Implementação local preparada para review. Publicação Railway e validação em Android físico pendentes. E03 não iniciada.

## Entrega

- API FastAPI com diagnóstico do processo e prontidão do PostgreSQL.
- SQLAlchemy e migração Alembic inicial de metadados técnicos, sem antecipar cadastros financeiros ou autenticação.
- PostgreSQL isolado em .cache/postgres-e02, porta 55432 e acesso apenas local; bancos anteriores preservados.
- Aplicativo conectado ao diagnóstico, com timeout, aviso de falha e nova tentativa. Os lançamentos continuam simulados, sem persistência no servidor.
- Dependências fixadas, exemplos de variáveis, configuração Compose alternativa, workflow de verificações e preparação Railway.

## Como testar

1. Consultar apps/api/README.md para iniciar banco e API, e apps/mobile/README.md para o Expo.
2. Copiar apps/mobile/.env.example para .env. Na prévia web local, EXPO_PUBLIC_API_URL=http://localhost:8000.
3. Abrir http://localhost:8081 e conferir “Servidor conectado”. A API está em http://localhost:8000/health/ready.
4. Parar a API com Ctrl+C no terminal correspondente e tocar “Verificar conexão”: deve informar que não foi possível conectar, sem afirmar que os lançamentos foram salvos.
5. Reiniciar a API e tocar “Tentar novamente”: deve voltar ao estado conectado.
6. Para Android físico, usar o IP LAN do computador na variável pública e iniciar uvicorn com --host 0.0.0.0 numa rede local confiável. Para emulador padrão Android, usar http://10.0.2.2:8000. Localhost no celular não aponta para o computador. Não expor o PostgreSQL à rede.
7. Reiniciar o Expo após alterar .env. Credenciais de banco nunca vão em variáveis EXPO_PUBLIC_*.

## Verificações realizadas

- 7 testes Python aprovados, incluindo migração real em banco descartável, upgrade repetido, comparação com os modelos, downgrade e novo upgrade.
- Ruff sem erros e TypeScript sem erros.
- Bundle Android exportado; não equivale a APK instalado ou teste físico.
- Interface no Edge com API/PostgreSQL reais: sucesso, resposta 503 simulada, falha de rede simulada e recuperação por nova tentativa.
- Aviso de depreciação upstream no TestClient/httpx; não impediu os testes. Na retomada houve também aviso de permissão do cache pytest; as asserções passaram.

## Pendências de ambiente e aceite

- Testar no Android físico e validar publicação no Railway após review e acesso ao projeto de hospedagem.
- Workflow preparado, ainda não executado no GitHub; Dockerfile preparado, ainda não construído neste computador.
- Não houve push da E01/E02. As branches e commits são locais; a E02 parte da E01. Para revisar apenas esta etapa, comparar com etapa/01-prototipo.
- Decisões de negócio pendentes continuam documentadas; não foram assumidas como aprovadas.

A E02 não deve ser considerada publicada nem aceita em Android físico. A próxima etapa depende de autorização própria.
