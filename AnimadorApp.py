"""
Animador App - programa com janela que controla o DaVinci Resolve Studio.

Lista os clipes da timeline aberta, e aplica os presets do Animador.py nos
clipes selecionados (cada clipe ganha uma composição Fusion com a animação).

Requisitos:
- DaVinci Resolve Studio aberto, com um projeto e uma timeline.
- Em Preferences > System > General, "External scripting using" = Local.
- Python 3 (64 bits) instalado. Rode: python AnimadorApp.py
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
# Interface
# ---------------------------------------------------------------------------


class AnimadorApp:
    def __init__(self, raiz):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.raiz = raiz
        self.resolve = None
        self.clipes = []

        raiz.title("Animador para DaVinci Resolve")
        raiz.geometry("520x520")
        raiz.minsize(420, 420)

        quadro = ttk.Frame(raiz, padding=12)
        quadro.pack(fill="both", expand=True)

        topo = ttk.Frame(quadro)
        topo.pack(fill="x")
        ttk.Button(topo, text="Conectar / Atualizar", command=self.atualizar).pack(side="left")
        ttk.Button(topo, text="Selecionar todos", command=self.selecionar_todos).pack(side="left", padx=6)

        ttk.Label(quadro, text="Clipes da timeline (Ctrl/Shift para escolher vários):").pack(
            anchor="w", pady=(12, 4))
        lista_quadro = ttk.Frame(quadro)
        lista_quadro.pack(fill="both", expand=True)
        self.lista = tk.Listbox(lista_quadro, selectmode="extended", activestyle="none")
        barra = ttk.Scrollbar(lista_quadro, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        self.lista.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        opcoes = ttk.LabelFrame(quadro, text="Animação", padding=10)
        opcoes.pack(fill="x", pady=12)
        opcoes.columnconfigure(1, weight=1)

        ttk.Label(opcoes, text="Preset:").grid(row=0, column=0, sticky="w")
        self.preset = ttk.Combobox(opcoes, values=list(Animador.PRESETS), state="readonly")
        self.preset.current(0)
        self.preset.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(opcoes, text="Duração (frames):").grid(row=1, column=0, sticky="w")
        self.duracao = tk.IntVar(value=24)
        ttk.Spinbox(opcoes, from_=1, to=1000, textvariable=self.duracao, width=8).grid(
            row=1, column=1, sticky="w", pady=2)

        ttk.Label(opcoes, text="Posição:").grid(row=2, column=0, sticky="w")
        self.posicao = tk.StringVar(value=POSICOES[0])
        pos_quadro = ttk.Frame(opcoes)
        pos_quadro.grid(row=2, column=1, sticky="w")
        for texto in POSICOES:
            ttk.Radiobutton(pos_quadro, text=texto, value=texto,
                            variable=self.posicao).pack(side="left", padx=(0, 10))

        ttk.Button(quadro, text="Aplicar nos clipes selecionados",
                   command=self.aplicar).pack(fill="x")
        self.status = ttk.Label(quadro, text="Clique em Conectar com o DaVinci aberto.",
                                wraplength=480)
        self.status.pack(anchor="w", pady=(8, 0))

    def mostrar(self, texto):
        self.status.configure(text=texto)

    def atualizar(self):
        try:
            if self.resolve is None:
                self.resolve = conectar_resolve()
            self.clipes = listar_clipes(timeline_atual(self.resolve))
        except Exception as erro:  # mostra qualquer falha da API na janela
            self.resolve = None
            self.mostrar("Erro: %s" % erro)
            return
        self.lista.delete(0, "end")
        for trilha, item in self.clipes:
            self.lista.insert("end", "V%d  |  %s  (%d frames)" % (
                trilha, item.GetName(), int(item.GetDuration())))
        self.mostrar("%d clipe(s) encontrados." % len(self.clipes))

    def selecionar_todos(self):
        self.lista.selection_set(0, "end")

    def aplicar(self):
        indices = self.lista.curselection()
        if not indices:
            self.mostrar("Selecione pelo menos um clipe.")
            return
        try:
            duracao = int(self.duracao.get())
        except (ValueError, self.tk.TclError):
            self.mostrar("Duração inválida.")
            return
        preset = self.preset.get()
        erros = []
        for i in indices:
            item = self.clipes[i][1]
            try:
                aplicar_em_clipe(item, preset, duracao, self.posicao.get())
            except Exception as erro:
                erros.append("%s: %s" % (item.GetName(), erro))
        ok = len(indices) - len(erros)
        texto = "'%s' aplicado em %d clipe(s)." % (preset, ok)
        if erros:
            texto += " Falhas: " + "; ".join(erros)
        self.mostrar(texto)


def main():
    import tkinter as tk

    raiz = tk.Tk()
    AnimadorApp(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
