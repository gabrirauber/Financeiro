# Revisão da E03 — acesso e compartilhamento

Data: 09/10/2026. Implementação local pronta para review. Sem push da E03; E04 não iniciada.

## O que funciona com dados reais

- Cadastro por e-mail e senha, login, consulta da identidade e logout.
- Senhas protegidas por Argon2; sessão aleatória com expiração em 30 dias e revogação no servidor. O banco armazena somente o hash do token.
- Sessão no Android armazenada com Expo SecureStore. Na prévia web, sessionStorage mantém a sessão apenas na aba.
- Criar/listar espaços e consultar seus participantes; autorização verificada no servidor.
- Convites de uso único, válidos por 24 horas, compartilháveis pelo usuário, com invalidação e limitação de tentativas.
- Aceitar convite com login próprio; participante não gera convites nem remove membros.
- Remover participante, transferir administração e sair do espaço. O administrador precisa transferir antes de sair.
- Recuperação por link de uso único com validade de 15 minutos; a troca de senha revoga as sessões anteriores. Configuração SMTP ainda necessária para entrega de e-mails reais.

As regras DEC-04 e DEC-05 foram aprovadas em 08/10/2026. Prazo de sessão, política de senha e validade do link são escolhas técnicas documentadas no ADR-0002.

## O que continua simulado

Despesas, categorias, contas e cartões do painel ainda são exemplos em memória. O painel reinicia os exemplos ao sair dele ou trocar de espaço. Pessoas no mesmo espaço compartilham o cadastro de participantes, mas ainda NÃO compartilham lançamentos financeiros persistidos. Isso pertence às próximas etapas.

## Roteiro de revisão

1. Iniciar banco e API conforme apps/api/README.md; executar alembic upgrade head. Iniciar o Expo conforme apps/mobile/README.md.
2. Abrir a prévia e cadastrar duas contas fictícias com e-mails diferentes e senhas de 10 a 128 caracteres. Para simular simultaneamente, usar duas janelas com sessões separadas.
3. Na conta A, criar um espaço e abrir Participantes. Gerar o código de convite.
4. Na conta B, informar esse código em Entrar por código. Verificar o mesmo espaço e seus participantes.
5. Tentar reutilizar o código numa terceira conta: deve recusar. Convite invalidado ou expirado também deve ser recusado.
6. Na conta B, confirmar que não há opções de gerar convite, remover membros ou transferir administração.
7. Na conta A, remover B e verificar que B perde acesso às rotas protegidas imediatamente. A interface revalida o acesso ao abrir o painel, voltar ao app e a cada 30 segundos.
8. Convidar B novamente, transferir a administração para B e sair usando A. B deve permanecer como administrador.
9. Recarregar a aba para verificar a restauração de sessão. Fazer logout e confirmar que o token antigo deixa de funcionar.
10. Testar Esqueci minha senha. Sem SMTP configurado, aparece mensagem explícita de indisponibilidade. Após configurar envio, o link abre a troca de senha; uma vez usado, não pode ser reutilizado.

## Verificações executadas

- 16 testes Python aprovados com PostgreSQL real de teste.
- Migrações em banco descartável: upgrade, comparação com modelos, downgrade e novo upgrade.
- Casos de sessão expirada/revogada, senha errada, e-mail duplicado, validação sem ecoar senha e limitação de tentativas.
- Isolamento de espaços, permissões de participante, remoção, transferência, convites expirados/revogados e duas aceitações concorrentes do mesmo código (somente uma aceita).
- Recuperação com resposta neutra, link expirado/uso único e revogação de sessões.
- TypeScript e Ruff sem erros; bundle Android exportado.
- Prévia web: cadastro, criação de espaço, restauração de sessão, login/logout, convite entre duas contas, transferência de administração, saída e troca real de senha por link de teste.
- E-mails externos NÃO foram enviados. O teste de entrega usou remetente simulado; o teste visual de redefinição usou token inserido exclusivamente na base local fictícia.
- Aviso upstream de depreciação de httpx/TestClient permanece; não impediu os testes.

## Limitações e configuração antes de publicar

- Validar no Android físico o SecureStore, teclado, botão voltar, compartilhamento e link profundo. Exportar bundle não equivale a instalar um APK.
- Configurar SMTP seguro, remetente e URL de recuperação; nenhuma credencial foi contratada ou criada.
- Configuração de sessões e limite por IP deve considerar a topologia real do proxy Railway antes de produção. Não confiar em cabeçalhos de IP arbitrários.
- Planejar limpeza periódica de sessões expiradas, tentativas e convites antigos antes de uso prolongado.
- Railway não recebeu deploy. A configuração de CI existe, mas a execução remota desta E03 ainda depende do push autorizado.
- Não há confirmação de propriedade do e-mail no cadastro nesta etapa.

## Como revisar o código

Branch: etapa/03-acesso-compartilhado. Base: etapa/02-base-tecnica.

```sh
git diff etapa/02-base-tecnica...etapa/03-acesso-compartilhado
git log --oneline etapa/02-base-tecnica..etapa/03-acesso-compartilhado
```

Esta entrega aguarda code review e autorização explícita antes de push. E04 exige autorização própria.
