# Revisão: cadastro e espaço único

Esta alteração simplifica o acesso ao espaço financeiro. O formulário de cadastro agora tem um campo opcional para o código de convite. Com código válido, a pessoa entra diretamente no espaço compartilhado. Sem código, o app cria e abre automaticamente o espaço “Minhas finanças”. Entradas seguintes abrem o mesmo espaço, sem uma lista de espaços para escolher.

O botão “Participantes” continua disponível para gerar convites, transferir a administração ou sair do espaço. Se um participante sair ou for removido, a tela oferece entrar com outro código ou criar um espaço próprio. A API rejeita a criação ou o aceite de um segundo espaço para o mesmo login. Código inválido não cria cadastro incompleto nem consome o convite.

Para conferir no app local em `http://localhost:8081/`, abra “Criar cadastro”: o campo “Código de convite (opcional)” aparece abaixo da senha. O seu login existente deve abrir diretamente o espaço “teste”, com “Participantes” no topo. Para testar os dois tipos de cadastro sem mexer nos seus dados, use contas novas de teste apenas no ambiente local.

Validação: 42 testes da API passaram no banco descartável de teste; verificação de tipos do app passou; análise estática dos arquivos Python alterados passou. Nenhuma alteração foi enviada ao GitHub nesta revisão.
