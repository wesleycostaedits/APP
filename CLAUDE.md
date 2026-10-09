# Animador para DaVinci Resolve

Biblioteca de animações para imagens no DaVinci Resolve (Python + PySide6).

## Mapa do código
- `Animador.py`: núcleo, sem interface. Curvas de easing, catálogo de animações
  (`_CATALOGO` → `PRESETS`/`CATEGORIAS`), geração de keyframes
  (`gerar_keyframes`, `gerar_trilhas`) e aplicação no Fusion (`aplicar_preset`,
  `remover_animacoes`). Também tem a janela simples do script (`abrir_janela`).
- `AnimadorApp.py`: conexão com o Resolve Studio (`conectar_resolve`), clipes da
  timeline (`listar_clipes`, `aplicar_em_clipe`), checagem de atualização,
  `VERSAO` e `main()`.
- `interface.py` (~1300 linhas): interface PySide6. Temas/estilo no topo,
  widgets (`Biblioteca`, `Previa`, `GraficoCurva`, `Cartao`, `ListaClipes`) e a
  janela principal `JanelaAnimador`.
- `tests/`: unittest, um arquivo por módulo.
- `Animador.spec` (PyInstaller), `instalador/Animador.iss` (Inno Setup),
  `.github/workflows/build-windows.yml` (testes + build no Windows).

## Comandos
- Testes: `python -m unittest discover tests`
- Teste de um arquivo: `python -m unittest tests.test_animador`

## Economia de tokens
- Antes de ler um arquivo grande, localize com `grep -n` e leia só o trecho
  necessário (offset/limit). Nunca leia `interface.py` inteiro sem precisar.
- Não abra imagens (`docs/`, `recursos/`) a não ser que o pedido seja sobre elas.
- Rode só os testes do módulo alterado; a suíte inteira só no final.
- Respostas curtas, em português, sem repetir código que não mudou.
