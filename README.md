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

## Instalação

Copie `Animador.py` para a pasta de scripts do Fusion:

- **Windows:** `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp\`
- **macOS:** `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/`
- **Linux:** `~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/`

Reinicie o DaVinci Resolve. Na versão gratuita, scripts com interface só rodam
de dentro do programa (pelo menu), que é exatamente como este funciona.

## Como usar

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
