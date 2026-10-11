# Financeiro — aplicativo E06

Interface React Native/Expo com TypeScript. Acesso, contas, categorias, despesas pagas, cartões e faturas usam a API e persistem no PostgreSQL. Configure EXPO_PUBLIC_API_URL conforme .env.example.

## Executar

Requisitos: Node.js 24 e pnpm 11.25.0 (ambiente usado na validação), celular Android com Expo Go compatível com SDK 57 ou emulador configurado.

Na pasta `apps/mobile`:

```sh
pnpm install --frozen-lockfile
pnpm start
```

Leia o QR code no Expo Go com computador e celular na mesma rede. Para emulador Android já instalado, use `pnpm android`. A inicialização e a compatibilidade do Expo Go no aparelho ainda precisam de validação física. Não foi gerado APK nesta etapa.

Prévia de apoio no navegador, executando os mesmos componentes:

```sh
pnpm web
```

O alvo do produto continua sendo Android. A prévia web facilita o review, mas não substitui verificar teclado, botão voltar e áreas seguras no aparelho.

## Verificar

```sh
pnpm typecheck
pnpm exec expo install --check
pnpm exec expo export --platform android --output-dir .expo/android-export
```

Exportar o bundle não instala nem testa o app em um Android. O lockfile deve acompanhar alterações de dependências.

## Organização

- `App.tsx`: painel real, abas e seleção de mês.
- `src/ExpenseForm.tsx`: formulário e validações de entrada.
- `src/finance.ts`: tipos dos dados financeiros.
- `src/CardPanel.tsx`: cartões, faturas, pagamento e correções de parcelas.
- `src/prototype.ts`: formatação de valores e datas.
- `src/ui.tsx`: componentes visuais reutilizados.

Base extraída do template oficial `expo-template-blank-typescript@57.0.29`, com dependências conferidas pelo Expo. [Referência do template](https://docs.expo.dev/more/create-expo/).

## Histórico: conexão E02

Copie .env.example para .env e configure EXPO_PUBLIC_API_URL. Reinicie o Expo após alterações. O diagnóstico consulta /health/ready; os lançamentos continuam em memória. Consulte [revisão E02](../../docs/revisao-e02.md) para Android físico e estados de falha.

## E03 — acesso real

Agora a entrada exige cadastro/login na API. Use e-mail fictício válido e senha de no mínimo 10 caracteres para testar localmente. Sessões ficam em SecureStore no Android e sessionStorage na prévia web. Criar espaço e compartilhar por código são operações reais; o painel financeiro continua simulado em memória.

O app.json declara o esquema financeiro e o plugin expo-secure-store. Links nativos de recuperação exigem um build instalado compatível. Consulte ../../docs/revisao-e03.md para o roteiro completo e as limitações do envio SMTP.
