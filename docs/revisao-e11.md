# E11 — servidor e APK de teste

Status: versão de teste do Rautto com API no Railway e APK instalável. A publicação na Play Store é uma etapa separada.

## Servidor

- Projeto Railway: [Meu Controle](https://railway.com/project/42ff613a-fc0e-4453-bafb-ccea3529e501), separado dos demais projetos da conta.
- Ambiente `production`: serviço `Financeiro` a partir da branch `main` e serviço PostgreSQL com volume próprio.
- API pública: `https://financeiro-production-51f2.up.railway.app`.
- Pasta do serviço: `/apps/api`; build pelo `/apps/api/Dockerfile`.
- Antes de iniciar, o Railway executa `alembic upgrade head`; prontidão em `/health/ready`.
- `DATABASE_URL` referencia `${{Postgres.DATABASE_URL}}` no Railway. `APP_ENV=production`, `CORS_ORIGINS=[]` e `PASSWORD_RESET_URL=financeiro://reset` estão no serviço. Nenhuma credencial do banco está no aplicativo ou no Git.
- Deploy automático do GitHub está **desativado**. Novas versões devem ser implantadas manualmente depois do push.
- Novos cadastros em produção aguardam aprovação da conta já existente `gabrirauber@gmail.com`, na tela Participantes. A prontidão do serviço exige essa conta como administradora de acesso.

O endpoint de diagnóstico respondeu HTTP 200 com banco pronto em 12 e 13/10/2026. O serviço roda no período de teste do Railway; a continuidade após o crédito/prazo de teste depende da conta do cliente. Nenhum plano pago foi contratado nesta etapa.

## Verificações já executadas

- Suíte da API com PostgreSQL local exclusivo `financeiro_test`: **68 testes passaram**. O banco do Railway não recebeu dados de teste.
- Backup em formato custom de `financeiro_test` restaurado no banco local separado `financeiro_e11_restore_test` com `pg_restore --exit-on-error`. Origem e cópia ficaram na migração `e08_income`, ambas com 26 tabelas públicas.
- A conferência de backup acima demonstra o procedimento técnico em ambiente de teste. Antes de guardar dados reais, definir rotina e retenção de backups no Railway, além de verificar periodicamente uma restauração. O arquivo de teste fica somente em `.cache/` e não é versionado.
- Build Android `assembleRelease` concluído. Assinatura do APK verificada pelo `apksigner`; `aapt` confirmou nome **Rautto**, pacote `com.gabrirauber.financeiro` e Android mínimo 7.0 (API 24). O pacote contém a URL HTTPS da API. TypeScript e Ruff passaram.
- APK instalado no aparelho conectado e processo do aplicativo iniciado. O roteiro funcional abaixo permanece para a revisão do cliente.

## APK de teste

O arquivo de instalação é `output/Rautto-teste.apk` (76.750.969 bytes; SHA-256 `441BA816E29CFD2AA2389B755A64B9273176C14E0A75914E473E0E53F78FA0E4`) e não é versionado. No Android, abra o arquivo APK, permita a instalação por essa origem se o sistema solicitar e conclua a instalação. Depois, abra **Rautto**. Os novos usuários precisarão da aprovação do administrador antes de entrar. O APK contém apenas a URL HTTPS pública da API; senhas e sessão ficam fora do pacote.

Este APK é uma versão de teste assinada com a chave de depuração gerada localmente. Para uma versão distribuída de forma permanente, será necessária uma chave de assinatura própria e preservada. Uma futura versão assinada com outra chave pode exigir desinstalar esta versão de teste antes da instalação; os dados financeiros permanecem no servidor após novo login.

O aplicativo precisa de internet. Recuperação de senha por e-mail ainda depende de configurar um serviço SMTP no Railway (`SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD`). O link nativo já aponta para `financeiro://reset`, mas o envio não funciona sem esse serviço.

## Reproduzir o APK localmente (Windows)

No Windows, usar `scripts/build-android-apk.ps1 -ApiUrl https://financeiro-production-51f2.up.railway.app -BuildRoot C:\mc15` a partir da raiz. A pasta temporária precisa estar vazia e ter caminho realmente curto, pois o compilador C++ do Android excede o limite de nomes de arquivo quando o projeto está na pasta longa do repositório. O script copia somente o código necessário, instala as versões do lockfile em formato plano, gera o projeto Android e executa `gradlew.bat :app:assembleRelease`. Requer Android SDK, JDK compatível, Node.js, pnpm e acesso à rede. O APK final vai para `output/Rautto-teste.apk`. A pasta temporária pode ser removida depois de conferir o APK, sem afetar o repositório.

Para cada APK novo, conferir o endereço da API antes do build: variáveis `EXPO_PUBLIC_*` são públicas e entram no pacote. Não colocar credenciais nelas. O projeto Android gerado e os APKs são ignorados pelo Git.

## Revisão no aparelho

1. Instalar o APK em um Android e abrir o aplicativo sem Expo Go.
2. Criar um usuário, aprová-lo em Participantes pela conta administradora, cadastrar uma conta e cartão, lançar receita e despesa, fechar e abrir novamente o app para confirmar persistência.
3. Conferir fatura, antecipação ou pagamento, resumo mensal e geração/compartilhamento do PDF.
4. Desligar a internet e confirmar a mensagem de conexão; religar e repetir a operação.
5. Testar convite com outro usuário somente depois de confirmar que o primeiro acesso funciona.

Antes de liberar uma nova versão para todos os usuários, confirmar o funcionamento do cadastro pendente, da aprovação e do login no servidor de produção.
