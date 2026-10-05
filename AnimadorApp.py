"""
Animador App - programa com janela que controla o DaVinci Resolve Studio.

Lista os clipes da timeline aberta, e aplica os presets do Animador.py nos
clipes selecionados (cada clipe ganha uma composição Fusion com a animação).

Requisitos:
- DaVinci Resolve Studio aberto, com um projeto e uma timeline.
- Em Preferences > System > General, "External scripting using" = Local.
- Python 3 (64 bits) e PySide6 (pip install -r requirements.txt).
  Rode: python AnimadorApp.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import Animador  # noqa: E402

POSICOES = ("Início do clipe", "Fim do clipe")


# ---------------------------------------------------------------------------
# Conexão com o DaVinci Resolve
# ---------------------------------------------------------------------------


def _caminhos_padrao():
    if sys.platform.startswith("win"):
        programdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        modulos = os.path.join(programdata, "Blackmagic Design", "DaVinci Resolve",
                               "Support", "Developer", "Scripting", "Modules")
        lib = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
    elif sys.platform == "darwin":
        modulos = ("/Library/Application Support/Blackmagic Design/DaVinci Resolve/"
                   "Developer/Scripting/Modules")
        lib = ("/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/"
               "Libraries/Fusion/fusionscript.so")
    else:
        modulos = "/opt/resolve/Developer/Scripting/Modules"
        lib = "/opt/resolve/libs/Fusion/fusionscript.so"
    return modulos, lib


def conectar_resolve():
    """Devolve o objeto `resolve` ou levanta RuntimeError com uma mensagem clara."""
    modulos, lib = _caminhos_padrao()
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    if modulos not in sys.path:
        sys.path.append(modulos)
    try:
        import DaVinciResolveScript as dvr
    except ImportError:
        raise RuntimeError("Não encontrei a API do DaVinci Resolve. "
                           "O DaVinci Resolve está instalado?")
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Não consegui conectar. Verifique se o DaVinci Resolve Studio "
                           "está aberto e se 'External scripting using' está em Local "
                           "(Preferences > System > General).")
    return resolve


def timeline_atual(resolve):
    projeto = resolve.GetProjectManager().GetCurrentProject()
    if projeto is None:
        raise RuntimeError("Nenhum projeto aberto no DaVinci.")
    timeline = projeto.GetCurrentTimeline()
    if timeline is None:
        raise RuntimeError("Nenhuma timeline aberta no projeto.")
    return timeline


def listar_clipes(timeline):
    """Devolve [(trilha, item), ...] com os clipes de todas as trilhas de vídeo."""
    clipes = []
    for trilha in range(1, int(timeline.GetTrackCount("video")) + 1):
        for item in timeline.GetItemListInTrack("video", trilha) or []:
            clipes.append((trilha, item))
    return clipes


# ---------------------------------------------------------------------------
# Aplicar animação num clipe da timeline
# ---------------------------------------------------------------------------


def comp_do_clipe(item):
    """Usa a primeira composição Fusion do clipe, criando uma se não existir."""
    if item.GetFusionCompCount() > 0:
        return item.GetFusionCompByIndex(1)
    comp = item.AddFusionComp()
    if comp is None:
        raise RuntimeError("Não consegui criar a composição Fusion em %s." % item.GetName())
    return comp


def media_in(comp):
    ferramentas = comp.GetToolList(False, "MediaIn") or {}
    if not ferramentas:
        raise RuntimeError("A composição não tem nó MediaIn.")
    return list(ferramentas.values())[0]


def intervalo_comp(comp, item):
    attrs = comp.GetAttrs() or {}
    inicio = attrs.get("COMPN_RenderStart")
    fim = attrs.get("COMPN_RenderEnd")
    if inicio is None or fim is None:
        inicio, fim = 0, int(item.GetDuration()) - 1
    return int(inicio), int(fim)


def aplicar_em_clipe(item, preset, duracao, posicao):
    comp = comp_do_clipe(item)
    inicio, fim = intervalo_comp(comp, item)
    duracao = max(1, min(int(duracao), fim - inicio))
    frame = inicio if posicao == POSICOES[0] else fim - duracao
    Animador.aplicar_preset(comp, media_in(comp), preset, frame, duracao)


# ---------------------------------------------------------------------------
# Interface (PySide6 / Qt)
# ---------------------------------------------------------------------------

VERSAO = "1.0"

# Categoria e descrição de cada preset (usadas na barra lateral, cartões e busca).
INFO_PRESETS = {
    "Fade In": ("Entradas", "Aparece suavemente"),
    "Deslizar da esquerda": ("Entradas", "Entra deslizando pela esquerda"),
    "Deslizar da direita": ("Entradas", "Entra deslizando pela direita"),
    "Deslizar de baixo": ("Entradas", "Sobe deslizando de baixo"),
    "Zoom Pop": ("Entradas", "Cresce do zero com um estouro"),
    "Quicar (cair do topo)": ("Entradas", "Cai do topo e quica até parar"),
    "Girar e aparecer": ("Entradas", "Gira enquanto cresce"),
    "Fade Out": ("Saídas", "Some suavemente"),
    "Pulsar": ("Destaque", "Aumenta um pouco e volta"),
    "Ken Burns": ("Fotos", "Zoom lento com movimento"),
}

# (seção, [(ícone, nome do filtro)])
NAVEGACAO = [
    ("Biblioteca", [("▦", "Todos"), ("☆", "Favoritos")]),
    ("Categorias", [("↗", "Entradas"), ("↘", "Saídas"), ("✦", "Destaque"), ("▣", "Fotos")]),
]


def info_preset(nome):
    return INFO_PRESETS.get(nome, ("Outros", ""))


def filtrar_presets(filtro, busca, favoritos):
    """Nomes dos presets que aparecem para o filtro da barra lateral e a busca."""
    busca = busca.strip().lower()
    nomes = []
    for nome in Animador.PRESETS:
        categoria, descricao = info_preset(nome)
        if filtro == "Favoritos" and nome not in favoritos:
            continue
        if filtro not in ("Todos", "Favoritos") and categoria != filtro:
            continue
        if busca and busca not in (nome + " " + descricao + " " + categoria).lower():
            continue
        nomes.append(nome)
    return nomes


ESTILO = """
* { font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; color: #e9e9ec; }
QLabel { background: transparent; }
QFrame#lateral { background: rgba(18, 18, 20, 235); border-right: 1px solid #232327; }
QFrame#categorias { background: rgba(22, 22, 25, 200); border-right: 1px solid #232327; }
QFrame#topo { border-bottom: 1px solid #232327; }
QFrame#rodape { border-top: 1px solid #232327; }
QFrame#painel { background: rgba(20, 20, 23, 220); border-left: 1px solid #232327; }
QLabel#logo { font-size: 16px; font-weight: 700; }
QLabel#titulo { font-size: 15px; font-weight: 700; }
QLabel#subtitulo, QLabel#dica { color: #77777f; }
QLabel#secao { color: #66666e; font-size: 10px; font-weight: 600; letter-spacing: 1.5px; }
QLabel#mono, QLabel#contagem {
    color: #77777f; font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 10px; letter-spacing: 1px;
}
QPushButton#nav {
    background: transparent; border: 1px solid transparent; border-radius: 8px;
    padding: 7px 10px; text-align: left; color: #b8b8be;
}
QPushButton#nav:hover { background: #1d1d21; color: #ffffff; }
QPushButton#nav:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a2014, stop:1 #241a16);
    border: 1px solid #5a3420; color: #ffffff; font-weight: 600;
}
QLineEdit {
    background: #161619; border: 1px solid #2a2a2f; border-radius: 9px;
    padding: 8px 12px; selection-background-color: #ff6a1a;
}
QLineEdit:focus { border-color: #ff6a1a; }
QLineEdit#buscaGrande {
    background: rgba(30, 22, 18, 200); border: 1px solid #6a3a20; padding: 11px 14px;
}
QPushButton {
    background: #18181b; border: 1px solid #2a2a2f; border-radius: 9px;
    padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: #202024; border-color: #3a3a40; }
QFrame#cartao { background: #1a1a1d; border: 1px solid #232327; border-radius: 12px; }
QFrame#cartao:hover { border-color: #3a3a40; }
QFrame#cartao[selecionado="true"] { border: 1px solid #ff6a1a; }
QLabel#nomeCartao { font-size: 13px; font-weight: 700; }
QToolButton#estrela {
    background: rgba(0, 0, 0, 120); border: none; border-radius: 13px;
    color: #77777f; font-size: 14px;
}
QToolButton#estrela:checked { color: #ffb020; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item {
    background: #18181b; border: 1px solid #232327; border-radius: 8px;
    padding: 8px 10px; margin: 2px 0;
}
QListWidget::item:hover { border-color: #3a3a40; }
QListWidget::item:selected { background: #2e1c14; border-color: #ff6a1a; color: #ffffff; }
QPushButton#segmento { padding: 7px; }
QPushButton#segmento:checked { background: #2e1c14; border-color: #ff6a1a; color: #ffffff; }
QPushButton#aplicar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5a14, stop:1 #ff8a2a);
    color: white; border: none; border-radius: 10px; padding: 12px; font-size: 14px;
}
QPushButton#aplicar:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6a28, stop:1 #ff9a40);
}
QPushButton#aplicar:disabled { background: #1d1d21; color: #55555c; }
QSpinBox {
    background: #161619; border: 1px solid #2a2a2f; border-radius: 8px;
    padding: 6px 10px; min-width: 80px;
}
QSlider::groove:horizontal { height: 4px; background: #2a2a2f; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #ff6a1a; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #ffffff; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #3a3a40; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""

CORES_STATUS = {
    "info": "#77777f",
    "ok": "#4ade80",
    "erro": "#ff7070",
}


def criar_janela():
    from PySide6.QtCore import QPointF, QRectF, QSettings, Qt, QTimer
    from PySide6.QtGui import (
        QColor, QLinearGradient, QPainter, QPainterPath, QRadialGradient,
    )
    from PySide6.QtWidgets import (
        QAbstractItemView, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
        QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
        QScrollArea, QSizePolicy, QSlider, QSpinBox, QToolButton, QVBoxLayout,
        QWidget,
    )

    class Previa(QWidget):
        """Desenha uma 'foto' de exemplo animada com os keyframes do preset."""

        PAUSA = 18  # frames parados no fim antes de repetir

        def __init__(self, preset, duracao=24):
            super().__init__()
            self.setMinimumHeight(128)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.frame = 0
            self.definir(preset, duracao)

        def definir(self, preset, duracao):
            self.keys = Animador.gerar_keyframes(preset, 0, duracao)
            self.duracao = duracao
            self.update()

        def tick(self, global_frame):
            self.frame = global_frame % (self.duracao + 1 + self.PAUSA)
            self.update()

        def valor(self, nome, padrao):
            if nome not in self.keys:
                return padrao
            return self.keys[nome][min(self.frame, self.duracao)][1]

        def paintEvent(self, evento):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            area = QRectF(self.rect())
            fundo = QPainterPath()
            r = 11
            # Só os cantos de cima arredondados, como no topo do cartão.
            fundo.moveTo(area.left(), area.bottom())
            fundo.lineTo(area.left(), area.top() + r)
            fundo.quadTo(area.left(), area.top(), area.left() + r, area.top())
            fundo.lineTo(area.right() - r, area.top())
            fundo.quadTo(area.right(), area.top(), area.right(), area.top() + r)
            fundo.lineTo(area.right(), area.bottom())
            fundo.closeSubpath()
            p.fillPath(fundo, QColor("#000000"))
            p.setClipPath(fundo)

            larg, alt = area.width(), area.height()
            cx, cy = self.valor("Center", (0.5, 0.5))
            tamanho = self.valor("Size", 1.0)
            angulo = self.valor("Angle", 0.0)
            opacidade = max(0.0, min(1.0, self.valor("Gain", 1.0)))

            p.translate(cx * larg, (1 - cy) * alt)
            p.rotate(-angulo)
            p.scale(tamanho, tamanho)
            p.setOpacity(opacidade)

            h = alt * 0.52
            foto = QRectF(-h * 0.8, -h / 2, h * 1.6, h)
            ceu = QLinearGradient(foto.topLeft(), foto.bottomLeft())
            ceu.setColorAt(0, QColor("#ff9a3d"))
            ceu.setColorAt(1, QColor("#ff4f6d"))
            moldura = QPainterPath()
            moldura.addRoundedRect(foto, 6, 6)
            p.fillPath(moldura, ceu)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 240, 200))
            p.drawEllipse(QPointF(foto.right() - foto.width() * 0.25,
                                  foto.top() + foto.height() * 0.3),
                          foto.height() * 0.12, foto.height() * 0.12)
            montanha = QPainterPath()
            montanha.moveTo(foto.left(), foto.bottom())
            montanha.lineTo(foto.left() + foto.width() * 0.35, foto.top() + foto.height() * 0.45)
            montanha.lineTo(foto.left() + foto.width() * 0.6, foto.top() + foto.height() * 0.75)
            montanha.lineTo(foto.left() + foto.width() * 0.75, foto.top() + foto.height() * 0.6)
            montanha.lineTo(foto.right(), foto.bottom())
            montanha.closeSubpath()
            p.setClipPath(moldura, Qt.IntersectClip)
            p.fillPath(montanha, QColor(60, 20, 50, 200))

    class Cartao(QFrame):
        def __init__(self, nome, ao_clicar, ao_favoritar):
            super().__init__()
            self.nome = nome
            self.ao_clicar = ao_clicar
            self.setObjectName("cartao")
            self.setCursor(Qt.PointingHandCursor)
            self.setMinimumWidth(160)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            self.previa = Previa(nome)
            categoria, descricao = info_preset(nome)
            self.setToolTip(descricao)
            titulo = QLabel(nome)
            titulo.setObjectName("nomeCartao")
            self.tags = QLabel()
            self.tags.setObjectName("mono")
            self.definir_duracao(24)

            texto = QVBoxLayout()
            texto.setContentsMargins(12, 10, 12, 12)
            texto.setSpacing(4)
            texto.addWidget(titulo)
            texto.addWidget(self.tags)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(1, 1, 1, 1)
            layout.setSpacing(0)
            layout.addWidget(self.previa)
            layout.addLayout(texto)

            self.estrela = QToolButton(self.previa)
            self.estrela.setObjectName("estrela")
            self.estrela.setText("★")
            self.estrela.setCheckable(True)
            self.estrela.setFixedSize(26, 26)
            self.estrela.setCursor(Qt.PointingHandCursor)
            self.estrela.setToolTip("Favoritar")
            self.estrela.toggled.connect(lambda marcado: ao_favoritar(nome, marcado))

        def definir_duracao(self, duracao):
            categoria, _ = info_preset(self.nome)
            self.tags.setText('<span style="color:#ff6a1a">%s</span>  ·  %dF'
                              % (categoria.upper(), duracao))

        def selecionar(self, sim):
            self.setProperty("selecionado", sim)
            self.style().unpolish(self)
            self.style().polish(self)

        def resizeEvent(self, evento):
            super().resizeEvent(evento)
            self.estrela.move(self.previa.width() - 34, 8)

        def mousePressEvent(self, evento):
            self.ao_clicar(self.nome)

    def rotulo(texto, nome="secao"):
        r = QLabel(texto.upper() if nome == "secao" else texto)
        r.setObjectName(nome)
        return r

    def linha_divisoria():
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet("background: #232327;")
        return d

    class JanelaAnimador(QWidget):
        def __init__(self):
            super().__init__()
            self.resolve = None
            self.filtro = "Todos"
            self.selecionado = None
            self.global_frame = 0
            self.config = QSettings("Animador", "AnimadorApp")
            favs = self.config.value("favoritos", []) or []
            self.favoritos = set([favs] if isinstance(favs, str) else favs)

            self.setWindowTitle("Animador para DaVinci Resolve")
            self.resize(1440, 820)
            self.setMinimumSize(1080, 640)
            self.setStyleSheet(ESTILO)

            raiz = QHBoxLayout(self)
            raiz.setContentsMargins(0, 0, 0, 0)
            raiz.setSpacing(0)
            raiz.addWidget(self.criar_lateral())
            centro = QVBoxLayout()
            centro.setSpacing(0)
            centro.addWidget(self.criar_topo())
            meio = QHBoxLayout()
            meio.setSpacing(0)
            meio.addWidget(self.criar_categorias())
            meio.addWidget(self.criar_grade(), 1)
            meio.addWidget(self.criar_painel())
            centro.addLayout(meio, 1)
            centro.addWidget(self.criar_rodape())
            raiz.addLayout(centro, 1)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.animar)
            self.timer.start(1000 // 30)

            self.selecionar(next(iter(Animador.PRESETS)))
            self.aplicar_filtro()
            self.mostrar_lista(False)
            self.atualizar_botao()
            self.definir_conexao(None)

        # -- montagem da tela -------------------------------------------------

        def criar_lateral(self):
            lateral = QFrame()
            lateral.setObjectName("lateral")
            lateral.setFixedWidth(190)
            v = QVBoxLayout(lateral)
            v.setContentsMargins(14, 16, 14, 14)
            v.setSpacing(4)
            logo = QLabel('<span style="color:#ff6a1a">●</span>&nbsp; Animador')
            logo.setObjectName("logo")
            v.addWidget(logo)
            v.addSpacing(18)
            principal = QPushButton("▦    Animações")
            principal.setObjectName("nav")
            principal.setCheckable(True)
            principal.setChecked(True)
            v.addWidget(principal)
            v.addSpacing(14)
            v.addWidget(rotulo("Atalhos"))
            conectar = QPushButton("⟳    Conectar")
            conectar.setObjectName("nav")
            conectar.clicked.connect(self.atualizar)
            v.addWidget(conectar)
            todos = QPushButton("☰    Todos os clipes")
            todos.setObjectName("nav")
            todos.clicked.connect(lambda: self.lista.selectAll())
            v.addWidget(todos)
            v.addStretch()
            v.addWidget(linha_divisoria())
            v.addSpacing(6)
            v.addWidget(rotulo("Para DaVinci Resolve", "dica"))
            return lateral

        def criar_topo(self):
            topo = QFrame()
            topo.setObjectName("topo")
            topo.setFixedHeight(64)
            h = QHBoxLayout(topo)
            h.setContentsMargins(18, 0, 18, 0)
            h.addWidget(rotulo("Animações", "titulo"))
            h.addSpacing(6)
            h.addWidget(rotulo("escolha a animação, depois aplique nos clipes", "subtitulo"))
            h.addStretch()
            self.busca_topo = QLineEdit()
            self.busca_topo.setPlaceholderText("⌕  Buscar")
            self.busca_topo.setFixedWidth(220)
            h.addWidget(self.busca_topo)
            self.botao_conectar = QPushButton("⟳  Conectar")
            self.botao_conectar.clicked.connect(self.atualizar)
            h.addWidget(self.botao_conectar)
            return topo

        def criar_categorias(self):
            quadro = QFrame()
            quadro.setObjectName("categorias")
            quadro.setFixedWidth(160)
            v = QVBoxLayout(quadro)
            v.setContentsMargins(10, 14, 10, 14)
            v.setSpacing(2)
            self.navs = QButtonGroup(self)
            self.contagens = {}
            for i, (secao, itens) in enumerate(NAVEGACAO):
                if i:
                    v.addSpacing(8)
                    v.addWidget(linha_divisoria())
                    v.addSpacing(8)
                v.addWidget(rotulo(secao))
                v.addSpacing(4)
                for icone, nome in itens:
                    botao = QPushButton("%s    %s" % (icone, nome))
                    botao.setObjectName("nav")
                    botao.setCheckable(True)
                    botao.setChecked(nome == self.filtro)
                    botao.clicked.connect(lambda _=False, n=nome: self.mudar_filtro(n))
                    contagem = rotulo("", "contagem")
                    contagem.setAttribute(Qt.WA_TransparentForMouseEvents)
                    linha = QHBoxLayout(botao)
                    linha.setContentsMargins(0, 0, 10, 0)
                    linha.addStretch()
                    linha.addWidget(contagem)
                    self.contagens[nome] = contagem
                    self.navs.addButton(botao)
                    v.addWidget(botao)
            v.addStretch()
            return quadro

        def criar_grade(self):
            area = QWidget()
            v = QVBoxLayout(area)
            v.setContentsMargins(16, 14, 10, 0)
            v.setSpacing(8)
            self.busca = QLineEdit()
            self.busca.setObjectName("buscaGrande")
            self.busca.setPlaceholderText("⌕   Buscar na biblioteca")
            self.busca.textChanged.connect(lambda _: self.aplicar_filtro())
            self.busca_topo.textChanged.connect(self.busca.setText)
            v.addWidget(self.busca)
            self.resultado = rotulo("", "contagem")
            self.resultado.setAlignment(Qt.AlignRight)
            v.addWidget(self.resultado)

            self.cartoes = {nome: Cartao(nome, self.selecionar, self.favoritar)
                            for nome in Animador.PRESETS}
            for nome, cartao in self.cartoes.items():
                cartao.estrela.blockSignals(True)
                cartao.estrela.setChecked(nome in self.favoritos)
                cartao.estrela.blockSignals(False)
            self.conteudo = QWidget()
            self.grade = QGridLayout(self.conteudo)
            self.grade.setContentsMargins(0, 0, 6, 16)
            self.grade.setSpacing(14)
            self.grade.setAlignment(Qt.AlignTop)
            self.vazio_grade = rotulo("Nenhuma animação encontrada.", "dica")
            self.vazio_grade.setAlignment(Qt.AlignCenter)
            self.rolagem = QScrollArea()
            self.rolagem.setWidgetResizable(True)
            self.rolagem.setWidget(self.conteudo)
            self.conteudo.setStyleSheet("background: transparent;")
            v.addWidget(self.rolagem, 1)
            return area

        def criar_painel(self):
            painel = QFrame()
            painel.setObjectName("painel")
            painel.setFixedWidth(280)
            v = QVBoxLayout(painel)
            v.setContentsMargins(16, 16, 16, 16)
            v.setSpacing(8)

            v.addWidget(rotulo("Selecionada"))
            self.nome_selecionado = rotulo("", "titulo")
            v.addWidget(self.nome_selecionado)
            self.desc_selecionado = rotulo("", "dica")
            self.desc_selecionado.setWordWrap(True)
            v.addWidget(self.desc_selecionado)
            v.addSpacing(6)

            v.addWidget(rotulo("Duração"))
            linha = QHBoxLayout()
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(1, 240)
            self.duracao = QSpinBox()
            self.duracao.setRange(1, 1000)
            self.duracao.setSuffix(" F")
            self.duracao.setButtonSymbols(QSpinBox.NoButtons)
            self.slider.valueChanged.connect(self.duracao.setValue)
            self.duracao.valueChanged.connect(
                lambda d: self.slider.setValue(min(d, self.slider.maximum())))
            self.duracao.valueChanged.connect(self.mudar_duracao)
            linha.addWidget(self.slider, 1)
            linha.addWidget(self.duracao)
            v.addLayout(linha)
            v.addSpacing(6)

            v.addWidget(rotulo("Posição no clipe"))
            pos = QHBoxLayout()
            self.posicoes = QButtonGroup(self)
            for i, texto in enumerate(POSICOES):
                b = QPushButton(texto.replace(" do clipe", ""))
                b.setObjectName("segmento")
                b.setCheckable(True)
                b.setChecked(i == 0)
                self.posicoes.addButton(b, i)
                pos.addWidget(b)
            v.addLayout(pos)
            v.addSpacing(10)
            v.addWidget(linha_divisoria())
            v.addSpacing(6)

            cab = QHBoxLayout()
            cab.addWidget(rotulo("Clipes da timeline"))
            cab.addStretch()
            self.qtd_clipes = rotulo("", "contagem")
            cab.addWidget(self.qtd_clipes)
            v.addLayout(cab)
            self.lista = QListWidget()
            self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.lista.itemSelectionChanged.connect(self.atualizar_botao)
            v.addWidget(self.lista, 1)
            self.vazio = rotulo("Abra uma timeline no DaVinci\ne clique em Conectar.", "dica")
            self.vazio.setAlignment(Qt.AlignCenter)
            v.addWidget(self.vazio, 1)

            self.aplicar_btn = QPushButton()
            self.aplicar_btn.setObjectName("aplicar")
            self.aplicar_btn.setCursor(Qt.PointingHandCursor)
            self.aplicar_btn.clicked.connect(self.aplicar)
            v.addWidget(self.aplicar_btn)
            self.status = rotulo("", "dica")
            self.status.setWordWrap(True)
            v.addWidget(self.status)
            return painel

        def criar_rodape(self):
            rodape = QFrame()
            rodape.setObjectName("rodape")
            rodape.setFixedHeight(34)
            h = QHBoxLayout(rodape)
            h.setContentsMargins(16, 0, 16, 0)
            self.conexao = rotulo("", "mono")
            self.conexao.setTextFormat(Qt.RichText)
            h.addWidget(self.conexao)
            h.addStretch()
            h.addWidget(rotulo("Animador %s  ·  DaVinci Resolve" % VERSAO, "mono"))
            return rodape

        # -- comportamento ----------------------------------------------------

        def paintEvent(self, evento):
            # Fundo escuro com um brilho laranja suave no canto, como um holofote.
            p = QPainter(self)
            p.fillRect(self.rect(), QColor("#0c0c0e"))
            brilho = QRadialGradient(QPointF(self.width() * 0.25, 0), self.width() * 0.55)
            brilho.setColorAt(0, QColor(255, 106, 26, 70))
            brilho.setColorAt(1, QColor(255, 106, 26, 0))
            p.fillRect(self.rect(), brilho)

        def animar(self):
            self.global_frame += 1
            for cartao in self.cartoes.values():
                if cartao.isVisible():
                    cartao.previa.tick(self.global_frame)

        def colunas(self):
            largura = self.rolagem.viewport().width()
            return max(1, (largura + 14) // 184)

        def aplicar_filtro(self):
            nomes = filtrar_presets(self.filtro, self.busca.text(), self.favoritos)
            for i in reversed(range(self.grade.count())):
                self.grade.itemAt(i).widget().setParent(None)
            for cartao in self.cartoes.values():
                cartao.hide()
            cols = self.colunas()
            for i, nome in enumerate(nomes):
                cartao = self.cartoes[nome]
                self.grade.addWidget(cartao, i // cols, i % cols)
                cartao.show()
            if not nomes:
                self.grade.addWidget(self.vazio_grade, 0, 0)
                self.vazio_grade.show()
            for c in range(cols):
                self.grade.setColumnStretch(c, 1)
            self.resultado.setText("%d DE %d ANIMAÇÕES" % (len(nomes), len(Animador.PRESETS)))
            for _, itens in NAVEGACAO:
                for _, nome in itens:
                    self.contagens[nome].setText(
                        str(len(filtrar_presets(nome, "", self.favoritos))))

        def resizeEvent(self, evento):
            super().resizeEvent(evento)
            QTimer.singleShot(0, self.aplicar_filtro)

        def mudar_filtro(self, nome):
            self.filtro = nome
            self.aplicar_filtro()

        def favoritar(self, nome, marcado):
            (self.favoritos.add if marcado else self.favoritos.discard)(nome)
            self.config.setValue("favoritos", sorted(self.favoritos))
            self.aplicar_filtro()

        def selecionar(self, nome):
            self.selecionado = nome
            for n, cartao in self.cartoes.items():
                cartao.selecionar(n == nome)
            categoria, descricao = info_preset(nome)
            self.nome_selecionado.setText(nome)
            self.desc_selecionado.setText("%s  ·  %s" % (categoria, descricao))
            self.atualizar_botao()

        def mudar_duracao(self, duracao):
            for cartao in self.cartoes.values():
                cartao.previa.definir(cartao.nome, duracao)
                cartao.definir_duracao(duracao)

        def mostrar(self, texto, tipo="info"):
            self.status.setStyleSheet("color: %s;" % CORES_STATUS[tipo])
            self.status.setText(texto)

        def definir_conexao(self, nome):
            if nome:
                texto = '<span style="color:#4ade80">●</span>&nbsp; CONECTADO  ·  %s' % (
                    nome.upper())
            else:
                texto = ('<span style="color:#ff6a1a">●</span>&nbsp; DESCONECTADO  ·  '
                         'CLIQUE EM CONECTAR')
            self.conexao.setText(texto)

        def mostrar_lista(self, tem_clipes):
            self.lista.setVisible(tem_clipes)
            self.vazio.setVisible(not tem_clipes)

        def atualizar_botao(self):
            n = len(self.lista.selectedItems())
            self.aplicar_btn.setEnabled(n > 0 and self.selecionado is not None)
            self.aplicar_btn.setText("Aplicar em %d clipe(s)" % n if n
                                     else "Selecione clipes para aplicar")

        def mostrar_clipes(self, clipes, nome=None):
            self.lista.clear()
            for trilha, item in clipes:
                linha = QListWidgetItem("V%d   %s\n       %d frames" % (
                    trilha, item.GetName(), int(item.GetDuration())))
                linha.setData(Qt.UserRole, item)
                self.lista.addItem(linha)
            self.mostrar_lista(bool(clipes))
            self.qtd_clipes.setText(str(len(clipes)))
            if nome:
                self.definir_conexao(nome)
            self.mostrar("%d clipe(s) encontrados." % len(clipes), "ok" if clipes else "info")

        def atualizar(self):
            try:
                if self.resolve is None:
                    self.resolve = conectar_resolve()
                timeline = timeline_atual(self.resolve)
                clipes = listar_clipes(timeline)
            except Exception as erro:  # mostra qualquer falha da API na janela
                self.resolve = None
                self.definir_conexao(None)
                self.mostrar("Erro: %s" % erro, "erro")
                return
            self.mostrar_clipes(clipes, timeline.GetName())

        def aplicar(self):
            preset = self.selecionado
            posicao = POSICOES[self.posicoes.checkedId()]
            selecionados = self.lista.selectedItems()
            erros = []
            for linha in selecionados:
                item = linha.data(Qt.UserRole)
                try:
                    aplicar_em_clipe(item, preset, self.duracao.value(), posicao)
                except Exception as erro:
                    erros.append("%s: %s" % (item.GetName(), erro))
            ok = len(selecionados) - len(erros)
            if erros:
                self.mostrar("'%s' aplicado em %d clipe(s). Falhas: %s"
                             % (preset, ok, "; ".join(erros)), "erro")
            else:
                self.mostrar("✓  '%s' aplicado em %d clipe(s)." % (preset, ok), "ok")

    janela = JanelaAnimador()
    janela.duracao.setValue(24)
    return janela


def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 não está instalado. Rode: pip install -r requirements.txt")
        sys.exit(1)
    app = QApplication(sys.argv)
    janela = criar_janela()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
