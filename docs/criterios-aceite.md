# Requisitos e critérios de aceite — E00

Data: 07/10/2026. Status: preparado para revisão. Cenários documentados, ainda não executados no aplicativo.

Base: [modelagem](modelagem.md) e [plano](plano-desenvolvimento.md). Regras novas ou ambíguas estão em [decisões pendentes](decisoes-pendentes.md); seus cenários não são aprovados implicitamente por este documento.

## Escopo e convenções

Primeira versão: Android online, acesso individual por e-mail/senha, espaço compartilhado, contas, receitas, despesas, cartões, recorrências, projeções e PDF. Fora do escopo inicial: iOS, modo offline, controle de limite de cartão, integração bancária automática e publicação obrigatória na Play Store.

Valores dos exemplos são em reais. O mês corrente deve ser controlável nos testes; outubro/2026 é apenas uma referência. Resultado mensal, consumo e fluxo de caixa são conceitos diferentes. A regra de refinanciamento em DEC-02 precisa ser aprovada antes de consolidar suas fórmulas.

## Matriz de rastreabilidade

| ID | Requisito / etapa | Cenário de aceite |
|---|---|---|
| RF-01 | Android online — E01/E02 | Dado o app no Android, ao abrir com internet carrega o serviço; sem conexão informa indisponibilidade e não confirma falsamente uma gravação. |
| RF-02 | Cadastro e autenticação — E03 | Cadastrar e-mail/senha, sair e entrar novamente permite acessar o próprio espaço; senha incorreta nega acesso e não cria sessão. |
| RF-03 | Espaço compartilhado — E03 | Usuário B aceita código criado por A e visualiza o mesmo espaço com login próprio. Usuário C sem participação não consulta nem altera seus dados, inclusive via API. |
| RF-04 | Administração — E03 | Administrador remove B; próximas operações de B são negadas. Participante comum não gera convites nem remove pessoas. Validade e transferência administrativa dependem de DEC-04. |
| RF-05 | Contas e saldo inicial — E04 | Cadastrar conta bancária com R$ 1.000 e dinheiro com R$ 100 resulta em saldos individuais corretos e consolidado de R$ 1.100, sem tratar saldo inicial como receita do mês. |
| RF-06 | Receita recebida — E04 | Lançar R$ 500 em uma conta com R$ 1.000 resulta imediatamente em R$ 1.500, sem segunda confirmação de recebimento. |
| RF-07 | Transferência — E04 | Transferir R$ 200 de A com R$ 1.000 para B com R$ 100 resulta em A=R$ 800, B=R$ 300; consolidado continua R$ 1.100 e não há receita nem despesa. Falha não salva apenas um lado. |
| RF-08 | Categorias — E05 | Novo espaço recebe categorias/subcategorias iniciais e permite adicionar opções. Subcategoria deve pertencer à categoria selecionada. Desativação de cadastro usado preserva o histórico. |
| RF-09 | Despesa paga — E05 | Lançar R$ 80 em débito ou dinheiro reduz em R$ 80 a conta escolhida, aparece uma vez na listagem e permanece após reabrir. Categoria/subcategoria são obrigatórias; observação é opcional e data começa no dia atual. |
| RF-10 | Tela inicial — E01/E05 | Ao abrir, exibir gráfico por categoria e botão flutuante à direita. Tocar em categoria mostra suas subcategorias; trocar mês altera os dados consultados. |
| RF-11 | Edição e exclusão — E04/E05 | Editar despesa atual de R$ 80 para R$ 90 reduz o saldo em mais R$ 10; excluir recompõe R$ 90. Alteração/exclusão de mês anterior é rejeitada também na API. Casos de parcelas e pagamentos dependem de DEC-03. |
| RF-12 | Cadastro de cartão — E06 | Cadastrar nome, dia de fechamento, vencimento e checkbox do fechamento sem exigir limite de crédito. |
| RF-13 | Fechamento de fatura — E06 | Fechamento em 10/10 e vencimento em 20/10: compra de 09/10 entra em outubro, de 11/10 em novembro. Em 10/10, checkbox desmarcado envia para outubro; marcado envia para novembro. |
| RF-14 | Compra parcelada — E06 | R$ 600 em três vezes com primeira fatura em outubro gera R$ 200 em outubro, novembro e dezembro, sem reduzir saldo bancário na compra. Permitir ajustar a primeira fatura. |
| RF-15 | Parcelamento antigo — E06 | Cadastrar três parcelas restantes de R$ 200 a partir de outubro gera apenas outubro, novembro e dezembro; não recria pagamentos anteriores nem modifica saldo inicial. |
| RF-16 | Pagamento integral — E06 | Pagar fatura de R$ 600 com conta de R$ 1.000 deixa saldo de R$ 400 e fatura quitada, sem adicionar R$ 600 de novas despesas ao gráfico. |
| RF-17 | Pagamento parcial — E07 | Fatura de R$ 1.000, pagamento de R$ 600 e restante de R$ 400 mais R$ 40 de juros em duas vezes gera saída de R$ 600 e duas parcelas de R$ 220. Cancelar antes de confirmar não grava efeitos parciais. |
| RF-18 | Faturas parceladas no gráfico — E07 | Parcelas do refinanciamento aparecem como “Faturas parceladas” nos meses correspondentes; compras originais permanecem no histórico. Total de consumo de vários meses não classifica novamente o principal financiado como compra. Resultado mensal depende de DEC-02. |
| RF-19 | Despesa fixa — E08 | Cadastrar internet mensal de R$ 100 gera previsão; confirmar pagamento por R$ 110 reduz caixa em R$ 110 e substitui a previsão pela despesa real, sem somar R$ 210. |
| RF-20 | Recorrência no cartão — E08 | Cadastrar assinatura de R$ 50 gera compra na fatura de cada período. Executar a rotina duas vezes para o mesmo período continua produzindo apenas uma ocorrência. |
| RF-21 | Renda prevista — E08 | Cadastrar R$ 2.000 no dia 5 e R$ 1.000 no dia 20, com responsáveis, gera duas previsões mensais sem aumentar saldo. Ajustar um mês não reescreve meses anteriores. |
| RF-22 | Lembrete de receita — E08 | Na data prevista, se ainda pendente, abrir app exige informar recebimento ou “Ainda não recebi”. Adiar não cria receita; pergunta volta no dia seguinte. Receita vinculada concluída encerra a cobrança. Recebimentos parciais dependem de DEC-01. |
| RF-23 | Resultado do mês — E09 | Renda considerada de R$ 3.000, despesas pagas de R$ 400, fixas pendentes de R$ 800 e fatura de R$ 600 resultam em R$ 1.200. Gastos acima da renda exibem déficit. Extras/refinanciamento dependem de DEC-01/02. |
| RF-24 | Saldo final previsto — E09 | Saldo atual R$ 1.100 + recebimentos ainda esperados R$ 1.500 − fixas pendentes R$ 800 − fatura pendente R$ 600 = R$ 1.200. Pagamentos já refletidos no saldo não são subtraídos novamente. Atrasos dependem de DEC-03. |
| RF-25 | PDF — E10 | Gerar relatório do mês inclui renda prevista/recebida, categorias, faturas, saldos e projeção. Detalhamento é opcional. Totais coincidem com o painel do período e PDF pode ser compartilhado pelo Android. |
| RF-26 | Histórico — E09/E10 | Consultar mês passado usa saldo na data final daquele mês, não o saldo atual. Alterações permitidas no mês corrente não reescrevem movimentações anteriores. |
| RF-27 | Séries — E08 | Alterar ocorrência atual ou atual e futuras aplica somente o alcance escolhido. Ocorrências de meses anteriores permanecem iguais; comportamento de fatura paga depende de DEC-03. |
| RF-28 | Recuperação de acesso — E03/E11 | Antes de uso real, usuário consegue recuperar acesso sem revelar senha antiga. Canal e detalhes pendentes em DEC-05. |

## Requisitos de integridade

| ID | Regra | Verificação prevista |
|---|---|---|
| RI-01 | Centavos exatos | R$ 100 em três vezes gera R$ 33,33 + R$ 33,33 + R$ 33,34. Soma sempre igual ao total. |
| RI-02 | Isolamento de espaços | Trocar identificador de conta, despesa ou fatura por identificador de outro espaço não concede acesso, nem por associação indireta. |
| RI-03 | Operações atômicas e reenvio | Falha durante transferência/refinanciamento não deixa efeitos parciais; repetir a mesma requisição não duplica saldo nem parcelas. |
| RI-04 | Recorrência no servidor | Com o app fechado, geração do período continua disponível no servidor; reexecução não duplica registros. |
| RI-05 | Datas limítrofes | Testar fevereiro, ano bissexto, dezembro/janeiro e dia 31. Proposta já identificada na modelagem: limitar dia inexistente ao último do mês. |
| RI-06 | Credenciais e sessão | Senha não é persistida em texto puro nem enviada em logs; logout invalida o acesso conforme política de sessão definida em E03. |
| RI-07 | Renda zero | Comprometimento percentual com renda zero aparece como não aplicável, sem divisão por zero; valores absolutos de déficit continuam visíveis. |
| RI-08 | Rastreabilidade | Movimentação registra autor e espaço; revisão mostra os commits que implementam e verificam cada requisito. |

## Validação por etapa

Cada entrega deverá citar os RF/RI atendidos, os cenários executados, seus resultados e o que permanece pendente. Os critérios acima são a base dos testes futuros; a E00 valida documentação e exemplos, não um aplicativo inexistente.
