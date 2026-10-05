"""
Animador - presets de animação para o DaVinci Resolve (página Fusion).

Como usar: selecione o nó da imagem na página Fusion (MediaIn ou Loader),
abra Workspace > Scripts > Comp > Animador, escolha o preset e clique em
"Aplicar". O script insere um nó animado (Transform; BrightnessContrast para
fades; Blur para desfoque) logo depois do nó selecionado, com a curva feita
por um modificador AnimCurves.
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
    """Devolve {input: [(frame, valor), ...]} com um valor por frame (usado na prévia).

    `easing` (um nome de EASINGS) substitui a curva do preset, exceto nas
    oscilações. `intensidade` aumenta (>1) ou suaviza (<1) o movimento.
    """
    if duracao < 1:
        raise ValueError("A duração precisa ser de pelo menos 1 frame")
    resultado = {}
    for nome, inicio, fim, curva in gerar_trilhas(preset, easing, intensidade):
        resultado[nome] = [
            (frame_inicial + i, _limitar(nome, interpolar(inicio, fim, curva(i / duracao))))
            for i in range(duracao + 1)
        ]
    return resultado


# ---------------------------------------------------------------------------
# Integração com o Fusion
#
# Cada animação vira UM nó (Transform, BrightnessContrast ou Blur) cujos inputs
# são guiados por um modificador AnimCurves: uma rampa linear de tempo com só
# dois keyframes (0 no início, 1 no fim) passa pela curva escolhida (Easing,
# Elastic, Bounce...) e é convertida no valor final com Scale e Offset. As
# oscilações (Pulsar, Balançar...) usam um BezierSpline com keyframes.
# O nó é montado como texto de configuração do Fusion e colado na composição.
# ---------------------------------------------------------------------------

PREFIXO = "Animador"  # nome dado aos nós criados, para poder removê-los depois

# input animado -> tipo do nó
NOS = {
    "Center": "Transform",
    "Size": "Transform",
    "Angle": "Transform",
    "XBlurSize": "Blur",
    "Gain": "BrightnessContrast",
}
ORDEM_NOS = ("Transform", "Blur", "BrightnessContrast")

# curva do motor -> (Curve, EaseIn, EaseOut) do AnimCurves
CURVAS_FUSION = {
    linear: ("Linear", "Linear", "Linear"),
    ease_in_out_sine: ("Easing", "Sine", "Sine"),
    ease_out_cubic: ("Easing", "Linear", "Cubic"),
    ease_in_cubic: ("Easing", "Cubic", "Linear"),
    ease_out_back: ("Easing", "Linear", "Back"),
    ease_in_back: ("Easing", "Back", "Linear"),
    ease_out_elastic: ("Easing", "Linear", "Elastic"),
    ease_out_bounce: ("Easing", "Linear", "Bounce"),
}


def gerar_trilhas(preset, easing=None, intensidade=1.0):
    """[(input, inicio, fim, curva)] já com a curva e a intensidade aplicadas."""
    if preset not in PRESETS:
        raise ValueError("Preset desconhecido: %s" % preset)
    if easing is not None and easing not in EASINGS:
        raise ValueError("Curva desconhecida: %s" % easing)
    trilhas = []
    for nome, inicio, fim, curva in PRESETS[preset]:
        if easing is not None and curva not in OSCILACOES:
            curva = EASINGS[easing]
        neutro = NEUTRO[nome]
        trilhas.append((nome, escalar(inicio, neutro, intensidade),
                        escalar(fim, neutro, intensidade), curva))
    return trilhas


def _num(valor):
    return "%.6g" % valor


def _rampa(frame_inicial, duracao):
    """Tempo da animação: 0 no primeiro frame e 1 no último, em linha reta."""
    fim = frame_inicial + duracao
    terco = duracao / 3.0
    return ("BezierSpline {\n"
            "\t\t\tSplineColor = { Red = 104, Green = 195, Blue = 244 },\n"
            "\t\t\tNameSet = true,\n"
            "\t\t\tKeyFrames = {\n"
            "\t\t\t\t[%s] = { 0, RH = { %s, 0.333333333333333 }, Flags = { Linear = true } },\n"
            "\t\t\t\t[%s] = { 1, LH = { %s, 0.666666666666667 }, Flags = { Linear = true } }\n"
            "\t\t\t}\n"
            "\t\t}" % (frame_inicial, _num(frame_inicial + terco), fim, _num(fim - terco)))


LOOKUP_LINEAR = ("LUTBezier {\n"
                 "\t\t\tKeyColorSplines = {\n"
                 "\t\t\t\t[0] = {\n"
                 "\t\t\t\t\t[0] = { 0, RH = { 0.333333333333333, 0.333333333333333 }, "
                 "Flags = { Linear = true } },\n"
                 "\t\t\t\t\t[1] = { 1, LH = { 0.666666666666667, 0.666666666666667 }, "
                 "Flags = { Linear = true } }\n"
                 "\t\t\t\t}\n"
                 "\t\t\t},\n"
                 "\t\t\tSplineColor = { Red = 255, Green = 255, Blue = 255 },\n"
                 "\t\t\tNameSet = true,\n"
                 "\t\t}")


class _Setting:
    """Monta o texto `{ Tools = ordered() { ... } }` que o Fusion sabe colar."""

    def __init__(self):
        self.blocos = []

    def add(self, nome, corpo):
        self.blocos.append("\t\t%s = %s" % (nome, corpo))

    def animcurves(self, nome, inicio, fim, curva, frame_inicial, duracao):
        tipo, ease_in, ease_out = CURVAS_FUSION[curva]
        self.add(nome, (
            "LUTLookup {\n"
            "\t\t\tNameSet = true,\n"
            "\t\t\tInputs = {\n"
            "\t\t\t\tSource = Input { Value = FuID { \"Custom\" }, },\n"
            "\t\t\t\tInput = Input { SourceOp = \"%sTempo\", Source = \"Value\", },\n"
            "\t\t\t\tCurve = Input { Value = FuID { \"%s\" }, },\n"
            "\t\t\t\tEaseIn = Input { Value = FuID { \"%s\" }, },\n"
            "\t\t\t\tEaseOut = Input { Value = FuID { \"%s\" }, },\n"
            "\t\t\t\tScale = Input { Value = %s, },\n"
            "\t\t\t\tOffset = Input { Value = %s, },\n"
            "\t\t\t\tLookup = Input { SourceOp = \"%sLookup\", Source = \"Value\", },\n"
            "\t\t\t},\n"
            "\t\t}" % (nome, tipo, ease_in, ease_out, _num(fim - inicio), _num(inicio), nome)))
        self.add(nome + "Tempo", _rampa(frame_inicial, duracao))
        self.add(nome + "Lookup", LOOKUP_LINEAR)

    def keyframes(self, nome, inicio, fim, curva, frame_inicial, duracao, limitar):
        chaves = []
        for i in range(duracao + 1):
            valor = limitar(interpolar(inicio, fim, curva(i / duracao)))
            chaves.append("\t\t\t\t[%d] = { %s, Flags = { Linear = true } }"
                          % (frame_inicial + i, _num(valor)))
        self.add(nome, ("BezierSpline {\n"
                        "\t\t\tSplineColor = { Red = 225, Green = 255, Blue = 0 },\n"
                        "\t\t\tNameSet = true,\n"
                        "\t\t\tKeyFrames = {\n%s\n\t\t\t}\n"
                        "\t\t}" % ",\n".join(chaves)))

    def texto(self):
        return "{\n\tTools = ordered() {\n%s\n\t}\n}" % ",\n".join(self.blocos)


def montar_setting(tipo, nome, trilhas, frame_inicial, duracao, posicao=None):
    """Texto de configuração com UM nó `tipo` chamado `nome` e suas animações."""
    s = _Setting()
    entradas = []
    if tipo == "BrightnessContrast":
        entradas.append("\t\t\t\tProcessAlpha = Input { Value = 1, },")

    def animar_numero(chave, inicio, fim, curva, input_nome):
        if curva in OSCILACOES:
            s.keyframes(chave, inicio, fim, curva, frame_inicial, duracao,
                        lambda v: _limitar(input_nome, v))
        else:
            s.animcurves(chave, inicio, fim, curva, frame_inicial, duracao)

    modificadores = []
    for input_nome, inicio, fim, curva in trilhas:
        chave = "%s%s" % (nome, input_nome)
        if input_nome == "Center":
            # Ponto: um XYPath com X e Y animados separadamente.
            eixos = []
            for eixo, a, b in (("X", inicio[0], fim[0]), ("Y", inicio[1], fim[1])):
                if a == b and curva not in OSCILACOES:
                    eixos.append("\t\t\t\t%s = Input { Value = %s, }," % (eixo, _num(a)))
                    continue
                sub = chave + eixo
                modificadores.append((sub, a, b, curva, input_nome))
                eixos.append("\t\t\t\t%s = Input { SourceOp = \"%s\", Source = \"Value\", },"
                             % (eixo, sub))
            s_xy = ("XYPath {\n"
                    "\t\t\tShowKeyPoints = false,\n"
                    "\t\t\tDrawMode = \"ModifyOnly\",\n"
                    "\t\t\tNameSet = true,\n"
                    "\t\t\tInputs = {\n%s\n\t\t\t},\n"
                    "\t\t}" % "\n".join(eixos))
            modificadores.append((chave, s_xy, None, None, None))
            entradas.append("\t\t\t\tCenter = Input { SourceOp = \"%s\", Source = \"Value\", },"
                            % chave)
        elif inicio == fim and curva not in OSCILACOES:
            entradas.append("\t\t\t\t%s = Input { Value = %s, }," % (input_nome, _num(inicio)))
        else:
            modificadores.append((chave, inicio, fim, curva, input_nome))
            entradas.append("\t\t\t\t%s = Input { SourceOp = \"%s\", Source = \"Value\", },"
                            % (input_nome, chave))

    vista = ""
    if posicao:
        vista = "\t\t\tViewInfo = OperatorInfo { Pos = { %s, %s } },\n" % (
            _num(posicao[0]), _num(posicao[1]))
    s.add(nome, ("%s {\n"
                 "\t\t\tNameSet = true,\n"
                 "\t\t\tInputs = {\n%s\n\t\t\t},\n%s"
                 "\t\t}" % (tipo, "\n".join(entradas), vista)))
    for chave, inicio, fim, curva, input_nome in modificadores:
        if input_nome is None:
            s.add(chave, inicio)  # XYPath já montado
        else:
            animar_numero(chave, inicio, fim, curva, input_nome)
    return s.texto()


def _nome_livre(comp, tipo):
    usados = {t.Name for t in (comp.GetToolList(False) or {}).values()}
    n = 1
    while "%s%s%d" % (PREFIXO, tipo, n) in usados:
        n += 1
    return "%s%s%d" % (PREFIXO, tipo, n)


def _posicionar_depois(comp, origem, novo):
    """Coloca `novo` no Flow logo à direita de `origem` (se o Fusion permitir)."""
    try:
        flow = comp.CurrentFrame.FlowView
        pos = flow.GetPosTable(origem)
        flow.SetPos(novo, float(pos[1]) + 1, float(pos[2]))
    except Exception:
        pass


def colar(comp, texto):
    """Cola um texto de configuração na composição (via Lua, que tem bmd.readstring)."""
    comp.Execute("comp:Paste(bmd.readstring([==[%s]==]))" % texto)


def inserir_depois(comp, origem, tipo, trilhas, frame_inicial, duracao):
    """Cria o nó animado logo depois de `origem`, mantendo as conexões."""
    nome = _nome_livre(comp, tipo)
    destinos = list((origem.Output.GetConnectedInputs() or {}).values())
    colar(comp, montar_setting(tipo, nome, trilhas, frame_inicial, duracao))
    novo = comp.FindTool(nome)
    if novo is None:
        raise RuntimeError("O Fusion não criou o nó %s." % nome)
    _posicionar_depois(comp, origem, novo)
    novo.ConnectInput("Input", origem)
    for entrada in destinos:
        entrada.ConnectTo(novo.Output)
    return novo


def aplicar_preset(comp, ferramenta, preset, frame_inicial, duracao,
                   easing=None, intensidade=1.0):
    """Insere o nó do preset depois de `ferramenta`. Devolve o último nó criado.

    Animações de movimento, tamanho e rotação usam um único Transform; fade usa
    um BrightnessContrast e desfoque um Blur.
    """
    if duracao < 1:
        raise ValueError("A duração precisa ser de pelo menos 1 frame")
    trilhas = gerar_trilhas(preset, easing, intensidade)
    comp.StartUndo("Animador: " + preset)
    comp.Lock()
    try:
        ultimo = ferramenta
        for tipo in ORDEM_NOS:
            do_tipo = [t for t in trilhas if NOS[t[0]] == tipo]
            if do_tipo:
                ultimo = inserir_depois(comp, ultimo, tipo, do_tipo, frame_inicial, duracao)
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
