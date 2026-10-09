# ADR-0002 — identidade, sessões e compartilhamento

Data: 09/10/2026. Implementado para revisão na E03.

- Login individual por e-mail normalizado; senha de 10 a 128 caracteres com hash Argon2.
- Sessões opacas e aleatórias de 256 bits, com somente SHA-256 armazenado no banco e validade de 30 dias. Logout remove a sessão; recuperação invalida todas as sessões do usuário.
- Expo SecureStore no Android; sessionStorage na prévia web. Senhas não são guardadas no cliente.
- Espaços têm participação explícita com papel admin/member. Todo acesso protegido consulta a participação atual.
- Operações de convite, remoção e transferência serializadas por bloqueio da linha do espaço no PostgreSQL. Transferência demove o administrador anterior e promove um participante existente numa transação.
- Código de convite aleatório de 12 caracteres hexadecimais, hash no banco, validade de 24 horas e uso único. Aceitação tem limite de tentativas.
- Recuperação usa token aleatório de 256 bits, hash no banco, expiração de 15 minutos, entrega por SMTP com TLS e resposta neutra para e-mail conhecido/desconhecido. Sem provedor configurado, endpoint retorna indisponibilidade explícita para todos.
- URL de recuperação é configuração do servidor, não fornecida pelo solicitante. Produção aceita HTTPS público ou o esquema nativo financeiro://reset. O token vai no fragmento do link para não aparecer na requisição HTTP da página.
- Login e redefinição de senha bloqueiam a mesma linha do usuário, evitando criar sessão com senha antiga durante a troca.
- Rate limiting armazenado no PostgreSQL para compartilhar contadores entre processos. Não usa dados pessoais em texto claro nas chaves.

Alternativa considerada: JWT. Sessão opaca simplifica revogação imediata neste primeiro aplicativo, ao custo de consultar o banco nas chamadas autenticadas.

As decisões de produto sobre convites e recuperação estão em DEC-04/05. Os prazos técnicos de sessão e recuperação podem ser ajustados após review.
