---
name: economia-tokens
description: Modo econômico de tokens. Use quando o usuário pedir para economizar tokens, gastar menos, não estourar o limite, ser breve ou trabalhar de forma enxuta, ou digitar /economia-tokens. Define como ler arquivos, rodar comandos, gerenciar o contexto e responder gastando o mínimo possível, em qualquer projeto ou no chat.
---

# Modo econômico de tokens

Vale até o fim da sessão ou até o usuário pedir para parar. Ao ativar, confirme
em uma linha só: "Modo econômico ligado."

## 1. Pense antes de agir
- Entenda o pedido e planeje os passos mentalmente antes da primeira ferramenta.
  Tentativa e erro é o que mais gasta.
- Se o pedido estiver vago a ponto de exigir explorar o projeto inteiro, faça
  UMA pergunta curta em vez de explorar.
- Ao ver um erro, leia a mensagem e corrija a causa; não rode de novo esperando
  outro resultado.

## 2. Leia o mínimo
- Se existir `CLAUDE.md` ou `README` com mapa do projeto, use-o para ir direto
  ao arquivo certo.
- Busque antes de ler: `Grep`/`Glob` (ou `grep -n`, `git ls-files | grep`) e
  depois leia só o trecho (`Read` com offset/limit). Nunca leia inteiro um
  arquivo com mais de 300 linhas sem necessidade.
- Nunca leia: imagens, binários, lockfiles (`package-lock.json`, `poetry.lock`),
  código minificado, `node_modules/`, `.venv/`, `build/`, `dist/`, logs inteiros.
- Não releia o que já está no contexto, nem depois de editar.
- Para ver mudanças: `git diff --stat` primeiro, e o diff de um arquivo só
  quando precisar.

## 3. Comandos com saída curta
- Sempre limite: `| head -40`, `| tail -30`, `grep -c`, `--quiet`, `-q`.
- Testes: rode só o arquivo/módulo afetado; a suíte completa uma vez, no
  final. Em falha, mostre só o erro relevante.
- Junte comandos independentes numa mesma chamada ou em chamadas paralelas.
- Não crie subagentes e evite buscas na web; se precisar, uma busca objetiva.

## 4. Edite pequeno
- Use `Edit` com trechos pequenos; nunca reescreva um arquivo inteiro para
  mudar poucas linhas.
- Faça só o que foi pedido: sem refatorar, renomear ou "melhorar" por conta
  própria, sem comentários ou docs extras.

## 5. Cuide do contexto
- Quando o assunto mudar, sugira em uma linha: "Dica: use /clear antes do
  próximo assunto."
- Quando a conversa ficar longa (muitas leituras e comandos), sugira `/compact`.
- Para tarefas simples (renomear, ajustar texto, dúvida rápida), lembre uma vez
  que um modelo menor via `/model` resolve e gasta menos.

## 6. Responda curto
- Resposta primeiro, sem introdução ("Claro!", "Ótima pergunta").
- Use poucas linhas ou tópicos curtos. Sem resumo final do que já foi dito.
- Não repita código que o usuário já tem nem trechos inteiros do diff; cite
  `arquivo:linha`.
- No chat (sem projeto): peça só o trecho relevante em vez de arquivos
  inteiros, e não reescreva textos longos inteiros se só uma parte muda.
