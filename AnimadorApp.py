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

# Ícone, nome curto (para o cartão) e descrição de cada preset.
INFO_PRESETS = {
    "Fade In": ("◐", "Fade In", "Aparece suavemente"),
    "Fade Out": ("◑", "Fade Out", "Some suavemente"),
    "Deslizar da esquerda": ("→", "Esquerda", "Entra deslizando pela esquerda"),
    "Deslizar da direita": ("←", "Direita", "Entra deslizando pela direita"),
    "Deslizar de baixo": ("↑", "De baixo", "Sobe deslizando de baixo"),
    "Zoom Pop": ("✦", "Zoom Pop", "Cresce do zero com um estouro"),
    "Quicar (cair do topo)": ("⬇", "Quicar", "Cai do topo e quica até parar"),
    "Girar e aparecer": ("↻", "Girar", "Gira enquanto cresce"),
    "Pulsar": ("♥", "Pulsar", "Aumenta um pouco e volta"),
    "Ken Burns": ("▣", "Ken Burns", "Zoom lento com movimento, para fotos"),
}


def info_preset(nome):
    return INFO_PRESETS.get(nome, ("•", nome, ""))

LARANJA = "#ff6a3d"

ESTILO = """
* { font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; }
QWidget#raiz { background: #141418; }
QLabel { color: #e8e8ee; background: transparent; }
QLabel#titulo { font-size: 22px; font-weight: 700; }
QLabel#subtitulo, QLabel#dica { color: #8a8a96; }
QLabel#secao { color: #8a8a96; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#pilula { border-radius: 11px; padding: 3px 12px; font-size: 12px; font-weight: 600; }
QFrame#painel { background: #1c1c22; border: 1px solid #2a2a33; border-radius: 12px; }
QListWidget {
    background: transparent; border: none; color: #e8e8ee; outline: none;
}
QListWidget::item {
    background: #23232b; border: 1px solid #2c2c36; border-radius: 8px;
    padding: 9px 10px; margin: 3px 0;
}
QListWidget::item:hover { border-color: #444452; }
QListWidget::item:selected { background: #3a2219; border-color: #ff6a3d; color: #ffffff; }
QPushButton {
    background: #26262e; color: #e8e8ee; border: 1px solid #33333d;
    border-radius: 8px; padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: #2f2f39; border-color: #45454f; }
QToolButton#cartao {
    background: #23232b; color: #e8e8ee; border: 1px solid #2c2c36;
    border-radius: 10px; padding: 8px 4px; font-size: 12px; font-weight: 600;
}
QToolButton#cartao:hover { border-color: #55555f; }
QToolButton#cartao:checked { background: #3a2219; border: 2px solid #ff6a3d; }
QPushButton#segmento { border-radius: 8px; padding: 7px; }
QPushButton#segmento:checked { background: #ff6a3d; border-color: #ff6a3d; color: white; }
QPushButton#aplicar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6a3d, stop:1 #ff9a3d);
    color: white; border: none; border-radius: 10px; padding: 13px; font-size: 14px;
}
QPushButton#aplicar:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7a50, stop:1 #ffaa55);
}
QPushButton#aplicar:disabled { background: #2a2a33; color: #6a6a76; }
QSpinBox {
    background: #23232b; color: #e8e8ee; border: 1px solid #2c2c36;
    border-radius: 8px; padding: 6px 10px; min-width: 90px;
}
QSlider::groove:horizontal { height: 6px; background: #2c2c36; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #ff6a3d; border-radius: 3px; }
QSlider::handle:horizontal {
    background: white; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px;
}
QLabel#status { border-radius: 8px; padding: 9px 12px; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #33333d; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""

CORES_STATUS = {
    "info": ("#23232b", "#a0a0ac"),
    "ok": ("#16301f", "#5ee08a"),
    "erro": ("#3a1a1a", "#ff7b7b"),
}


def criar_janela():
    from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
    from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
    from PySide6.QtWidgets import (
        QAbstractItemView, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
        QLabel, QListWidget, QListWidgetItem, QPushButton, QSizePolicy, QSlider,
        QSpinBox, QToolButton, QVBoxLayout, QWidget,
    )

    class Previa(QWidget):
        """Desenha uma 'foto' de exemplo animada com os keyframes do preset."""

        PAUSA = 18  # frames parados no fim antes de repetir

        def __init__(self):
            super().__init__()
            self.setMinimumHeight(200)
            self.frame = 0
            self.definir("Fade In", 24)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.avancar)
            self.timer.start(1000 // 30)

        def definir(self, preset, duracao):
            self.legenda = "%s  ·  %s" % (preset, info_preset(preset)[2])
            self.keys = Animador.gerar_keyframes(preset, 0, duracao)
            self.duracao = duracao
            self.frame = 0
            self.update()

        def avancar(self):
            self.frame = (self.frame + 1) % (self.duracao + 1 + self.PAUSA)
            self.update()

        def valor(self, nome, padrao):
            if nome not in self.keys:
                return padrao
            return self.keys[nome][min(self.frame, self.duracao)][1]

        def paintEvent(self, evento):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            area = QRectF(self.rect()).adjusted(1, 1, -1, -1)
            fundo = QPainterPath()
            fundo.addRoundedRect(area, 10, 10)
            p.fillPath(fundo, QColor("#0d0d10"))
            p.setClipPath(fundo)

            # "Quadro" 16:9 centralizado (acima da legenda), com a imagem de exemplo.
            util = area.adjusted(12, 12, -12, -30)
            larg = min(util.width(), util.height() * 16 / 9)
            alt = larg * 9 / 16
            quadro = QRectF(0, 0, larg, alt)
            quadro.moveCenter(util.center())
            p.setPen(QColor("#2c2c36"))
            p.drawRect(quadro)
            p.setPen(QColor("#6a6a76"))
            p.drawText(area.adjusted(0, 0, 0, -6), Qt.AlignHCenter | Qt.AlignBottom,
                       self.legenda)

            cx, cy = self.valor("Center", (0.5, 0.5))
            tamanho = self.valor("Size", 1.0)
            angulo = self.valor("Angle", 0.0)
            opacidade = max(0.0, min(1.0, self.valor("Gain", 1.0)))

            p.setClipRect(quadro)
            p.translate(quadro.left() + cx * larg, quadro.top() + (1 - cy) * alt)
            p.rotate(-angulo)
            p.scale(tamanho, tamanho)
            p.setOpacity(opacidade)

            foto = QRectF(-larg * 0.3, -alt * 0.3, larg * 0.6, alt * 0.6)
            ceu = QLinearGradient(foto.topLeft(), foto.bottomLeft())
            ceu.setColorAt(0, QColor("#ff9a3d"))
            ceu.setColorAt(1, QColor("#ff4f6d"))
            moldura = QPainterPath()
            moldura.addRoundedRect(foto, 6, 6)
            p.fillPath(moldura, ceu)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 240, 200))
            p.drawEllipse(QPointF(foto.right() - foto.width() * 0.25,
                                  foto.top() + foto.height() * 0.3), foto.height() * 0.12,
                          foto.height() * 0.12)
            montanha = QPainterPath()
            montanha.moveTo(foto.left(), foto.bottom())
            montanha.lineTo(foto.left() + foto.width() * 0.35, foto.top() + foto.height() * 0.45)
            montanha.lineTo(foto.left() + foto.width() * 0.6, foto.top() + foto.height() * 0.75)
            montanha.lineTo(foto.left() + foto.width() * 0.75, foto.top() + foto.height() * 0.6)
            montanha.lineTo(foto.right(), foto.bottom())
            montanha.closeSubpath()
            p.setClipPath(moldura, Qt.IntersectClip)
            p.fillPath(montanha, QColor(60, 20, 50, 200))

    def painel():
        quadro = QFrame()
        quadro.setObjectName("painel")
        layout = QVBoxLayout(quadro)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        return quadro, layout

    def secao(texto):
        rotulo = QLabel(texto.upper())
        rotulo.setObjectName("secao")
        return rotulo

    class JanelaAnimador(QWidget):
        def __init__(self):
            super().__init__()
            self.resolve = None
            self.setObjectName("raiz")
            self.setWindowTitle("Animador para DaVinci Resolve")
            self.resize(1000, 720)
            self.setMinimumSize(860, 640)
            self.setStyleSheet(ESTILO)

            raiz = QVBoxLayout(self)
            raiz.setContentsMargins(20, 18, 20, 18)
            raiz.setSpacing(14)

            # Cabeçalho
            cabecalho = QHBoxLayout()
            textos = QVBoxLayout()
            textos.setSpacing(0)
            titulo = QLabel("Animador")
            titulo.setObjectName("titulo")
            subtitulo = QLabel("Animações prontas para suas imagens no DaVinci Resolve")
            subtitulo.setObjectName("subtitulo")
            textos.addWidget(titulo)
            textos.addWidget(subtitulo)
            cabecalho.addLayout(textos)
            cabecalho.addStretch()
            self.pilula = QLabel()
            self.pilula.setObjectName("pilula")
            cabecalho.addWidget(self.pilula, 0, Qt.AlignVCenter)
            conectar = QPushButton("⟳  Conectar")
            conectar.clicked.connect(self.atualizar)
            cabecalho.addWidget(conectar, 0, Qt.AlignVCenter)
            raiz.addLayout(cabecalho)

            colunas = QHBoxLayout()
            colunas.setSpacing(14)
            raiz.addLayout(colunas, 1)

            # Coluna esquerda: clipes
            esquerda, layout_esq = painel()
            linha = QHBoxLayout()
            linha.addWidget(secao("Clipes da timeline"))
            linha.addStretch()
            todos = QPushButton("Selecionar todos")
            todos.clicked.connect(lambda: self.lista.selectAll())
            linha.addWidget(todos)
            layout_esq.addLayout(linha)
            self.lista = QListWidget()
            self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.lista.itemSelectionChanged.connect(self.atualizar_botao)
            layout_esq.addWidget(self.lista, 1)
            self.vazio = QLabel("Abra o DaVinci Resolve Studio com uma timeline\n"
                                "e clique em Conectar.")
            self.vazio.setObjectName("dica")
            self.vazio.setAlignment(Qt.AlignCenter)
            layout_esq.addWidget(self.vazio, 1)
            dica = QLabel("Dica: Ctrl ou Shift para escolher vários clipes.")
            dica.setObjectName("dica")
            layout_esq.addWidget(dica)
            colunas.addWidget(esquerda, 5)

            # Coluna direita: animação
            direita, layout_dir = painel()
            layout_dir.addWidget(secao("Animação"))
            grade = QGridLayout()
            grade.setSpacing(8)
            self.cartoes = QButtonGroup(self)
            self.cartoes.setExclusive(True)
            for i, nome in enumerate(Animador.PRESETS):
                icone, curto, descricao = info_preset(nome)
                cartao = QToolButton()
                cartao.setObjectName("cartao")
                cartao.setText("%s\n%s" % (icone, curto))
                cartao.setToolTip("%s: %s" % (nome, descricao))
                cartao.setCheckable(True)
                cartao.setMinimumSize(96, 62)
                cartao.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                cartao.setProperty("preset", nome)
                self.cartoes.addButton(cartao, i)
                grade.addWidget(cartao, i // 5, i % 5)
            self.cartoes.button(0).setChecked(True)
            self.cartoes.idClicked.connect(lambda _: self.atualizar_previa())
            layout_dir.addLayout(grade)

            self.previa = Previa()
            layout_dir.addWidget(self.previa, 1)

            layout_dir.addWidget(secao("Duração"))
            linha_dur = QHBoxLayout()
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(1, 240)
            self.duracao = QSpinBox()
            self.duracao.setRange(1, 1000)
            self.duracao.setSuffix(" frames")
            self.duracao.setButtonSymbols(QSpinBox.NoButtons)
            self.slider.valueChanged.connect(self.duracao.setValue)
            self.duracao.valueChanged.connect(
                lambda v: self.slider.setValue(min(v, self.slider.maximum())))
            self.duracao.valueChanged.connect(lambda _: self.atualizar_previa())
            self.duracao.setValue(24)
            linha_dur.addWidget(self.slider, 1)
            linha_dur.addWidget(self.duracao)
            layout_dir.addLayout(linha_dur)

            layout_dir.addWidget(secao("Posição no clipe"))
            linha_pos = QHBoxLayout()
            linha_pos.setSpacing(8)
            self.posicoes = QButtonGroup(self)
            for i, texto in enumerate(POSICOES):
                botao = QPushButton(texto)
                botao.setObjectName("segmento")
                botao.setCheckable(True)
                botao.setChecked(i == 0)
                self.posicoes.addButton(botao, i)
                linha_pos.addWidget(botao)
            layout_dir.addLayout(linha_pos)
            colunas.addWidget(direita, 6)

            # Rodapé
            self.aplicar_btn = QPushButton()
            self.aplicar_btn.setObjectName("aplicar")
            self.aplicar_btn.setCursor(Qt.PointingHandCursor)
            self.aplicar_btn.clicked.connect(self.aplicar)
            raiz.addWidget(self.aplicar_btn)
            self.status = QLabel()
            self.status.setObjectName("status")
            self.status.setWordWrap(True)
            raiz.addWidget(self.status)

            self.definir_conexao(None)
            self.mostrar_lista(False)
            self.atualizar_previa()
            self.atualizar_botao()
            self.mostrar("Pronto. Conecte ao DaVinci para listar os clipes.")

        # -- helpers de estado ------------------------------------------------

        def preset_atual(self):
            return self.cartoes.checkedButton().property("preset")

        def mostrar(self, texto, tipo="info"):
            fundo, cor = CORES_STATUS[tipo]
            self.status.setStyleSheet("background: %s; color: %s; border-radius: 8px;"
                                      " padding: 9px 12px;" % (fundo, cor))
            self.status.setText(texto)

        def definir_conexao(self, nome):
            if nome:
                texto, fundo, cor = "●  " + nome, "#16301f", "#5ee08a"
            else:
                texto, fundo, cor = "●  Desconectado", "#2a2a33", "#8a8a96"
            self.pilula.setText(texto)
            self.pilula.setStyleSheet("background: %s; color: %s; border-radius: 11px;"
                                      " padding: 4px 12px;" % (fundo, cor))

        def mostrar_lista(self, tem_clipes):
            self.lista.setVisible(tem_clipes)
            self.vazio.setVisible(not tem_clipes)

        def atualizar_previa(self):
            self.previa.definir(self.preset_atual(), self.duracao.value())

        def atualizar_botao(self):
            n = len(self.lista.selectedItems())
            self.aplicar_btn.setEnabled(n > 0)
            self.aplicar_btn.setText("✦  Aplicar em %d clipe(s)" % n if n
                                     else "Selecione clipes para aplicar")

        # -- ações ------------------------------------------------------------

        def mostrar_clipes(self, clipes, nome=None):
            self.lista.clear()
            for trilha, item in clipes:
                segundos = int(item.GetDuration()) / 24.0
                linha = QListWidgetItem("V%d    %s\n        %d frames  ·  ~%.1fs" % (
                    trilha, item.GetName(), int(item.GetDuration()), segundos))
                linha.setData(Qt.UserRole, item)
                self.lista.addItem(linha)
            self.mostrar_lista(bool(clipes))
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
            preset = self.preset_atual()
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

    return JanelaAnimador()


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
