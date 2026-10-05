import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import AnimadorApp as app  # noqa: E402
from test_animador import FakeComp, FakeTool  # noqa: E402


class FakeTimelineComp(FakeComp):
    def __init__(self, inicio, fim):
        super().__init__()
        self.media_in = FakeTool("MediaIn1", self)
        self.tools.append(self.media_in)
        self.attrs = {"COMPN_RenderStart": inicio, "COMPN_RenderEnd": fim}

    def GetToolList(self, selecionados=False, tipo=None):
        if tipo == "MediaIn":
            return {1: self.media_in}
        return super().GetToolList(selecionados, tipo)

    def GetAttrs(self):
        return self.attrs


class FakeItem:
    def __init__(self, comps=0, duracao=100):
        self.comps = [FakeTimelineComp(0, duracao - 1) for _ in range(comps)]
        self.duracao = duracao

    def GetName(self):
        return "foto.jpg"

    def GetDuration(self):
        return self.duracao

    def GetFusionCompCount(self):
        return len(self.comps)

    def GetFusionCompByIndex(self, i):
        return self.comps[i - 1]

    def AddFusionComp(self):
        self.comps.append(FakeTimelineComp(0, self.duracao - 1))
        return self.comps[-1]


class FakeTimeline:
    def __init__(self, trilhas):
        self.trilhas = trilhas

    def GetTrackCount(self, tipo):
        return len(self.trilhas)

    def GetItemListInTrack(self, tipo, i):
        return self.trilhas[i - 1]


class TestAnimadorApp(unittest.TestCase):
    def test_cria_comp_quando_clipe_nao_tem(self):
        item = FakeItem(comps=0)
        app.aplicar_em_clipe(item, "Zoom Pop", 20, app.POSICOES[0])
        comp = item.comps[0]
        transform = comp.tools[1]
        self.assertIs(transform.Input.source, comp.media_in.Output)
        self.assertEqual(min(transform.values["Size"]), 0)

    def test_reusa_comp_existente(self):
        item = FakeItem(comps=1)
        app.aplicar_em_clipe(item, "Fade In", 10, app.POSICOES[0])
        self.assertEqual(len(item.comps), 1)

    def test_fim_do_clipe_termina_no_ultimo_frame(self):
        item = FakeItem(comps=1, duracao=100)
        app.aplicar_em_clipe(item, "Fade Out", 24, app.POSICOES[1])
        gain = item.comps[0].tools[1].values["Gain"]
        self.assertEqual(min(gain), 75)
        self.assertEqual(max(gain), 99)

    def test_duracao_maior_que_clipe_e_limitada(self):
        item = FakeItem(comps=1, duracao=10)
        app.aplicar_em_clipe(item, "Fade In", 500, app.POSICOES[0])
        self.assertEqual(max(item.comps[0].tools[1].values["Gain"]), 9)

    def test_listar_clipes_de_todas_as_trilhas(self):
        a, b, c = FakeItem(), FakeItem(), FakeItem()
        clipes = app.listar_clipes(FakeTimeline([[a, b], [], [c]]))
        self.assertEqual([t for t, _ in clipes], [1, 1, 3])

    def test_entrada_e_saida_no_mesmo_clipe(self):
        item = FakeItem(comps=1, duracao=100)
        app.aplicar_em_clipe(item, "Zoom Pop", 20, app.POSICOES[0], saida="Fade Out")
        comp = item.comps[0]
        tipos = sorted(t.kind for t in comp.tools)
        self.assertEqual(tipos, ["BrightnessContrast", "MediaIn1", "Transform"])
        fade = [t for t in comp.tools if t.kind == "BrightnessContrast"][0]
        self.assertEqual((min(fade.values["Gain"]), max(fade.values["Gain"])), (79, 99))

    def test_curva_e_intensidade_chegam_ao_motor(self):
        item = FakeItem(comps=1)
        app.aplicar_em_clipe(item, "Ken Burns", 10, app.POSICOES[0], "Linear", 2.0)
        size = item.comps[0].tools[1].values["Size"]
        self.assertAlmostEqual(size[10], 1.4)
        self.assertAlmostEqual(size[5], 1.2)

    def test_remover_do_clipe(self):
        item = FakeItem(comps=1)
        app.aplicar_em_clipe(item, "Desfoque de entrada", 10, app.POSICOES[0])
        self.assertEqual(app.remover_do_clipe(item), 2)
        self.assertEqual([t.Name for t in item.comps[0].tools], ["MediaIn1"])


class TestAtualizacao(unittest.TestCase):
    def test_compara_versoes(self):
        self.assertGreater(app.versao_tupla("v2.10.0"), app.versao_tupla("2.9.1"))
        self.assertEqual(app.versao_tupla("V2.0"), (2, 0))

    def test_falha_de_rede_e_ignorada(self):
        self.assertIsNone(app.buscar_atualizacao(repositorio="nao/existe", timeout=0.01))


if __name__ == "__main__":
    unittest.main()
