"""
Animador - presets de animação para o DaVinci Resolve (página Fusion).

Como usar: selecione o nó da imagem na página Fusion (MediaIn ou Loader),
abra Workspace > Scripts > Comp > Animador, escolha o preset e clique em
"Aplicar". O script insere um nó Transform (e, para fades, um
BrightnessContrast) logo depois do nó selecionado e cria os keyframes.

A parte de cálculo (easings e presets) não depende do DaVinci, então pode ser
testada fora dele: veja tests/test_animador.py.
"""

import math

# ---------------------------------------------------------------------------
# Easings: recebem t entre 0 e 1 e devolvem o progresso da animação.
# ---------------------------------------------------------------------------


def linear(t):
    return t


def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def pulse(t):
    """Vai até o valor final no meio da animação e volta ao inicial."""
    return math.sin(math.pi * t)


# ---------------------------------------------------------------------------
# Presets: cada trilha é (input, valor_inicial, valor_final, easing).
# "Center" usa pontos (x, y) em coordenadas do Fusion (0.5, 0.5 = centro).
# "Gain" anima o nó de fade (BrightnessContrast); o resto anima o Transform.
# ---------------------------------------------------------------------------

CENTRO = (0.5, 0.5)

PRESETS = {
    "Fade In": [("Gain", 0.0, 1.0, ease_in_out_sine)],
    "Fade Out": [("Gain", 1.0, 0.0, ease_in_out_sine)],
    "Deslizar da esquerda": [("Center", (-0.5, 0.5), CENTRO, ease_out_cubic)],
    "Deslizar da direita": [("Center", (1.5, 0.5), CENTRO, ease_out_cubic)],
    "Deslizar de baixo": [("Center", (0.5, -0.5), CENTRO, ease_out_cubic)],
    "Zoom Pop": [("Size", 0.0, 1.0, ease_out_back)],
    "Quicar (cair do topo)": [("Center", (0.5, 1.5), CENTRO, ease_out_bounce)],
    "Girar e aparecer": [
        ("Angle", -180.0, 0.0, ease_out_cubic),
        ("Size", 0.0, 1.0, ease_out_cubic),
    ],
    "Pulsar": [("Size", 1.0, 1.15, pulse)],
    # Clássico para fotos: zoom lento com um leve deslocamento.
    "Ken Burns": [
        ("Size", 1.0, 1.2, ease_in_out_sine),
        ("Center", CENTRO, (0.45, 0.52), ease_in_out_sine),
    ],
}


def interpolar(inicio, fim, progresso):
    if isinstance(inicio, tuple):
        return tuple(interpolar(a, b, progresso) for a, b in zip(inicio, fim))
    return inicio + (fim - inicio) * progresso


def gerar_keyframes(preset, frame_inicial, duracao):
    """Devolve {input: [(frame, valor), ...]} com um keyframe por frame."""
    if preset not in PRESETS:
        raise ValueError("Preset desconhecido: %s" % preset)
    if duracao < 1:
        raise ValueError("A duração precisa ser de pelo menos 1 frame")
    resultado = {}
    for nome, inicio, fim, easing in PRESETS[preset]:
        keys = []
        for i in range(duracao + 1):
            progresso = easing(i / duracao)
            keys.append((frame_inicial + i, interpolar(inicio, fim, progresso)))
        resultado[nome] = keys
    return resultado


# ---------------------------------------------------------------------------
# Integração com o Fusion
# ---------------------------------------------------------------------------


def inserir_depois(comp, origem, tipo):
    """Cria um nó do tipo pedido logo depois de `origem`, mantendo as conexões."""
    destinos = list((origem.Output.GetConnectedInputs() or {}).values())
    novo = comp.AddTool(tipo, -32768, -32768)
    novo.ConnectInput("Input", origem)
    for entrada in destinos:
        entrada.ConnectTo(novo.Output)
    return novo


def aplicar_preset(comp, ferramenta, preset, frame_inicial, duracao):
    keyframes = gerar_keyframes(preset, frame_inicial, duracao)
    comp.StartUndo("Animador: " + preset)
    comp.Lock()
    try:
        ultimo = ferramenta
        transform_inputs = {k: v for k, v in keyframes.items() if k != "Gain"}
        if transform_inputs:
            ultimo = inserir_depois(comp, ultimo, "Transform")
            for nome, keys in transform_inputs.items():
                ultimo.AddModifier(nome, "XYPath" if nome == "Center" else "BezierSpline")
                for frame, valor in keys:
                    if isinstance(valor, tuple):
                        valor = {1: valor[0], 2: valor[1]}
                    ultimo.SetInput(nome, valor, frame)
        if "Gain" in keyframes:
            fade = inserir_depois(comp, ultimo, "BrightnessContrast")
            fade.SetInput("ProcessAlpha", 1)
            fade.AddModifier("Gain", "BezierSpline")
            for frame, valor in keyframes["Gain"]:
                fade.SetInput("Gain", valor, frame)
    finally:
        comp.Unlock()
        comp.EndUndo(True)


def obter_fusion():
    """Encontra o objeto `fusion`, seja rodando dentro do Resolve ou fora dele."""
    fu = globals().get("fusion") or globals().get("fu")
    if fu:
        return fu
    bmd_mod = globals().get("bmd")
    if bmd_mod:
        return bmd_mod.scriptapp("Fusion")
    import DaVinciResolveScript as dvr  # disponível com o Resolve aberto

    return dvr.scriptapp("Resolve").Fusion()


def abrir_janela():
    fu = obter_fusion()
    comp = fu.GetCurrentComp()
    if comp is None:
        print("Abra a página Fusion antes de rodar o Animador.")
        return

    ui = fu.UIManager
    disp = bmd.UIDispatcher(ui)  # noqa: F821 - `bmd` existe dentro do Resolve
    win = disp.AddWindow(
        {"ID": "AnimadorWin", "WindowTitle": "Animador", "Geometry": [200, 200, 340, 200]},
        ui.VGroup([
            ui.Label({"Text": "Preset de animação:"}),
            ui.ComboBox({"ID": "Preset"}),
            ui.HGroup([
                ui.Label({"Text": "Frame inicial:"}),
                ui.SpinBox({"ID": "Inicio", "Minimum": -100000, "Maximum": 100000,
                            "Value": int(comp.CurrentTime)}),
            ]),
            ui.HGroup([
                ui.Label({"Text": "Duração (frames):"}),
                ui.SpinBox({"ID": "Duracao", "Minimum": 1, "Maximum": 1000, "Value": 24}),
            ]),
            ui.Button({"ID": "Aplicar", "Text": "Aplicar"}),
            ui.Label({"ID": "Status", "Text": "Selecione um nó e clique em Aplicar."}),
        ]),
    )
    itens = win.GetItems()
    for nome in PRESETS:
        itens["Preset"].AddItem(nome)

    def ao_aplicar(ev):
        ferramenta = comp.ActiveTool
        if ferramenta is None:
            itens["Status"].Text = "Nenhum nó selecionado."
            return
        preset = itens["Preset"].CurrentText
        aplicar_preset(comp, ferramenta, preset,
                       itens["Inicio"].Value, itens["Duracao"].Value)
        itens["Status"].Text = "'%s' aplicado em %s." % (preset, ferramenta.Name)

    def ao_fechar(ev):
        disp.ExitLoop()

    win.On.Aplicar.Clicked = ao_aplicar
    win.On.AnimadorWin.Close = ao_fechar
    win.Show()
    disp.RunLoop()
    win.Hide()


# Dentro do Resolve o script pode não rodar como __main__, então checamos também
# se os objetos que o Resolve injeta estão presentes.
if __name__ == "__main__" or "bmd" in globals():
    abrir_janela()
