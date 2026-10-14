# Railway — preparação da E02

Atualização E11: o ambiente do Meu Controle foi criado e a API está ativa no Railway; veja [revisão E11](revisao-e11.md). O roteiro abaixo registra a preparação original da E02.

Status na E02: configuração pronta para revisão, sem publicação. Usar um ambiente de teste separado de produção.

1. Após code review e autorização de push/publicação, criar serviço da API no Railway ligado ao repositório Financeiro.
2. Definir Root Directory como `/apps/api` e o caminho do arquivo de configuração como `/apps/api/railway.json`. O Dockerfile é relativo à raiz do serviço.
3. Adicionar PostgreSQL no mesmo ambiente e definir DATABASE_URL por referência à variável do serviço PostgreSQL. Nunca copiar credenciais para arquivos versionados ou para o aplicativo.
4. Definir APP_ENV=production. Definir CORS_ORIGINS como array JSON de origens web permitidas; `[]` basta para cliente Android nativo. Não usar curinga.
5. A configuração executa `alembic upgrade head` antes de iniciar a API e usa `/health/ready` como healthcheck. A porta é recebida de PORT. O processo no container roda como usuário sem privilégios.
6. Gerar domínio HTTPS e conferir `/health/live` e `/health/ready`, ambos HTTP 200. Informar a URL HTTPS pública em EXPO_PUBLIC_API_URL no app e reiniciar o Expo/regerar o aplicativo.
7. Manter deploy automático desativado até combinar o fluxo com o cliente. Uma autorização de push não autoriza produção automaticamente.

Arquivos preparados: Dockerfile, .dockerignore e railway.json em apps/api. Nenhuma conta Railway foi acessada, nenhum recurso contratado e nenhuma URL remota foi criada. O build Docker e o deploy remoto ainda precisam ser validados no ambiente de hospedagem; Docker não está disponível nesta sessão.

Referências consultadas: [FastAPI no Railway](https://docs.railway.com/guides/fastapi), [comando inicial](https://docs.railway.com/deployments/start-command).
