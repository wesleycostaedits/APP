"""
Animador - presets de animação para o DaVinci Resolve (página Fusion).

Como usar: selecione o nó da imagem na página Fusion (MediaIn ou Loader),
abra Workspace > Scripts > Comp > Animador, escolha o preset e clique em
"Aplicar". O script insere os nós necessários (Transform, Blur ou
BrightnessContrast) logo depois do nó selecionado e cria os keyframes.
"Remover" apaga os nós criados pelo Animador nessa composição.

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


def ease_in_cubic(t):
    return t ** 3


def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_back(t):
    c1 = 1.70158
    return (c1 + 1) * t ** 3 - c1 * t ** 2


def ease_out_elastic(t):
    if t in (0, 1):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


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


# Oscilações: começam e terminam no valor inicial, por isso não aceitam troca
# de curva (veja gerar_keyframes).


def pulse(t):
    """Vai até o valor final no meio da animação e volta ao inicial."""
    return math.sin(math.pi * t)


def wobble(t):
    """Balança para os dois lados, perdendo força."""
    return math.sin(6 * math.pi * t) * (1 - t)


def shake(t):
    """Tremida irregular que vai parando."""
    return (math.sin(14 * math.pi * t) + 0.5 * math.sin(26 * math.pi * t)) / 1.5 * (1 - t)


def blink(t):
    """Duas piscadas."""
    return abs(math.sin(2 * math.pi * t))


OSCILACOES = (pulse, wobble, shake, blink)

# Curvas que o usuário pode escolher para substituir a do preset.
EASINGS = {
    "Linear": linear,
    "Suave": ease_in_out_sine,
    "Desacelerar": ease_out_cubic,
    "Acelerar": ease_in_cubic,
    "Voltar": ease_out_back,
    "Elástico": ease_out_elastic,
    "Quique": ease_out_bounce,
}

# ---------------------------------------------------------------------------
# Presets: cada trilha é (input, valor_inicial, valor_final, easing).
# "Center" usa pontos (x, y) em coordenadas do Fusion (0.5, 0.5 = centro).
# Center, Size e Angle animam um Transform; Gain anima um BrightnessContrast
# (opacidade) e XBlurSize anima um Blur.
# ---------------------------------------------------------------------------

CENTRO = (0.5, 0.5)

# Valor "em repouso" de cada input; a intensidade escala a distância até ele.
NEUTRO = {"Center": CENTRO, "Size": 1.0, "Angle": 0.0, "Gain": 1.0, "XBlurSize": 0.0}

ENTRADA, SAIDA, DESTAQUE, FOTOS = "Entradas", "Saídas", "Destaque", "Fotos"

# nome: (categoria, descrição, trilhas)
_CATALOGO = [
    # Entradas
    ("Fade In", ENTRADA, "Aparece suavemente",
     [("Gain", 0.0, 1.0, ease_in_out_sine)]),
    ("Deslizar da esquerda", ENTRADA, "Entra deslizando pela esquerda",
     [("Center", (-0.5, 0.5), CENTRO, ease_out_cubic)]),
    ("Deslizar da direita", ENTRADA, "Entra deslizando pela direita",
     [("Center", (1.5, 0.5), CENTRO, ease_out_cubic)]),
    ("Deslizar de baixo", ENTRADA, "Sobe deslizando de baixo",
     [("Center", (0.5, -0.5), CENTRO, ease_out_cubic)]),
    ("Deslizar de cima", ENTRADA, "Desce deslizando de cima",
     [("Center", (0.5, 1.5), CENTRO, ease_out_cubic)]),
    ("Surgir", ENTRADA, "Sobe um pouco enquanto aparece",
     [("Center", (0.5, 0.42), CENTRO, ease_out_cubic), ("Gain", 0.0, 1.0, ease_out_cubic)]),
    ("Zoom Pop", ENTRADA, "Cresce do zero com um estouro",
     [("Size", 0.0, 1.0, ease_out_back)]),
    ("Aproximar", ENTRADA, "Vem de perto da câmera até o lugar",
     [("Size", 1.6, 1.0, ease_out_cubic), ("Gain", 0.0, 1.0, ease_out_cubic)]),
    ("Quicar (cair do topo)", ENTRADA, "Cai do topo e quica até parar",
     [("Center", (0.5, 1.5), CENTRO, ease_out_bounce)]),
    ("Girar e aparecer", ENTRADA, "Gira enquanto cresce",
     [("Angle", -180.0, 0.0, ease_out_cubic), ("Size", 0.0, 1.0, ease_out_cubic)]),
    ("Desfoque de entrada", ENTRADA, "Sai do desfoque até ficar nítido",
     [("XBlurSize", 30.0, 0.0, ease_out_cubic), ("Gain", 0.0, 1.0, ease_out_cubic)]),
    # Saídas
    ("Fade Out", SAIDA, "Some suavemente",
     [("Gain", 1.0, 0.0, ease_in_out_sine)]),
    ("Sair pela esquerda", SAIDA, "Desliza para fora pela esquerda",
     [("Center", CENTRO, (-0.5, 0.5), ease_in_cubic)]),
    ("Sair pela direita", SAIDA, "Desliza para fora pela direita",
     [("Center", CENTRO, (1.5, 0.5), ease_in_cubic)]),
    ("Sair por baixo", SAIDA, "Desliza para fora por baixo",
     [("Center", CENTRO, (0.5, -0.5), ease_in_cubic)]),
    ("Sair por cima", SAIDA, "Desliza para fora por cima",
     [("Center", CENTRO, (0.5, 1.5), ease_in_cubic)]),
    ("Encolher", SAIDA, "Diminui até sumir",
     [("Size", 1.0, 0.0, ease_in_back)]),
    ("Girar e sumir", SAIDA, "Gira enquanto diminui",
     [("Angle", 0.0, 180.0, ease_in_cubic), ("Size", 1.0, 0.0, ease_in_cubic)]),
    ("Desfoque de saída", SAIDA, "Desfoca enquanto some",
     [("XBlurSize", 0.0, 30.0, ease_in_cubic), ("Gain", 1.0, 0.0, ease_in_cubic)]),
    # Destaque
    ("Pulsar", DESTAQUE, "Aumenta um pouco e volta",
     [("Size", 1.0, 1.15, pulse)]),
    ("Respirar", DESTAQUE, "Pulsação bem leve, para clipes longos",
     [("Size", 1.0, 1.05, pulse)]),
    ("Balançar", DESTAQUE, "Balança para os lados e para",
     [("Angle", 0.0, 12.0, wobble)]),
    ("Tremer", DESTAQUE, "Tremida rápida, como um impacto",
     [("Center", CENTRO, (0.53, 0.515), shake)]),
    ("Piscar", DESTAQUE, "Pisca duas vezes",
     [("Gain", 1.0, 0.15, blink)]),
    # Fotos
    ("Ken Burns", FOTOS, "Zoom lento aproximando, com movimento",
     [("Size", 1.0, 1.2, ease_in_out_sine),
      ("Center", CENTRO, (0.45, 0.52), ease_in_out_sine)]),
    ("Ken Burns (afastar)", FOTOS, "Zoom lento se afastando",
     [("Size", 1.2, 1.0, ease_in_out_sine),
      ("Center", (0.45, 0.52), CENTRO, ease_in_out_sine)]),
    ("Panorâmica para a esquerda", FOTOS, "Foto ampliada passando para a esquerda",
     [("Size", 1.2, 1.2, linear), ("Center", (0.56, 0.5), (0.44, 0.5), ease_in_out_sine)]),
    ("Panorâmica para a direita", FOTOS, "Foto ampliada passando para a direita",
     [("Size", 1.2, 1.2, linear), ("Center", (0.44, 0.5), (0.56, 0.5), ease_in_out_sine)]),
    ("Panorâmica para cima", FOTOS, "Foto ampliada subindo devagar",
     [("Size", 1.2, 1.2, linear), ("Center", (0.5, 0.56), (0.5, 0.44), ease_in_out_sine)]),
]

PRESETS = {nome: trilhas for nome, _, _, trilhas in _CATALOGO}
CATEGORIAS = {nome: (categoria, descricao) for nome, categoria, descricao, _ in _CATALOGO}


def interpolar(inicio, fim, progresso):
    if isinstance(inicio, tuple):
        return tuple(interpolar(a, b, progresso) for a, b in zip(inicio, fim))
    return inicio + (fim - inicio) * progresso


def escalar(valor, neutro, intensidade):
    """Aproxima ou afasta `valor` do repouso conforme a intensidade (1 = original)."""
    if isinstance(valor, tuple):
        return tuple(escalar(v, n, intensidade) for v, n in zip(valor, neutro))
    return neutro + (valor - neutro) * intensidade


def _limitar(nome, valor):
    if nome == "Gain":
        return max(0.0, min(1.0, valor))
    if nome in ("Size", "XBlurSize"):
        return max(0.0, valor)
    return valor


def gerar_keyframes(preset, frame_inicial, duracao, easing=None, intensidade=1.0):
    """Devolve {input: [(frame, valor), ...]} com um keyframe por frame.

    `easing` (um nome de EASINGS) substitui a curva do preset, exceto nas
    oscilações. `intensidade` aumenta (>1) ou suaviza (<1) o movimento.
    """
    if preset not in PRESETS:
        raise ValueError("Preset desconhecido: %s" % preset)
    if duracao < 1:
        raise ValueError("A duração precisa ser de pelo menos 1 frame")
    if easing is not None and easing not in EASINGS:
        raise ValueError("Curva desconhecida: %s" % easing)
    resultado = {}
    for nome, inicio, fim, curva in PRESETS[preset]:
        if easing is not None and curva not in OSCILACOES:
            curva = EASINGS[easing]
        neutro = NEUTRO[nome]
        inicio = escalar(inicio, neutro, intensidade)
        fim = escalar(fim, neutro, intensidade)
        keys = []
        for i in range(duracao + 1):
            valor = interpolar(inicio, fim, curva(i / duracao))
            keys.append((frame_inicial + i, _limitar(nome, valor)))
        resultado[nome] = keys
    return resultado


# ---------------------------------------------------------------------------
# Integração com o Fusion
# ---------------------------------------------------------------------------

PREFIXO = "Animador"  # nome dado aos nós criados, para poder removê-los depois

# input animado -> (tipo do nó, modificador)
NOS = {
    "Center": ("Transform", "XYPath"),
    "Size": ("Transform", "BezierSpline"),
    "Angle": ("Transform", "BezierSpline"),
    "XBlurSize": ("Blur", "BezierSpline"),
    "Gain": ("BrightnessContrast", "BezierSpline"),
}
ORDEM_NOS = ("Transform", "Blur", "BrightnessContrast")


def _nome_livre(comp, tipo):
    usados = {t.Name for t in (comp.GetToolList(False) or {}).values()}
    n = 1
    while "%s%s%d" % (PREFIXO, tipo, n) in usados:
        n += 1
    return "%s%s%d" % (PREFIXO, tipo, n)


def inserir_depois(comp, origem, tipo):
    """Cria um nó do tipo pedido logo depois de `origem`, mantendo as conexões."""
    destinos = list((origem.Output.GetConnectedInputs() or {}).values())
    novo = comp.AddTool(tipo, -32768, -32768)
    novo.SetAttrs({"TOOLS_Name": _nome_livre(comp, tipo)})
    novo.ConnectInput("Input", origem)
    for entrada in destinos:
        entrada.ConnectTo(novo.Output)
    return novo


def aplicar_preset(comp, ferramenta, preset, frame_inicial, duracao,
                   easing=None, intensidade=1.0):
    """Insere os nós do preset depois de `ferramenta`. Devolve o último nó criado."""
    keyframes = gerar_keyframes(preset, frame_inicial, duracao, easing, intensidade)
    comp.StartUndo("Animador: " + preset)
    comp.Lock()
    try:
        ultimo = ferramenta
        for tipo in ORDEM_NOS:
            inputs = [n for n in keyframes if NOS[n][0] == tipo]
            if not inputs:
                continue
            ultimo = inserir_depois(comp, ultimo, tipo)
            if tipo == "BrightnessContrast":
                ultimo.SetInput("ProcessAlpha", 1)
            for nome in inputs:
                ultimo.AddModifier(nome, NOS[nome][1])
                for frame, valor in keyframes[nome]:
                    if isinstance(valor, tuple):
                        valor = {1: valor[0], 2: valor[1]}
                    ultimo.SetInput(nome, valor, frame)
        return ultimo
    finally:
        comp.Unlock()
        comp.EndUndo(True)


def remover_animacoes(comp):
    """Remove os nós criados pelo Animador, religando a imagem. Devolve quantos."""
    nos = [t for t in (comp.GetToolList(False) or {}).values()
           if str(t.Name).startswith(PREFIXO)]
    if not nos:
        return 0
    comp.StartUndo("Animador: remover animações")
    comp.Lock()
    try:
        for no in nos:
            origem = no.Input.GetConnectedOutput()
            for entrada in list((no.Output.GetConnectedInputs() or {}).values()):
                if origem is not None:
                    entrada.ConnectTo(origem)
            no.Delete()
    finally:
        comp.Unlock()
        comp.EndUndo(True)
    return len(nos)


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
        {"ID": "AnimadorWin", "WindowTitle": "Animador", "Geometry": [200, 200, 360, 260]},
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
            ui.HGroup([
                ui.Label({"Text": "Curva:"}),
                ui.ComboBox({"ID": "Curva"}),
            ]),
            ui.HGroup([
                ui.Button({"ID": "Aplicar", "Text": "Aplicar"}),
                ui.Button({"ID": "Remover", "Text": "Remover animações"}),
            ]),
            ui.Label({"ID": "Status", "Text": "Selecione um nó e clique em Aplicar."}),
        ]),
    )
    itens = win.GetItems()
    for nome in PRESETS:
        itens["Preset"].AddItem(nome)
    itens["Curva"].AddItem("Padrão do preset")
    for nome in EASINGS:
        itens["Curva"].AddItem(nome)

    def ao_aplicar(ev):
        ferramenta = comp.ActiveTool
        if ferramenta is None:
            itens["Status"].Text = "Nenhum nó selecionado."
            return
        preset = itens["Preset"].CurrentText
        curva = itens["Curva"].CurrentText
        aplicar_preset(comp, ferramenta, preset, itens["Inicio"].Value,
                       itens["Duracao"].Value, None if curva not in EASINGS else curva)
        itens["Status"].Text = "'%s' aplicado em %s." % (preset, ferramenta.Name)

    def ao_remover(ev):
        n = remover_animacoes(comp)
        itens["Status"].Text = "%d nó(s) do Animador removidos." % n

    def ao_fechar(ev):
        disp.ExitLoop()

    win.On.Aplicar.Clicked = ao_aplicar
    win.On.Remover.Clicked = ao_remover
    win.On.AnimadorWin.Close = ao_fechar
    win.Show()
    disp.RunLoop()
    win.Hide()


# Dentro do Resolve o script pode não rodar como __main__, então checamos também
# se os objetos que o Resolve injeta estão presentes.
if __name__ == "__main__" or "bmd" in globals():
    abrir_janela()
