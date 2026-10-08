# Revisão da E01 — protótipo Android

Data: 07/10/2026. Status: implementado para revisão visual; aceite no aparelho Android pendente. E02 não iniciada.

## Escopo entregue

Revisão solicitada pelo cliente: cadastro simulado de categorias e subcategorias disponível em “Gerenciar categorias e subcategorias” no resumo e diretamente no formulário. A base inicial já contém subcategorias; no lançamento, elas aparecem após selecionar a categoria. Novos cadastros são compartilhados entre telas durante a sessão, com rejeição de nomes vazios ou duplicados na mesma categoria. Recarregar restaura a base inicial. Persistência permanece na E05.

- Painel com mês selecionável, total simulado, gráfico em barras por categoria e detalhamento por subcategoria.
- Lista de movimentações filtrada pelo mês e, ao detalhar, pela categoria.
- Botão flutuante à direita para nova despesa.
- Valor, categoria/subcategoria obrigatórias, data atual editável, pagamento, origem do dinheiro e observação opcional.
- Validação de valor positivo e data existente; troca de categoria limpa a subcategoria anterior.
- Lançamento simulado atualiza gráfico e lista; escolher data de outro mês navega para esse mês.
- Navegação para contas e cartões com dados ilustrativos e indicação das etapas em que ganharão operações reais.
- Identificação permanente de protótipo com dados fictícios.

Cobertura visual: RF-09/RF-10; organização de telas RF-05/RF-12. Não considerar atendida a persistência, conexão de RF-01 ou regras financeiras das etapas seguintes.

## Roteiro do cliente

1. Iniciar conforme [README do aplicativo](../apps/mobile/README.md), abrir no Android e conferir tamanho e legibilidade.
2. No Resumo, tocar em Alimentação: devem aparecer Mercado, Restaurantes e Café. Voltar a todas as categorias.
3. Avançar um mês: deve aparecer o estado vazio. Voltar ao mês inicial.
4. Tocar em +. Conferir data atual e tentar adicionar sem valor, sem categoria e sem subcategoria: cada caso deve informar o campo faltante.
5. Digitar R$ 45,90, escolher Alimentação/Café, Pix e Conta principal, deixando a observação vazia. Adicionar à simulação.
6. Total inicial de R$ 2.249,90 passa a R$ 2.295,80 e o lançamento aparece na lista. Reabrir formulário deve começar limpo.
7. Informar data impossível, como 31/02/2026: não deve aceitar. Trocar categoria não pode manter subcategoria incompatível.
8. Experimentar Crédito: selecionar cartão e conferir o aviso de que não há cálculo de faturas na E01.
9. Navegar por Contas e Cartões. Conferir que os saldos ilustrativos são fixos e claramente identificados.
10. Cancelar um lançamento não modifica os exemplos. Recarregar restaura os cinco lançamentos iniciais.
11. No Android, conferir teclado, rolagem até o botão final, botão voltar do aparelho e espaçamento junto às barras do sistema.

## Verificações executadas

- TypeScript estrito sem erros.
- Compatibilidade de dependências confirmada pelo Expo.
- Bundle Android exportado com sucesso; isso não é um APK nem um teste em aparelho físico.
- Prévia web em Edge headless: categorias, meses, abas, validação de valor/categoria/subcategoria/data, crédito, lançamento, total, reset e cancelamento. Nenhum erro JavaScript durante a jornada.
- Inspeção visual em largura de 393 px e verificação de ausência de overflow horizontal em 320 px.

## Limitações intencionais

Os saldos das contas são exemplos fixos. Crédito é exibido no mês da compra apenas na simulação; fechamento, parcelas e faturas ficam na E06. Provisionamento, login, convites, receitas e PDF não foram implementados. Fechar ou recarregar descarta os lançamentos simulados.

Não há emulador/aparelho conectado disponível nesta execução; a experiência nativa e o uso do Expo Go precisam da revisão no Android. Decisões de negócio pendentes da E00 continuam em [decisões pendentes](decisoes-pendentes.md); autorização para push não equivale a responder essas questões.

## Git e autorização

E00 enviada ao remoto informado pelo cliente, em `main` e `etapa/00-especificacoes`. E01 desenvolvida em `etapa/01-prototipo`, com commits locais separados para base e interface. **Não fazer push desta branch antes do novo code review e autorização do cliente.**

Para revisar:

```sh
git log --oneline main..etapa/01-prototipo
git diff main...etapa/01-prototipo
```
