---
name: economia-tokens
description: Modo econômico de tokens. Use quando o usuário pedir para economizar tokens, ser breve, trabalhar de forma enxuta, ou digitar /economia-tokens. Define como ler arquivos, rodar comandos e responder gastando o mínimo possível.
---

# Modo econômico de tokens

Siga estas regras até o fim da sessão ou até o usuário pedir para parar.

## Leitura de código
- Use o mapa do `CLAUDE.md` para ir direto ao arquivo certo, sem explorar o repositório.
- Localize com `grep -n "nome"` e leia só o trecho (`Read` com offset/limit,
  ou `sed -n 'A,Bp'`). Nunca leia um arquivo inteiro com mais de 300 linhas
  sem necessidade.
- Não releia um arquivo que já está no contexto e não releia depois de editar.
- Não abra imagens, binários, `.ico`/`.png`, nem builds (`build/`, `dist/`).
- Não crie subagentes; faça tudo direto.

## Comandos
- Limite a saída: `| head -50`, `| tail -30`, `grep -c`, flags `-q`/`--quiet`.
- Testes: rode só o módulo afetado (`python -m unittest tests.test_animador`)
  e a suíte completa uma vez, no final. Em caso de falha, mostre só o erro.
- Junte comandos independentes numa chamada só.

## Edição
- Use `Edit` com trechos pequenos, nunca reescreva o arquivo inteiro.
- Faça só o que foi pedido; nada de refatorações ou melhorias extras.

## Respostas
- Curtas e diretas, em português. Sem resumo do que já foi dito e sem repetir
  código que o usuário pode ver no diff.
- Pergunte só quando estiver de fato travado; senão escolha o óbvio e siga.
