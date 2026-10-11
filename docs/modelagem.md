# Modelagem do aplicativo de controle financeiro

Versão inicial — 30/09/2026. Documento de especificação; não representa uma implementação.

Atualização de contexto em 07/10/2026: tecnologias aprovadas em [ADR-0001](adr/0001-arquitetura-inicial.md), critérios em [critérios de aceite](criterios-aceite.md). Refinamentos ainda não aprovados estão em [decisões pendentes](decisoes-pendentes.md); em particular, a fórmula do resultado após refinanciamento aguarda essa decisão. O restante deste documento preserva a modelagem inicial.

## Escopo

Aplicativo Android, conectado à internet, com autenticação por e-mail e senha e dados no servidor. Cada pessoa possui seu login e participa de um espaço financeiro compartilhável por código de convite. Conta financeira significa conta bancária ou dinheiro em espécie; não significa login.

Refinamento de 11/10/2026: cada login pertence a um único espaço financeiro por vez. No cadastro, o código de convite é opcional: com código, a pessoa entra no espaço compartilhado; sem código, o aplicativo cria seu espaço pessoal. Após entrar, o aplicativo abre esse espaço diretamente, sem escolha entre vários espaços. Se um participante sair ou for removido, pode entrar em outro espaço por convite ou criar um espaço próprio, sem manter duas participações simultâneas.

## Fluxograma principal

```mermaid
flowchart TD
    A[ Abrir aplicativo ] --> B{Sessão autenticada?}
    B -- Não --> C[Entrar ou cadastrar com e-mail e senha]
    C --> D{Já participa de um espaço?}
    B -- Sim --> D
    D -- Não --> E{Informou código no cadastro?}
    E -- Não --> F[Criar espaço pessoal]
    E -- Sim --> G[Validar código de convite]
    G --> H{Código válido?}
    H -- Não --> G
    H -- Sim --> I[Acessar espaço compartilhado]
    F --> J[Cadastrar contas e saldos iniciais]
    J --> K[Cadastrar cartões e previsões de renda se houver]
    K --> L[Carregar dados e gerar recorrências devidas]
    I --> L
    D -- Sim --> L
    L --> M{Receita prevista vencida sem lançamento?}
    M -- Sim --> N{Informar recebimento}
    N -- Recebi --> O[Lançar receita na conta e vincular à previsão]
    N -- Ainda não recebi --> P[Adiar lembrete até o próximo dia]
    O --> Q[Tela inicial do mês]
    P --> Q
    M -- Não --> Q
    Q --> R[Gráfico por categoria e subcategoria]
    Q --> S[Resultado do mês e saldo final previsto]
    Q --> T{Ação}
    T --> U[Adicionar despesa]
    T --> V[Confirmar pagamento de despesa fixa]
    T --> W[Lançar receita ou transferência]
    T --> X[Consultar e pagar fatura]
    T --> Y[Gerenciar cadastros e compartilhamento]
    T --> Z[Gerar e compartilhar PDF]
    U --> AA[Atualizar saldos, gráfico e previsão]
    V --> AA
    W --> AA
    X --> AA
    Y --> AA
    AA --> Q
```

## Fluxograma de despesas e cartões

```mermaid
flowchart TD
    A[Nova despesa] --> B[Valor, categoria, subcategoria e data atual editável]
    B --> C[Observação opcional e forma de pagamento]
    C --> D{Compra no cartão?}
    D -- Não --> E[Selecionar conta de saída]
    E --> F[Registrar despesa paga e saída de caixa]
    D -- Sim --> G[Selecionar cartão]
    G --> H{Tipo de compra}
    H -- À vista --> I[Gerar uma parcela]
    H -- Parcelada --> J[Informar total e quantidade de parcelas]
    J --> K[Calcular parcelas com ajuste de centavos]
    H -- Recorrente --> L[Cadastrar regra mensal de recorrência]
    L --> I
    I --> M[Determinar primeira fatura pelo fechamento e checkbox]
    K --> M
    M --> N[Permitir ajuste da primeira fatura]
    N --> O[Distribuir parcelas nas faturas mensais]
    O --> P[Atualizar compromissos sem retirar dinheiro da conta]
    F --> Q[Atualizar painel]
    P --> Q

    R[Pagar fatura] --> S[Informar conta, data e valor pago]
    S --> T{Pagamento integral?}
    T -- Sim --> U[Registrar saída de caixa e quitar fatura]
    T -- Não --> V[Preparar saldo restante automaticamente]
    V --> W[Informar juros, parcelas e primeira fatura do financiamento]
    W --> X[Confirmar pagamento e financiamento juntos]
    X --> Y[Registrar saída apenas do valor pago]
    Y --> Z[Encerrar fatura original como refinanciada]
    Z --> AA[Adicionar parcelas futuras como Faturas parceladas]
    U --> Q
    AA --> Q
```

O pagamento parcial e a destinação do saldo restante são confirmados juntos. Cancelar essa operação antes da confirmação não pode deixar uma fatura encerrada sem o registro do saldo devedor. As compras originais permanecem no histórico; a fatura é encerrada por pagamento e refinanciamento, não por uma saída fictícia de dinheiro.

## Diagrama de classes — identidade e cadastros

Os diagramas abaixo compõem um único modelo, dividido para facilitar a leitura. As classes de domínio descrevem os dados e responsabilidades; não exigem uma tecnologia específica.

```mermaid
classDiagram
    class Usuario {
        UUID id
        string nome
        string email
        string credencialProtegida
    }
    class EspacoFinanceiro {
        UUID id
        string nome
        string fusoHorario
    }
    class Participacao {
        UUID id
        Papel papel
        bool ativa
    }
    class Convite {
        UUID id
        string codigoProtegido
        datetime validade
        datetime utilizadoEm
        validar()
        aceitar()
    }
    class ContaFinanceira {
        UUID id
        string descricao
        TipoConta tipo
        decimal saldoInicial
        date dataSaldoInicial
        bool ativa
        calcularSaldo()
    }
    class CartaoCredito {
        UUID id
        string nome
        int diaFechamento
        int diaVencimento
        bool compraNoFechamentoVaiParaProxima
        determinarFatura(dataCompra)
    }
    class Categoria {
        UUID id
        string nome
        bool ativa
    }
    class Subcategoria {
        UUID id
        string nome
        bool ativa
    }
    Usuario "1" --> "0..*" Participacao
    EspacoFinanceiro "1" --> "1..*" Participacao
    EspacoFinanceiro "1" --> "0..*" Convite
    Usuario "1" --> "0..*" Convite : criado por
    EspacoFinanceiro "1" --> "0..*" ContaFinanceira
    EspacoFinanceiro "1" --> "0..*" CartaoCredito
    EspacoFinanceiro "1" --> "1..*" Categoria
    Categoria "1" --> "1..*" Subcategoria
```

O criador do espaço é administrador. Participantes ativos podem consultar e registrar movimentações; somente o administrador gerencia participantes e convites. O código dá acesso ao espaço, não à senha ou à identidade de outra pessoa. Categorias iniciais são copiadas para cada espaço e podem ser personalizadas.

## Diagrama de classes — movimentações e previsões

```mermaid
classDiagram
    class MovimentoCaixa {
        UUID id
        date data
        decimal valorAssinado
        TipoMovimento tipo
    }
    class Receita {
        UUID id
        string descricao
        decimal valor
        date dataRecebimento
    }
    class Transferencia {
        UUID id
        decimal valor
        date data
        registrar()
    }
    class PrevisaoRenda {
        UUID id
        string descricao
        decimal valorMensal
        int diaRecebimento
        bool ativa
    }
    class RecebimentoPrevisto {
        UUID id
        YearMonth competencia
        decimal valorPrevisto
        date dataPrevista
        date lembrarNovamenteEm
        calcularValorAindaEsperado()
    }
    class Despesa {
        UUID id
        string descricao
        decimal valorTotal
        date dataCompra
        FormaPagamento formaPagamento
        string observacao
    }
    class RecorrenciaDespesa {
        UUID id
        string descricao
        decimal valorPrevisto
        int diaPrevisto
        date inicio
        date fim
        gerarOcorrenciaMensal()
    }
    class OcorrenciaDespesaFixa {
        UUID id
        YearMonth competencia
        date dataPrevista
        decimal valorPrevisto
        StatusOcorrencia status
        confirmarPagamento(valorReal, conta)
    }
    ContaFinanceira "1" --> "0..*" MovimentoCaixa
    Receita "1" --> "1" MovimentoCaixa : entrada
    Transferencia "1" --> "2" MovimentoCaixa : saída e entrada
    PrevisaoRenda "1" --> "0..*" RecebimentoPrevisto
    Usuario "1" --> "0..*" PrevisaoRenda : responsável
    RecebimentoPrevisto "0..1" --> "0..*" Receita : recebimentos vinculados
    Despesa "1" --> "0..1" MovimentoCaixa : pagamento fora do cartão
    Subcategoria "1" --> "0..*" Despesa
    Subcategoria "1" --> "0..*" RecorrenciaDespesa
    RecorrenciaDespesa "1" --> "0..*" OcorrenciaDespesaFixa
    OcorrenciaDespesaFixa "0..1" --> "0..1" Despesa : pagamento realizado
    RecorrenciaDespesa "0..1" --> "0..*" Despesa : geração no cartão
    CartaoCredito "0..1" --> "0..*" RecorrenciaDespesa
```

Cada registro financeiro pertence a um espaço e registra quem o criou. Essas relações comuns foram omitidas deste diagrama para legibilidade. A categoria da despesa é obtida pela subcategoria escolhida, impedindo combinações inconsistentes.

Uma recorrência fora do cartão gera previsões de despesas fixas; a confirmação gera a despesa paga. Uma recorrência no cartão gera compras automaticamente, uma única vez por período. Receita avulsa aumenta o caixa, mas não quita automaticamente uma previsão sem vínculo. O lançamento solicitado pelo lembrete já recebe esse vínculo.

## Diagrama de classes — faturas e serviços

```mermaid
classDiagram
    class Fatura {
        UUID id
        date dataFechamento
        date dataVencimento
        StatusFatura status
        calcularTotal()
        calcularSaldoDevedor()
    }
    class ParcelaCartao {
        UUID id
        int numero
        int quantidadeTotal
        decimal valor
        TipoParcela tipo
    }
    class PagamentoFatura {
        UUID id
        date data
        decimal valorPago
    }
    class FinanciamentoFatura {
        UUID id
        decimal principal
        decimal jurosEEncargos
        int quantidadeParcelas
        gerarParcelas()
    }
    class ServicoProvisionamento {
        calcularResultadoMensal(espaco, mes)
        calcularSaldoFinalPrevisto(espaco, mes)
        calcularComprometimentoRenda(espaco, mes)
    }
    class ServicoRelatorioPDF {
        gerar(espaco, mes, incluirDetalhamento)
    }
    class PoliticaEdicao {
        validarMesCorrente(registro, espaco)
        validarAlteracaoDaSerie(registro)
    }
    class ServicoRecorrencias {
        gerarOcorrenciasSemDuplicidade(espaco, mes)
    }
    CartaoCredito "1" --> "0..*" Fatura
    Fatura "1" --> "0..*" ParcelaCartao
    Despesa "0..1" --> "0..*" ParcelaCartao : compra
    FinanciamentoFatura "0..1" --> "1..*" ParcelaCartao : refinanciamento
    Fatura "1" --> "0..*" PagamentoFatura
    PagamentoFatura "1" --> "1" MovimentoCaixa : saída real
    Fatura "1" --> "0..1" FinanciamentoFatura : saldo refinanciado
    ServicoProvisionamento ..> Fatura
    ServicoProvisionamento ..> RecebimentoPrevisto
    ServicoProvisionamento ..> OcorrenciaDespesaFixa
    ServicoProvisionamento ..> MovimentoCaixa
    ServicoRelatorioPDF ..> ServicoProvisionamento
    PoliticaEdicao ..> Despesa
    ServicoRecorrencias ..> RecorrenciaDespesa
    ServicoRecorrencias ..> PrevisaoRenda
```

Cada parcela tem uma única origem: compra ou financiamento. Parcelamentos antigos geram somente as parcelas restantes; valores históricos já pagos não alteram o saldo inicial. Faturas e parcelas usam o mês de vencimento como competência do compromisso.

## Regras de cálculo e integridade

1. **Saldo da conta:** saldo inicial mais movimentos de caixa posteriores ao marco inicial. Comprar no cartão não gera saída de caixa; pagar a fatura gera. Transferências geram duas movimentações na mesma operação e não afetam o resultado consolidado.
2. **Resultado previsto do mês:** renda prevista menos despesas fora do cartão já pagas, despesas fixas ainda pendentes e compromissos de cartão do mês. Uma despesa fixa paga substitui sua previsão pelo valor real, sem duplicação.
3. **Saldo final previsto:** saldo atual consolidado mais recebimentos vinculados ainda esperados no mês menos despesas fixas pendentes e valores de faturas ainda a pagar no mês. Receita recebida já está no saldo e não entra outra vez como expectativa. Valores ainda esperados nunca ficam negativos.
4. **Financiamento de fatura:** o gráfico mantém as compras no mês original e mostra o financiamento nas competências futuras em “Faturas parceladas”. Essa é uma visão de compromissos mensais. Em totais de consumo de vários meses, principal refinanciado não é nova compra; juros e encargos aparecem separados. O PDF distingue consumo, compromissos e fluxo de caixa.
5. **Gráfico do cartão:** compras no crédito entram em Gastos do mês pelo mês da fatura atribuída, inclusive enquanto aberta. Continuam no mesmo mês após fechamento e pagamento; pagar a fatura reduz o caixa e não cria outra despesa no gráfico.
6. **Fechamento:** compras após o fechamento vão para a fatura seguinte; no próprio dia, vale o checkbox do cartão. Cada fatura guarda datas concretas, além dos dias configurados no cartão. Proposta técnica: em meses sem o dia cadastrado, usar o último dia do mês; vencimento deve ocorrer após o fechamento correspondente.
6. **Centavos:** usar valores monetários exatos, sem ponto flutuante binário. O ajuste de arredondamento fica na última parcela, garantindo que a soma corresponda ao total.
7. **Histórico:** edição e exclusão financeira somente no mês corrente do espaço. Em séries, mudanças podem atingir a ocorrência atual e as futuras, preservando meses anteriores. Parcelas antigas já encerradas não podem ser reescritas ao alterar o restante da série. Cadastros usados no histórico devem ser desativados em vez de apagados.
8. **Automação:** geração mensal de previsões e recorrências acontece no servidor, com proteção contra duplicação. Abrir o app consulta os dados atualizados; não é necessário manter o celular aberto para gerar compromissos.
9. **Compartilhamento:** toda consulta e alteração exige participação ativa no espaço. Pagamentos, transferências e refinanciamentos são gravados como operações indivisíveis, evitando saldos parciais e duplicação por toques repetidos.
10. **Lembretes:** ao atingir a data prevista, solicitar o recebimento se houver pendência vinculada. “Ainda não recebi” posterga a cobrança até o dia seguinte, sem criar receita. Permitir informar valor real diferente do previsto e encerrar a previsão quando o recebimento estiver concluído.

## Relatório PDF

Cabeçalho com espaço, mês e data de geração; resumo da renda prevista e recebida; resultado mensal e saldo final projetado; gráfico por categoria; despesas fixas pagas e pendentes; faturas e financiamentos; saldos atuais por conta. Detalhamento de despesas opcional. Para meses anteriores, os saldos devem ser calculados na data de encerramento do período e identificados como históricos, sem apresentar o saldo atual como se fosse daquele mês.

## Limites desta fase

Este é um modelo conceitual para revisão. Não escolhe linguagem, banco de dados ou provedor de servidor. O fluxo não exige limite de cartão nem funcionamento offline. Validade e uso único dos códigos de convite, fuso do espaço, tratamento de centavos e geração sem duplicações são propostas técnicas para dar consistência às regras aprovadas.
