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

ESTILO = """
QWidget { background: #1f1f23; color: #e6e6e6; font-size: 13px; }
QGroupBox { border: 1px solid #3a3a40; border-radius: 6px; margin-top: 14px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #a0a0a8; }
QListWidget, QComboBox, QSpinBox {
    background: #2a2a30; border: 1px solid #3a3a40; border-radius: 4px; padding: 4px;
}
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background: #e8613c; color: white; }
QPushButton {
    background: #34343b; border: 1px solid #45454d; border-radius: 4px; padding: 7px 12px;
}
QPushButton:hover { background: #3f3f47; }
QPushButton#aplicar { background: #e8613c; border: none; color: white; font-weight: bold; padding: 10px; }
QPushButton#aplicar:hover { background: #f07250; }
QPushButton#aplicar:disabled { background: #5a3a30; color: #b0a0a0; }
QLabel#status { color: #a0a0a8; }
"""


def criar_janela():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractItemView, QButtonGroup, QComboBox, QFormLayout, QGroupBox,
        QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
        QRadioButton, QSpinBox, QVBoxLayout, QWidget,
    )

    class JanelaAnimador(QWidget):
        def __init__(self):
            super().__init__()
            self.resolve = None
            self.setWindowTitle("Animador para DaVinci Resolve")
            self.resize(560, 600)
            self.setStyleSheet(ESTILO)

            conectar = QPushButton("Conectar / Atualizar")
            conectar.clicked.connect(self.atualizar)
            todos = QPushButton("Selecionar todos")
            todos.clicked.connect(lambda: self.lista.selectAll())
            topo = QHBoxLayout()
            topo.addWidget(conectar)
            topo.addWidget(todos)
            topo.addStretch()

            self.lista = QListWidget()
            self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.lista.itemSelectionChanged.connect(self.atualizar_botao)

            self.preset = QComboBox()
            self.preset.addItems(list(Animador.PRESETS))
            self.duracao = QSpinBox()
            self.duracao.setRange(1, 1000)
            self.duracao.setValue(24)
            self.duracao.setSuffix(" frames")
            self.posicoes = QButtonGroup(self)
            linha_pos = QHBoxLayout()
            for i, texto in enumerate(POSICOES):
                botao = QRadioButton(texto)
                botao.setChecked(i == 0)
                self.posicoes.addButton(botao, i)
                linha_pos.addWidget(botao)
            linha_pos.addStretch()

            formulario = QFormLayout()
            formulario.addRow("Preset:", self.preset)
            formulario.addRow("Duração:", self.duracao)
            formulario.addRow("Posição:", linha_pos)
            grupo = QGroupBox("Animação")
            grupo.setLayout(formulario)

            self.aplicar_btn = QPushButton("Aplicar nos clipes selecionados")
            self.aplicar_btn.setObjectName("aplicar")
            self.aplicar_btn.clicked.connect(self.aplicar)

            self.status = QLabel("Abra o DaVinci e clique em Conectar.")
            self.status.setObjectName("status")
            self.status.setWordWrap(True)

            layout = QVBoxLayout(self)
            layout.addLayout(topo)
            layout.addWidget(QLabel("Clipes da timeline (Ctrl/Shift para escolher vários):"))
            layout.addWidget(self.lista, 1)
            layout.addWidget(grupo)
            layout.addWidget(self.aplicar_btn)
            layout.addWidget(self.status)
            self.atualizar_botao()

        def mostrar_clipes(self, clipes):
            self.lista.clear()
            for trilha, item in clipes:
                linha = QListWidgetItem("V%d   %s   (%d frames)" % (
                    trilha, item.GetName(), int(item.GetDuration())))
                linha.setData(Qt.UserRole, item)
                self.lista.addItem(linha)
            self.status.setText("%d clipe(s) encontrados." % len(clipes))

        def atualizar(self):
            try:
                if self.resolve is None:
                    self.resolve = conectar_resolve()
                clipes = listar_clipes(timeline_atual(self.resolve))
            except Exception as erro:  # mostra qualquer falha da API na janela
                self.resolve = None
                self.status.setText("Erro: %s" % erro)
                return
            self.mostrar_clipes(clipes)

        def atualizar_botao(self):
            n = len(self.lista.selectedItems())
            self.aplicar_btn.setEnabled(n > 0)
            self.aplicar_btn.setText("Aplicar em %d clipe(s)" % n if n
                                     else "Selecione clipes para aplicar")

        def aplicar(self):
            preset = self.preset.currentText()
            posicao = POSICOES[self.posicoes.checkedId()]
            selecionados = self.lista.selectedItems()
            erros = []
            for linha in selecionados:
                item = linha.data(Qt.UserRole)
                try:
                    aplicar_em_clipe(item, preset, self.duracao.value(), posicao)
                except Exception as erro:
                    erros.append("%s: %s" % (item.GetName(), erro))
            texto = "'%s' aplicado em %d clipe(s)." % (preset, len(selecionados) - len(erros))
            if erros:
                texto += " Falhas: " + "; ".join(erros)
            self.status.setText(texto)

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
