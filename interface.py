"""
Interface do Animador App (PySide6 / Qt).

Separada do AnimadorApp.py, que cuida da conexão com o DaVinci. A janela recebe
esse módulo como `backend` para conectar, listar e aplicar nos clipes.
"""

import json
import os
import threading
from string import Template

from PySide6.QtCore import QMimeData, QObject, QPointF, QRectF, QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor, QDesktopServices, QDrag, QIcon, QKeySequence, QLinearGradient, QPainter,
    QPainterPath, QPen, QRadialGradient, QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QComboBox, QDialog, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QToolButton,
    QVBoxLayout, QWidget,
)

import Animador

MIME_PRESET = "application/x-animador-preset"

# ---------------------------------------------------------------------------
# Temas
# ---------------------------------------------------------------------------

TEMAS = {
    "Escuro": {
        "fundo": "#0c0c0e", "lateral": "#121214", "coluna": "#161619", "painel": "#141417",
        "cartao": "#1a1a1d", "previa": "#000000", "campo": "#161619", "hover": "#202024",
        "borda": "#232327", "borda2": "#3a3a40", "texto": "#e9e9ec", "texto2": "#b8b8be",
        "texto3": "#77777f", "brilho": 70,
    },
    "Claro": {
        "fundo": "#f4f4f6", "lateral": "#ffffff", "coluna": "#fafafb", "painel": "#ffffff",
        "cartao": "#ffffff", "previa": "#1b1b1f", "campo": "#f1f1f4", "hover": "#ececf0",
        "borda": "#e2e2e7", "borda2": "#c8c8d0", "texto": "#18181b", "texto2": "#3f3f46",
        "texto3": "#71717a", "brilho": 45,
    },
}

CORES = {
    "Laranja": "#ff6a1a",
    "Azul": "#3d8bff",
    "Verde": "#22c55e",
    "Roxo": "#a855f7",
    "Rosa": "#ec4899",
}


def misturar(cor1, cor2, t):
    a, b = QColor(cor1), QColor(cor2)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    ).name()


ESTILO = Template("""
* { font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; color: $texto; }
QLabel { background: transparent; }
QFrame#lateral { background: $lateral; border-right: 1px solid $borda; }
QFrame#coluna { background: $coluna; border-right: 1px solid $borda; }
QFrame#topo { border-bottom: 1px solid $borda; }
QFrame#rodape { border-top: 1px solid $borda; }
QFrame#painel { background: $painel; border-left: 1px solid $borda; }
QFrame#divisoria { background: $borda; }
QLabel#logo { font-size: 16px; font-weight: 700; }
QLabel#titulo { font-size: 15px; font-weight: 700; }
QLabel#subtitulo, QLabel#dica { color: $texto3; }
QLabel#secao { color: $texto3; font-size: 10px; font-weight: 600; letter-spacing: 1.5px; }
QLabel#mono, QLabel#contagem {
    color: $texto3; font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 10px; letter-spacing: 1px;
}
QPushButton#nav {
    background: transparent; border: 1px solid transparent; border-radius: 8px;
    padding: 7px 10px; text-align: left; color: $texto2;
}
QPushButton#nav:hover { background: $hover; color: $texto; }
QPushButton#nav:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $sel, stop:1 $sel2);
    border: 1px solid $selborda; color: $texto; font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox {
    background: $campo; border: 1px solid $borda; border-radius: 9px;
    padding: 7px 12px; selection-background-color: $acento;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: $acento; }
QLineEdit#buscaGrande { background: $sel2; border: 1px solid $selborda; padding: 11px 14px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: $painel; border: 1px solid $borda2; selection-background-color: $sel;
    selection-color: $texto; outline: none;
}
QPushButton {
    background: $campo; border: 1px solid $borda; border-radius: 9px;
    padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: $hover; border-color: $borda2; }
QPushButton#atualizacao { background: $sel; border-color: $acento; color: $texto; }
QFrame#cartao { background: $cartao; border: 1px solid $borda; border-radius: 12px; }
QFrame#cartao:hover { border-color: $borda2; }
QFrame#cartao[selecionado="true"] { border: 1px solid $acento; }
QLabel#nomeCartao { font-size: 13px; font-weight: 700; }
QToolButton#estrela {
    background: rgba(0, 0, 0, 120); border: none; border-radius: 13px;
    color: #9a9aa2; font-size: 14px;
}
QToolButton#estrela:checked { color: #ffb020; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item {
    background: $campo; border: 1px solid $borda; border-radius: 8px;
    padding: 8px 10px; margin: 2px 0; color: $texto;
}
QListWidget::item:hover { border-color: $borda2; }
QListWidget::item:selected { background: $sel; border-color: $acento; color: $texto; }
QListWidget[arrastando="true"] { border: 1px dashed $acento; border-radius: 8px; }
QPushButton#segmento { padding: 7px; }
QPushButton#segmento:checked { background: $sel; border-color: $acento; }
QPushButton#aplicar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $acento, stop:1 $acento2);
    color: white; border: none; border-radius: 10px; padding: 12px; font-size: 14px;
}
QPushButton#aplicar:disabled { background: $hover; color: $texto3; }
QPushButton#secundario { padding: 6px 10px; font-weight: 500; color: $texto2; }
QSlider::groove:horizontal { height: 4px; background: $borda; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $acento; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #ffffff; border: 1px solid $borda2; width: 14px; height: 14px;
    margin: -6px 0; border-radius: 8px;
}
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: $borda2; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { background: $painel; color: $texto; border: 1px solid $borda2; padding: 4px; }
QMenu { background: $painel; border: 1px solid $borda2; padding: 4px; }
QMenu::item { padding: 6px 18px; border-radius: 6px; }
QMenu::item:selected { background: $sel; }
QDialog { background: $painel; }
""")


def montar_estilo(tema, cor):
    t = dict(TEMAS[tema])
    acento = CORES[cor]
    t.update(
        acento=acento,
        acento2=misturar(acento, "#ffffff", 0.25),
        sel=misturar(t["cartao"], acento, 0.22),
        sel2=misturar(t["cartao"], acento, 0.08),
        selborda=misturar(t["cartao"], acento, 0.45),
    )
    return ESTILO.substitute(t)


# ---------------------------------------------------------------------------
# Biblioteca: filtros e presets do usuário
# ---------------------------------------------------------------------------

# (seção, [(ícone, nome do filtro)])
NAVEGACAO = [
    ("Biblioteca", [("▦", "Todos"), ("☆", "Favoritos"), ("◷", "Recentes"),
                    ("✎", "Meus presets")]),
    ("Categorias", [("↗", Animador.ENTRADA), ("↘", Animador.SAIDA),
                    ("✦", Animador.DESTAQUE), ("▣", Animador.FOTOS)]),
]
PADRAO_CURVA = "Padrão do preset"
MAX_RECENTES = 8


class Biblioteca:
    """Presets do motor + presets salvos pelo usuário, com favoritos e recentes."""

    def __init__(self, meus=None, favoritos=(), recentes=()):
        # meus: {nome: {"base", "curva", "intensidade", "duracao"}}
        self.meus = dict(meus or {})
        self.favoritos = set(favoritos)
        self.recentes = list(recentes)

    def nomes(self):
        return list(Animador.PRESETS) + list(self.meus)

    def info(self, nome):
        """(categoria, descrição, preset base)"""
        if nome in self.meus:
            base = self.meus[nome]["base"]
            return "Meus presets", "Baseado em %s" % base, base
        categoria, descricao = Animador.CATEGORIAS.get(nome, ("Outros", ""))
        return categoria, descricao, nome

    def filtrar(self, filtro, busca=""):
        busca = busca.strip().lower()
        if filtro == "Recentes":
            candidatos = [n for n in self.recentes if n in self.nomes()]
        else:
            candidatos = self.nomes()
        nomes = []
        for nome in candidatos:
            categoria, descricao, base = self.info(nome)
            if filtro == "Favoritos" and nome not in self.favoritos:
                continue
            if filtro not in ("Todos", "Favoritos", "Recentes") and categoria != filtro:
                continue
            texto = " ".join((nome, descricao, categoria, base)).lower()
            if busca and busca not in texto:
                continue
            nomes.append(nome)
        return nomes

    def usar(self, nome):
        if nome in self.recentes:
            self.recentes.remove(nome)
        self.recentes.insert(0, nome)
        del self.recentes[MAX_RECENTES:]

    def salvar_meu(self, nome, base, curva, intensidade, duracao):
        if not nome.strip():
            raise ValueError("Dê um nome para o preset.")
        if nome in Animador.PRESETS:
            raise ValueError("Já existe uma animação com esse nome.")
        self.meus[nome] = {"base": base, "curva": curva, "intensidade": intensidade,
                           "duracao": duracao}

    def excluir_meu(self, nome):
        self.meus.pop(nome, None)
        self.favoritos.discard(nome)
        if nome in self.recentes:
            self.recentes.remove(nome)


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------


class Previa(QWidget):
    """Desenha uma 'foto' de exemplo animada com os keyframes do preset."""

    PAUSA = 18  # frames parados no fim antes de repetir

    def __init__(self, preset, altura=128):
        super().__init__()
        self.setMinimumHeight(altura)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.frame = 0
        self.cor_fundo = QColor("#000000")
        self.definir(preset, 24)

    def definir(self, preset, duracao, curva=None, intensidade=1.0):
        self.keys = Animador.gerar_keyframes(preset, 0, duracao, curva, intensidade)
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
        p.fillPath(fundo, self.cor_fundo)
        p.setClipPath(fundo)

        larg, alt = area.width(), area.height()
        cx, cy = self.valor("Center", (0.5, 0.5))
        tamanho = self.valor("Size", 1.0)
        angulo = self.valor("Angle", 0.0)
        opacidade = self.valor("Gain", 1.0)
        desfoque = self.valor("XBlurSize", 0.0)

        p.translate(cx * larg, (1 - cy) * alt)
        p.rotate(-angulo)
        p.scale(tamanho, tamanho)

        h = alt * 0.52
        foto = QRectF(-h * 0.8, -h / 2, h * 1.6, h)
        # Desfoque simulado: cópias deslocadas e translúcidas da foto.
        passos = [(0, 0)]
        if desfoque > 0.5:
            d = desfoque * 0.25
            passos = [(dx * d, dy * d) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        for dx, dy in passos:
            p.save()
            p.translate(dx, dy)
            p.setOpacity(opacidade / len(passos) * (2 if len(passos) > 1 else 1))
            self._foto(p, foto)
            p.restore()

    @staticmethod
    def _foto(p, foto):
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
        p.save()
        p.setClipPath(moldura, Qt.IntersectClip)
        p.fillPath(montanha, QColor(60, 20, 50, 200))
        p.restore()


class GraficoCurva(QWidget):
    """Mostra o formato da curva (easing) escolhida."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.funcao = Animador.linear
        self.cor = QColor("#ff6a1a")
        self.cor_grade = QColor("#2a2a2f")

    def definir(self, funcao):
        self.funcao = funcao
        self.update()

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area = QRectF(self.rect()).adjusted(8, 10, -8, -10)
        p.setPen(QPen(self.cor_grade, 1, Qt.DashLine))
        p.drawLine(area.bottomLeft(), area.bottomRight())
        p.drawLine(area.topLeft(), area.topRight())
        caminho = QPainterPath()
        for i in range(61):
            t = i / 60
            ponto = QPointF(area.left() + t * area.width(),
                            area.bottom() - self.funcao(t) * area.height())
            caminho.lineTo(ponto) if i else caminho.moveTo(ponto)
        p.setPen(QPen(self.cor, 2.2))
        p.drawPath(caminho)


class Cartao(QFrame):
    def __init__(self, nome, janela):
        super().__init__()
        self.nome = nome
        self.janela = janela
        self.inicio_arraste = None
        self.setObjectName("cartao")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        _, descricao, base = janela.biblioteca.info(nome)
        self.base = base
        self.previa = Previa(base)
        self.setToolTip("%s\n%s\nArraste até um clipe para aplicar direto."
                        % (nome, descricao))
        self.titulo = QLabel(nome)
        self.titulo.setObjectName("nomeCartao")
        self.tags = QLabel()
        self.tags.setObjectName("mono")

        texto = QVBoxLayout()
        texto.setContentsMargins(12, 10, 12, 12)
        texto.setSpacing(4)
        texto.addWidget(self.titulo)
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
        self.estrela.setChecked(nome in janela.biblioteca.favoritos)
        self.estrela.setFixedSize(26, 26)
        self.estrela.setCursor(Qt.PointingHandCursor)
        self.estrela.setToolTip("Favoritar")
        self.estrela.toggled.connect(lambda marcado: janela.favoritar(nome, marcado))

    def atualizar(self, duracao, curva, intensidade, acento):
        meu = self.janela.biblioteca.meus.get(self.nome)
        if meu:
            duracao, curva, intensidade = meu["duracao"], meu["curva"], meu["intensidade"]
        self.previa.definir(self.base, duracao, curva, intensidade)
        categoria, _, _ = self.janela.biblioteca.info(self.nome)
        self.tags.setText('<span style="color:%s">%s</span>  ·  %dF'
                          % (acento, categoria.upper(), duracao))

    def selecionar(self, sim):
        self.setProperty("selecionado", sim)
        self.style().unpolish(self)
        self.style().polish(self)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.estrela.move(self.previa.width() - 34, 8)
        # Nomes longos terminam em "…" em vez de serem cortados.
        largura = max(40, self.width() - 26)
        self.titulo.setText(self.titulo.fontMetrics().elidedText(
            self.nome, Qt.ElideRight, largura))

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.inicio_arraste = evento.position().toPoint()
            self.janela.selecionar(self.nome)

    def mouseMoveEvent(self, evento):
        if self.inicio_arraste is None:
            return
        distancia = (evento.position().toPoint() - self.inicio_arraste).manhattanLength()
        if distancia < QApplication.startDragDistance():
            return
        self.inicio_arraste = None
        dados = QMimeData()
        dados.setData(MIME_PRESET, self.nome.encode("utf-8"))
        arraste = QDrag(self)
        arraste.setMimeData(dados)
        arraste.setPixmap(self.grab().scaledToWidth(150, Qt.SmoothTransformation))
        arraste.setHotSpot(arraste.pixmap().rect().center())
        arraste.exec(Qt.CopyAction)

    def mouseReleaseEvent(self, evento):
        self.inicio_arraste = None

    def contextMenuEvent(self, evento):
        menu = QMenu(self)
        aplicar = menu.addAction("Aplicar nos clipes selecionados")
        favorito = menu.addAction("Remover dos favoritos" if self.estrela.isChecked()
                                  else "Adicionar aos favoritos")
        excluir = None
        if self.nome in self.janela.biblioteca.meus:
            menu.addSeparator()
            excluir = menu.addAction("Excluir preset")
        escolha = menu.exec(evento.globalPos())
        if escolha is aplicar:
            self.janela.selecionar(self.nome)
            self.janela.aplicar()
        elif escolha is favorito:
            self.estrela.toggle()
        elif excluir is not None and escolha is excluir:
            self.janela.excluir_meu(self.nome)


class ListaClipes(QListWidget):
    """Lista de clipes que aceita cartões arrastados para aplicar direto."""

    def __init__(self, ao_soltar):
        super().__init__()
        self.ao_soltar = ao_soltar
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(False)

    def _marcar(self, sim):
        self.setProperty("arrastando", sim)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, evento):
        if evento.mimeData().hasFormat(MIME_PRESET):
            self._marcar(True)
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragMoveEvent(self, evento):
        if not evento.mimeData().hasFormat(MIME_PRESET):
            evento.ignore()
            return
        linha = self.itemAt(evento.position().toPoint())
        if linha is not None:
            self.setCurrentItem(linha)
        evento.acceptProposedAction()

    def dragLeaveEvent(self, evento):
        self._marcar(False)

    def dropEvent(self, evento):
        self._marcar(False)
        linha = self.itemAt(evento.position().toPoint())
        if linha is None or not evento.mimeData().hasFormat(MIME_PRESET):
            evento.ignore()
            return
        nome = bytes(evento.mimeData().data(MIME_PRESET)).decode("utf-8")
        evento.acceptProposedAction()
        self.ao_soltar(linha, nome)


class Avisador(QObject):
    """Leva o resultado da busca de atualização da thread para a interface."""

    nova_versao = Signal(str, str)


def rotulo(texto, nome="secao"):
    r = QLabel(texto.upper() if nome == "secao" else texto)
    r.setObjectName(nome)
    return r


def divisoria():
    d = QFrame()
    d.setObjectName("divisoria")
    d.setFixedHeight(1)
    return d


def botao_nav(texto, ao_clicar=None, marcavel=False):
    b = QPushButton(texto)
    b.setObjectName("nav")
    b.setCheckable(marcavel)
    if ao_clicar:
        b.clicked.connect(ao_clicar)
    return b


# ---------------------------------------------------------------------------
# Janela principal
# ---------------------------------------------------------------------------


class JanelaAnimador(QWidget):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.resolve = None
        self.selecionado = None
        self.global_frame = 0
        self.config = QSettings("Animador", "AnimadorApp")
        self.tema = self.ler("tema", "Escuro", TEMAS)
        self.cor = self.ler("cor", "Laranja", CORES)
        self.filtro = self.ler("filtro", "Todos")
        self.biblioteca = Biblioteca(self.ler_json("meus", {}), self.ler_json("favoritos", []),
                                     self.ler_json("recentes", []))

        self.setWindowTitle("Animador para DaVinci Resolve")
        icone = os.path.join(backend.pasta_recursos(), "icone.png")
        if os.path.exists(icone):
            self.setWindowIcon(QIcon(icone))
        self.resize(1460, 860)
        self.setMinimumSize(1100, 680)

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

        self.cartoes = {}
        self.recriar_cartoes()
        self.restaurar_opcoes()
        self.aplicar_tema()
        self.criar_atalhos()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animar)
        self.timer.start(1000 // 30)

        self.selecionar(self.ler("selecionado", next(iter(Animador.PRESETS))))
        self.mostrar_lista(False)
        self.atualizar_botao()
        self.definir_conexao(None)
        self.mostrar("Conecte ao DaVinci (F5) para listar os clipes.")
        self.buscar_atualizacao()

    # -- configurações salvas -------------------------------------------------

    def ler(self, chave, padrao, validos=None):
        valor = self.config.value(chave, padrao)
        if validos is not None and valor not in validos:
            return padrao
        return valor

    def ler_json(self, chave, padrao):
        valor = self.config.value(chave)
        if isinstance(valor, (list, dict)):  # formato antigo (versão 1)
            return valor
        try:
            dados = json.loads(valor) if valor else padrao
        except (TypeError, ValueError):
            return padrao
        return dados if isinstance(dados, type(padrao)) else padrao

    def salvar_biblioteca(self):
        b = self.biblioteca
        self.config.setValue("meus", json.dumps(b.meus))
        self.config.setValue("favoritos", json.dumps(sorted(b.favoritos)))
        self.config.setValue("recentes", json.dumps(b.recentes))

    def salvar_opcoes(self):
        self.config.setValue("duracao", self.duracao.value())
        self.config.setValue("curva", self.curva.currentText())
        self.config.setValue("intensidade", self.intensidade.value())
        self.config.setValue("posicao", self.posicoes.checkedId())
        self.config.setValue("saida", self.saida.currentText())
        self.config.setValue("filtro", self.filtro)
        if self.selecionado:
            self.config.setValue("selecionado", self.selecionado)

    def restaurar_opcoes(self):
        try:
            self.duracao.setValue(int(self.ler("duracao", 24)))
            self.intensidade.setValue(int(self.ler("intensidade", 100)))
            self.posicoes.button(int(self.ler("posicao", 0))).setChecked(True)
        except (TypeError, ValueError, AttributeError):
            pass
        self.curva.setCurrentText(self.ler("curva", PADRAO_CURVA))
        self.saida.setCurrentText(self.ler("saida", "Nenhuma"))
        self.atualizar_saida()
        for botao in self.navs.buttons():
            if botao.property("filtro") == self.filtro:
                botao.setChecked(True)

    def closeEvent(self, evento):
        self.salvar_opcoes()
        self.salvar_biblioteca()
        super().closeEvent(evento)

    # -- montagem da tela -----------------------------------------------------

    def criar_lateral(self):
        lateral = QFrame()
        lateral.setObjectName("lateral")
        lateral.setFixedWidth(210)
        v = QVBoxLayout(lateral)
        v.setContentsMargins(14, 16, 14, 14)
        v.setSpacing(4)
        self.logo = QLabel()
        self.logo.setObjectName("logo")
        v.addWidget(self.logo)
        v.addSpacing(18)
        principal = botao_nav("▦    Animações", marcavel=True)
        principal.setChecked(True)
        v.addWidget(principal)
        v.addSpacing(14)
        v.addWidget(rotulo("Atalhos"))
        v.addWidget(botao_nav("⟳    Conectar", self.atualizar))
        v.addWidget(botao_nav("☰    Todos os clipes", lambda: self.lista.selectAll()))
        remover = botao_nav("✕    Limpar clipes", self.remover)
        remover.setToolTip("Remove as animações do Animador dos clipes selecionados")
        v.addWidget(remover)
        v.addStretch()
        v.addWidget(divisoria())
        v.addSpacing(6)
        v.addWidget(botao_nav("⚙    Configurações", self.abrir_configuracoes))
        return lateral

    def criar_topo(self):
        topo = QFrame()
        topo.setObjectName("topo")
        topo.setFixedHeight(64)
        h = QHBoxLayout(topo)
        h.setContentsMargins(18, 0, 18, 0)
        h.addWidget(rotulo("Animações", "titulo"))
        h.addSpacing(6)
        h.addWidget(rotulo("escolha a animação, depois aplique ou arraste até o clipe",
                           "subtitulo"))
        h.addStretch()
        self.botao_atualizacao = QPushButton()
        self.botao_atualizacao.setObjectName("atualizacao")
        self.botao_atualizacao.hide()
        h.addWidget(self.botao_atualizacao)
        self.busca_topo = QLineEdit()
        self.busca_topo.setPlaceholderText("⌕  Buscar        Ctrl K")
        self.busca_topo.setFixedWidth(220)
        h.addWidget(self.busca_topo)
        conectar = QPushButton("⟳  Conectar")
        conectar.setToolTip("Conectar ao DaVinci (F5)")
        conectar.clicked.connect(self.atualizar)
        h.addWidget(conectar)
        return topo

    def criar_categorias(self):
        quadro = QFrame()
        quadro.setObjectName("coluna")
        quadro.setFixedWidth(180)
        v = QVBoxLayout(quadro)
        v.setContentsMargins(10, 14, 10, 14)
        v.setSpacing(2)
        self.navs = QButtonGroup(self)
        self.contagens = {}
        for i, (secao, itens) in enumerate(NAVEGACAO):
            if i:
                v.addSpacing(8)
                v.addWidget(divisoria())
                v.addSpacing(8)
            v.addWidget(rotulo(secao))
            v.addSpacing(4)
            for icone, nome in itens:
                botao = botao_nav("%s    %s" % (icone, nome),
                                  lambda _=False, n=nome: self.mudar_filtro(n), True)
                botao.setProperty("filtro", nome)
                botao.setChecked(nome == self.filtro)
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
        self.conteudo = QWidget()
        self.conteudo.setStyleSheet("background: transparent;")
        self.grade = QGridLayout(self.conteudo)
        self.grade.setContentsMargins(0, 0, 6, 16)
        self.grade.setSpacing(14)
        self.grade.setAlignment(Qt.AlignTop)
        self.vazio_grade = rotulo("Nenhuma animação aqui ainda.", "dica")
        self.vazio_grade.setAlignment(Qt.AlignCenter)
        self.rolagem = QScrollArea()
        self.rolagem.setWidgetResizable(True)
        self.rolagem.setWidget(self.conteudo)
        v.addWidget(self.rolagem, 1)
        return area

    def criar_painel(self):
        painel = QFrame()
        painel.setObjectName("painel")
        painel.setFixedWidth(300)
        v = QVBoxLayout(painel)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)

        v.addWidget(rotulo("Selecionada"))
        self.nome_selecionado = rotulo("", "titulo")
        v.addWidget(self.nome_selecionado)
        self.desc_selecionado = rotulo("", "dica")
        self.desc_selecionado.setWordWrap(True)
        v.addWidget(self.desc_selecionado)
        v.addSpacing(4)

        v.addWidget(rotulo("Duração"))
        linha = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 240)
        self.duracao = QSpinBox()
        self.duracao.setRange(1, 1000)
        self.duracao.setSuffix(" F")
        self.duracao.setButtonSymbols(QSpinBox.NoButtons)
        self.duracao.setFixedWidth(76)
        self.slider.valueChanged.connect(self.duracao.setValue)
        self.duracao.valueChanged.connect(
            lambda d: self.slider.setValue(min(d, self.slider.maximum())))
        self.duracao.valueChanged.connect(lambda _: self.opcoes_mudaram())
        linha.addWidget(self.slider, 1)
        linha.addWidget(self.duracao)
        v.addLayout(linha)

        v.addWidget(rotulo("Curva"))
        self.curva = QComboBox()
        self.curva.addItems([PADRAO_CURVA] + list(Animador.EASINGS))
        self.curva.currentTextChanged.connect(lambda _: self.opcoes_mudaram())
        v.addWidget(self.curva)
        self.grafico = GraficoCurva()
        v.addWidget(self.grafico)

        cab = QHBoxLayout()
        cab.addWidget(rotulo("Intensidade"))
        cab.addStretch()
        self.valor_intensidade = rotulo("", "contagem")
        cab.addWidget(self.valor_intensidade)
        v.addLayout(cab)
        self.intensidade = QSlider(Qt.Horizontal)
        self.intensidade.setRange(25, 200)
        self.intensidade.setSingleStep(5)
        self.intensidade.valueChanged.connect(lambda _: self.opcoes_mudaram())
        v.addWidget(self.intensidade)

        v.addWidget(rotulo("Posição no clipe"))
        pos = QHBoxLayout()
        self.posicoes = QButtonGroup(self)
        for i, texto in enumerate(self.backend.POSICOES):
            b = QPushButton(texto.replace(" do clipe", ""))
            b.setObjectName("segmento")
            b.setCheckable(True)
            b.setChecked(i == 0)
            self.posicoes.addButton(b, i)
            pos.addWidget(b)
        self.posicoes.idClicked.connect(lambda _: self.atualizar_saida())
        v.addLayout(pos)

        v.addSpacing(2)
        v.addWidget(rotulo("Saída no fim do clipe"))
        self.saida = QComboBox()
        self.saida.addItems(["Nenhuma"] + [n for n, (c, _) in Animador.CATEGORIAS.items()
                                           if c == Animador.SAIDA])
        self.saida.setToolTip("Aplica também uma animação de saída terminando no último "
                              "frame, para entrada + saída em um clique.")
        v.addWidget(self.saida)

        salvar = QPushButton("✎  Salvar como meu preset")
        salvar.setObjectName("secundario")
        salvar.clicked.connect(self.salvar_meu)
        v.addWidget(salvar)
        v.addSpacing(4)
        v.addWidget(divisoria())
        v.addSpacing(4)

        cab = QHBoxLayout()
        cab.addWidget(rotulo("Clipes da timeline"))
        cab.addStretch()
        self.qtd_clipes = rotulo("", "contagem")
        cab.addWidget(self.qtd_clipes)
        v.addLayout(cab)
        self.lista = ListaClipes(self.soltar_no_clipe)
        self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lista.itemSelectionChanged.connect(self.atualizar_botao)
        v.addWidget(self.lista, 1)
        self.vazio = rotulo("Abra uma timeline no DaVinci\ne clique em Conectar (F5).", "dica")
        self.vazio.setAlignment(Qt.AlignCenter)
        v.addWidget(self.vazio, 1)

        self.aplicar_btn = QPushButton()
        self.aplicar_btn.setObjectName("aplicar")
        self.aplicar_btn.setCursor(Qt.PointingHandCursor)
        self.aplicar_btn.setToolTip("Ctrl+Enter")
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
        h.addWidget(rotulo("Animador %s  ·  DaVinci Resolve" % self.backend.VERSAO, "mono"))
        return rodape

    def criar_atalhos(self):
        atalhos = [
            ("Ctrl+K", self.focar_busca),
            ("Ctrl+F", self.focar_busca),
            ("Ctrl+Return", self.aplicar),
            ("Ctrl+Enter", self.aplicar),
            ("F5", self.atualizar),
            ("Ctrl+S", self.salvar_meu),
            ("Esc", lambda: self.busca.clear()),
        ]
        for tecla, acao in atalhos:
            QShortcut(QKeySequence(tecla), self).activated.connect(acao)

    # -- aparência -------------------------------------------------------------

    def acento(self):
        return CORES[self.cor]

    def aplicar_tema(self):
        self.setStyleSheet(montar_estilo(self.tema, self.cor))
        t = TEMAS[self.tema]
        self.logo.setText('<span style="color:%s">●</span>&nbsp; Animador' % self.acento())
        self.grafico.cor = QColor(self.acento())
        self.grafico.cor_grade = QColor(t["borda2"])
        for cartao in self.cartoes.values():
            cartao.previa.cor_fundo = QColor(t["previa"])
        self.opcoes_mudaram()
        self.definir_conexao(self.resolve and self.nome_timeline)
        self.update()

    def paintEvent(self, evento):
        # Fundo com um brilho suave da cor de destaque no canto, como um holofote.
        p = QPainter(self)
        t = TEMAS[self.tema]
        p.fillRect(self.rect(), QColor(t["fundo"]))
        brilho = QRadialGradient(QPointF(self.width() * 0.25, 0), self.width() * 0.55)
        cor = QColor(self.acento())
        cor.setAlpha(t["brilho"])
        brilho.setColorAt(0, cor)
        cor.setAlpha(0)
        brilho.setColorAt(1, cor)
        p.fillRect(self.rect(), brilho)

    def abrir_configuracoes(self):
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Configurações")
        dialogo.setMinimumWidth(360)
        form = QFormLayout(dialogo)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)
        tema = QComboBox()
        tema.addItems(list(TEMAS))
        tema.setCurrentText(self.tema)
        cor = QComboBox()
        cor.addItems(list(CORES))
        cor.setCurrentText(self.cor)

        def mudar():
            self.tema, self.cor = tema.currentText(), cor.currentText()
            self.config.setValue("tema", self.tema)
            self.config.setValue("cor", self.cor)
            self.aplicar_tema()

        tema.currentTextChanged.connect(lambda _: mudar())
        cor.currentTextChanged.connect(lambda _: mudar())
        form.addRow("Tema:", tema)
        form.addRow("Cor de destaque:", cor)
        atalhos = QLabel(
            "<b>Atalhos</b><br>"
            "Ctrl+K — buscar<br>"
            "Ctrl+Enter — aplicar nos clipes selecionados<br>"
            "F5 — conectar / atualizar clipes<br>"
            "Ctrl+S — salvar como meu preset<br>"
            "Esc — limpar a busca<br>"
            "Arraste um cartão até um clipe para aplicar direto.")
        atalhos.setObjectName("dica")
        form.addRow(atalhos)
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(dialogo.accept)
        form.addRow(fechar)
        dialogo.exec()

    # -- biblioteca -------------------------------------------------------------

    def recriar_cartoes(self):
        for cartao in self.cartoes.values():
            cartao.setParent(None)
            cartao.deleteLater()
        self.cartoes = {nome: Cartao(nome, self) for nome in self.biblioteca.nomes()}
        cor_previa = QColor(TEMAS[self.tema]["previa"])
        for cartao in self.cartoes.values():
            cartao.previa.cor_fundo = cor_previa
        if self.selecionado in self.cartoes:
            self.cartoes[self.selecionado].selecionar(True)
        self.aplicar_filtro()
        if hasattr(self, "curva"):
            self.opcoes_mudaram()

    def animar(self):
        self.global_frame += 1
        for cartao in self.cartoes.values():
            if cartao.isVisible():
                cartao.previa.tick(self.global_frame)

    def colunas(self):
        return max(1, (self.rolagem.viewport().width() + 14) // 184)

    def aplicar_filtro(self):
        nomes = self.biblioteca.filtrar(self.filtro, self.busca.text())
        while self.grade.count():
            self.grade.takeAt(0)
        for cartao in self.cartoes.values():
            cartao.hide()
        self.vazio_grade.hide()
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
        self.resultado.setText("%d DE %d ANIMAÇÕES"
                               % (len(nomes), len(self.biblioteca.nomes())))
        for nome, contagem in self.contagens.items():
            contagem.setText(str(len(self.biblioteca.filtrar(nome))))

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        QTimer.singleShot(0, self.aplicar_filtro)

    def focar_busca(self):
        self.busca.setFocus()
        self.busca.selectAll()

    def mudar_filtro(self, nome):
        self.filtro = nome
        self.aplicar_filtro()

    def favoritar(self, nome, marcado):
        if marcado:
            self.biblioteca.favoritos.add(nome)
        else:
            self.biblioteca.favoritos.discard(nome)
        self.salvar_biblioteca()
        self.aplicar_filtro()

    def selecionar(self, nome):
        if nome not in self.cartoes:
            nome = next(iter(Animador.PRESETS))
        self.selecionado = nome
        for n, cartao in self.cartoes.items():
            cartao.selecionar(n == nome)
        categoria, descricao, _ = self.biblioteca.info(nome)
        self.nome_selecionado.setText(nome)
        self.desc_selecionado.setText("%s  ·  %s" % (categoria, descricao))
        meu = self.biblioteca.meus.get(nome)
        if meu:
            # Carrega as opções salvas no preset do usuário.
            self.duracao.setValue(int(meu["duracao"]))
            self.curva.setCurrentText(meu["curva"] or PADRAO_CURVA)
            self.intensidade.setValue(int(round(meu["intensidade"] * 100)))
        self.opcoes_mudaram()
        self.atualizar_botao()

    def opcoes_atuais(self):
        """(preset base, curva ou None, intensidade, duração)"""
        _, _, base = self.biblioteca.info(self.selecionado)
        curva = self.curva.currentText()
        return (base, None if curva == PADRAO_CURVA else curva,
                self.intensidade.value() / 100.0, self.duracao.value())

    def opcoes_mudaram(self):
        if self.selecionado is None:
            return
        base, curva, intensidade, duracao = self.opcoes_atuais()
        self.valor_intensidade.setText("%d%%" % self.intensidade.value())
        if curva:
            self.grafico.definir(Animador.EASINGS[curva])
        else:
            self.grafico.definir(Animador.PRESETS[base][0][3])
        for cartao in self.cartoes.values():
            cartao.atualizar(duracao, curva, intensidade, self.acento())

    def atualizar_saida(self):
        no_inicio = self.posicoes.checkedId() == 0
        self.saida.setEnabled(no_inicio)
        if not no_inicio:
            self.saida.setCurrentIndex(0)

    def salvar_meu(self):
        base, curva, intensidade, duracao = self.opcoes_atuais()
        sugestao = "%s (meu)" % base
        nome, ok = QInputDialog.getText(self, "Salvar como meu preset",
                                        "Nome do preset:", text=sugestao)
        if not ok:
            return
        nome = nome.strip()
        try:
            self.biblioteca.salvar_meu(nome, base, curva, intensidade, duracao)
        except ValueError as erro:
            self.mostrar(str(erro), "erro")
            return
        self.salvar_biblioteca()
        self.recriar_cartoes()
        self.selecionar(nome)
        self.mostrar("✓  Preset '%s' salvo em Meus presets." % nome, "ok")

    def excluir_meu(self, nome):
        resposta = QMessageBox.question(self, "Excluir preset", "Excluir '%s'?" % nome)
        if resposta != QMessageBox.Yes:
            return
        self.biblioteca.excluir_meu(nome)
        self.salvar_biblioteca()
        if self.selecionado == nome:
            self.selecionado = None
        self.recriar_cartoes()
        self.selecionar(self.selecionado or next(iter(Animador.PRESETS)))

    # -- DaVinci ---------------------------------------------------------------

    nome_timeline = None

    def mostrar(self, texto, tipo="info"):
        cores = {"info": TEMAS[self.tema]["texto3"], "ok": "#22c55e", "erro": "#ef4444"}
        self.status.setStyleSheet("color: %s;" % cores[tipo])
        self.status.setText(texto)

    def definir_conexao(self, nome):
        if nome:
            texto = '<span style="color:#22c55e">●</span>&nbsp; CONECTADO  ·  %s' % (
                nome.upper())
        else:
            texto = ('<span style="color:%s">●</span>&nbsp; DESCONECTADO  ·  '
                     'F5 PARA CONECTAR' % self.acento())
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
            self.nome_timeline = nome
            self.definir_conexao(nome)
        self.mostrar("%d clipe(s) encontrados. Selecione ou arraste uma animação até eles."
                     % len(clipes), "ok" if clipes else "info")

    def atualizar(self):
        try:
            if self.resolve is None:
                self.resolve = self.backend.conectar_resolve()
            timeline = self.backend.timeline_atual(self.resolve)
            clipes = self.backend.listar_clipes(timeline)
        except Exception as erro:  # mostra qualquer falha da API na janela
            self.resolve = None
            self.nome_timeline = None
            self.definir_conexao(None)
            self.mostrar("Erro: %s" % erro, "erro")
            return
        self.mostrar_clipes(clipes, timeline.GetName())

    def aplicar_em(self, linhas, nome):
        if not linhas or nome is None:
            return
        _, curva, intensidade, duracao = self.opcoes_atuais()
        _, _, base = self.biblioteca.info(nome)
        meu = self.biblioteca.meus.get(nome)
        if meu and nome != self.selecionado:
            curva, intensidade, duracao = meu["curva"], meu["intensidade"], meu["duracao"]
        posicao = self.backend.POSICOES[self.posicoes.checkedId()]
        saida = self.saida.currentText() if self.saida.isEnabled() else "Nenhuma"
        saida = None if saida == "Nenhuma" else saida
        erros = []
        for linha in linhas:
            item = linha.data(Qt.UserRole)
            try:
                self.backend.aplicar_em_clipe(item, base, duracao, posicao, curva,
                                              intensidade, saida)
            except Exception as erro:
                erros.append("%s: %s" % (item.GetName(), erro))
        self.biblioteca.usar(nome)
        self.salvar_biblioteca()
        self.salvar_opcoes()
        self.aplicar_filtro()
        ok = len(linhas) - len(erros)
        extra = " + %s" % saida if saida else ""
        if erros:
            self.mostrar("'%s'%s aplicado em %d clipe(s). Falhas: %s"
                         % (nome, extra, ok, "; ".join(erros)), "erro")
        else:
            self.mostrar("✓  '%s'%s aplicado em %d clipe(s)." % (nome, extra, ok), "ok")

    def aplicar(self):
        self.aplicar_em(self.lista.selectedItems(), self.selecionado)

    def soltar_no_clipe(self, linha, nome):
        self.selecionar(nome)
        self.aplicar_em([linha], nome)

    def remover(self):
        linhas = self.lista.selectedItems()
        if not linhas:
            self.mostrar("Selecione os clipes de onde remover as animações.", "erro")
            return
        total, erros = 0, []
        for linha in linhas:
            item = linha.data(Qt.UserRole)
            try:
                total += self.backend.remover_do_clipe(item)
            except Exception as erro:
                erros.append("%s: %s" % (item.GetName(), erro))
        if erros:
            self.mostrar("Falhas ao remover: " + "; ".join(erros), "erro")
        else:
            self.mostrar("✓  %d nó(s) do Animador removidos de %d clipe(s)."
                         % (total, len(linhas)), "ok")

    # -- atualizações -------------------------------------------------------------

    def buscar_atualizacao(self):
        self.avisador = Avisador()
        self.avisador.nova_versao.connect(self.mostrar_atualizacao)

        def tarefa():
            resultado = self.backend.buscar_atualizacao()
            if resultado:
                self.avisador.nova_versao.emit(*resultado)

        threading.Thread(target=tarefa, daemon=True).start()

    def mostrar_atualizacao(self, versao, link):
        self.botao_atualizacao.setText("⬆  Versão %s disponível" % versao)
        self.botao_atualizacao.setToolTip("Clique para baixar a nova versão")
        self.botao_atualizacao.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(link)))
        self.botao_atualizacao.show()


def criar_janela(backend):
    return JanelaAnimador(backend)
