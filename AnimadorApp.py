"""
Animador App - programa com janela que controla o DaVinci Resolve Studio.

Lista os clipes da timeline aberta, e aplica os presets do Animador.py nos
clipes selecionados (cada clipe ganha uma composição Fusion com a animação).

Requisitos:
- DaVinci Resolve Studio aberto, com um projeto e uma timeline.
- Em Preferences > System > General, "External scripting using" = Local.
- Python 3 (64 bits) e PySide6 (pip install -r requirements.txt).
  Rode: python AnimadorApp.py (ou use o Animador.exe, que já traz tudo).
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import Animador  # noqa: E402

VERSAO = "2.0.1"
REPOSITORIO = "wesleycostaedits/app"
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


def _carregar_fusionscript(lib):
    """Carrega a biblioteca de scripting do DaVinci direto do arquivo."""
    import importlib.machinery
    import importlib.util

    carregador = importlib.machinery.ExtensionFileLoader("fusionscript", lib)
    spec = importlib.util.spec_from_file_location("fusionscript", lib, loader=carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


def conectar_resolve():
    """Devolve o objeto `resolve` ou levanta RuntimeError com uma mensagem clara."""
    modulos, padrao = _caminhos_padrao()
    lib = os.environ.get("RESOLVE_SCRIPT_LIB", padrao)
    if os.path.exists(lib):
        try:
            api = _carregar_fusionscript(lib)
        except Exception as erro:
            raise RuntimeError("Não consegui carregar a API do DaVinci (%s): %s" % (lib, erro))
    else:
        # Instalação fora do lugar padrão: tenta o módulo que acompanha o DaVinci.
        os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
        if modulos not in sys.path:
            sys.path.append(modulos)
        try:
            import DaVinciResolveScript as api
        except ImportError:
            raise RuntimeError("Não encontrei a API do DaVinci Resolve. "
                               "O DaVinci Resolve está instalado?")
    resolve = api.scriptapp("Resolve")
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


def aplicar_em_clipe(item, preset, duracao, posicao, easing=None, intensidade=1.0,
                     saida=None):
    """Aplica `preset` no início ou no fim do clipe e, opcionalmente, um preset
    de `saida` terminando no último frame (para entrada + saída de uma vez)."""
    comp = comp_do_clipe(item)
    inicio, fim = intervalo_comp(comp, item)
    limite = max(1, fim - inicio)
    duracao = max(1, min(int(duracao), limite))
    frame = inicio if posicao == POSICOES[0] else fim - duracao
    imagem = media_in(comp)
    Animador.aplicar_preset(comp, imagem, preset, frame, duracao, easing, intensidade)
    if saida:
        dur_saida = max(1, min(int(duracao), limite))
        Animador.aplicar_preset(comp, imagem, saida, fim - dur_saida, dur_saida,
                                easing, intensidade)


def remover_do_clipe(item):
    """Remove as animações do Animador de todas as composições do clipe."""
    total = 0
    for i in range(1, int(item.GetFusionCompCount()) + 1):
        total += Animador.remover_animacoes(item.GetFusionCompByIndex(i))
    return total


# ---------------------------------------------------------------------------
# Atualizações (GitHub Releases)
# ---------------------------------------------------------------------------


def versao_tupla(texto):
    numeros = []
    for parte in str(texto).lstrip("vV").split("."):
        digitos = "".join(c for c in parte if c.isdigit())
        numeros.append(int(digitos) if digitos else 0)
    return tuple(numeros)


def buscar_atualizacao(atual=VERSAO, repositorio=REPOSITORIO, timeout=4):
    """Devolve (versão, link) se houver versão mais nova publicada, senão None.

    Falhas de rede ou repositório privado são ignoradas em silêncio.
    """
    url = "https://api.github.com/repos/%s/releases/latest" % repositorio
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": "Animador"})
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            dados = json.load(resposta)
    except Exception:
        return None
    tag = dados.get("tag_name") or ""
    if tag and versao_tupla(tag) > versao_tupla(atual):
        return tag.lstrip("vV"), dados.get("html_url") or ""
    return None


def pasta_recursos():
    """Pasta dos arquivos do app, também quando empacotado pelo PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "recursos")


def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 não está instalado. Rode: pip install -r requirements.txt")
        sys.exit(1)
    import interface

    app = QApplication(sys.argv)
    app.setApplicationName("Animador")
    janela = interface.criar_janela(sys.modules[__name__])
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
