# Animador para DaVinci Resolve

Script em Python que adiciona uma janela ao DaVinci Resolve para aplicar
animações prontas a **imagens** (e a qualquer outro nó) na página **Fusion**,
em um clique.

## Presets

| Preset | O que faz |
| --- | --- |
| Fade In / Fade Out | Aparece ou some suavemente |
| Deslizar da esquerda / direita / de baixo | Entra deslizando até o centro |
| Zoom Pop | Cresce do zero com um leve "estouro" |
| Quicar (cair do topo) | Cai do topo e quica até parar |
| Girar e aparecer | Gira 180° enquanto cresce |
| Pulsar | Aumenta um pouco e volta (bom para destacar) |
| Ken Burns | Zoom lento com leve movimento, clássico para fotos |

Existem duas formas de usar:

- **Animador App** (`AnimadorApp.py`): programa com janela própria que se
  conecta ao DaVinci e anima vários clipes da timeline de uma vez.
  Precisa do **DaVinci Resolve Studio**.
- **Script no DaVinci** (`Animador.py`): janela dentro do DaVinci que anima o
  nó selecionado na página Fusion. Funciona também na versão gratuita.

## Animador App (programa com janela)

![Tela do Animador App](docs/tela.png)

Escolha a animação nos cartões e veja a **prévia ao vivo** antes de aplicar.

### Preparar (só uma vez)

1. Instale o Python 3 (64 bits) em https://www.python.org/downloads/ e, na
   instalação, marque **"Add python.exe to PATH"**.
2. No DaVinci Resolve Studio, abra **Preferences → System → General** e mude
   **External scripting using** para **Local**. Reinicie o DaVinci.
3. O app usa a biblioteca **PySide6** (Qt) para a interface. O
   `Abrir Animador.bat` instala ela sozinho na primeira vez. Para instalar
   manualmente: `pip install -r requirements.txt`.
4. Baixe a pasta do projeto (no GitHub: **Code → Download ZIP**) e extraia.
   Os arquivos `AnimadorApp.py`, `Animador.py`, `requirements.txt` e
   `Abrir Animador.bat` precisam ficar na mesma pasta.

### Usar

1. Abra o DaVinci com o projeto e a timeline que tem as imagens.
2. Dê dois cliques em **`Abrir Animador.bat`**.
3. Clique em **Conectar / Atualizar**: os clipes da timeline aparecem na lista.
4. Selecione os clipes (Ctrl/Shift para vários, ou **Selecionar todos**).
5. Escolha o preset, a duração e se a animação fica no início ou no fim do
   clipe, e clique em **Aplicar nos clipes selecionados**.

Cada clipe ganha uma composição Fusion com a animação (se já tiver uma, ela é
usada). Para ver ou ajustar, clique no clipe e abra a página **Fusion**.

## Script no DaVinci

### Instalação

Copie `Animador.py` para a pasta de scripts do Fusion:

- **Windows:** `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp\`
- **macOS:** `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/`
- **Linux:** `~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/`

Reinicie o DaVinci Resolve. Na versão gratuita, scripts com interface só rodam
de dentro do programa (pelo menu), que é exatamente como este funciona.

### Como usar

1. Coloque a imagem na timeline, clique nela e abra a página **Fusion**.
   Selecione o nó da imagem (`MediaIn1`). Também funciona com `Loader`,
   `Text+` ou qualquer outro nó.
2. Abra **Workspace → Scripts → Comp → Animador**.
3. Escolha o preset, o frame inicial e a duração, e clique em **Aplicar**.

O Animador insere um nó `Transform` (e um `BrightnessContrast` para fades)
logo depois do nó selecionado, sem quebrar as conexões. Tudo entra como uma
única ação, então **Ctrl+Z** desfaz.

## Testes

A lógica das animações é testada fora do DaVinci:

```
python3 -m unittest discover tests
```
