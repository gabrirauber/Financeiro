# Financeiro — protótipo E01

Interface React Native/Expo com TypeScript. Todos os dados são fictícios e ficam em memória: reiniciar ou recarregar restaura os exemplos. Não há autenticação, API ou persistência nesta etapa.

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

- `App.tsx`: painel, abas, seleção de mês e estado da simulação.
- `src/ExpenseForm.tsx`: formulário e validações de entrada.
- `src/prototype.ts`: exemplos, categorias e formatação.
- `src/ui.tsx`: componentes visuais reutilizados.

Base extraída do template oficial `expo-template-blank-typescript@57.0.29`, com dependências conferidas pelo Expo. [Referência do template](https://docs.expo.dev/more/create-expo/).
