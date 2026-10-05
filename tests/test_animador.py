import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import Animador as an  # noqa: E402


class FakeOutput:
    def __init__(self, tool):
        self.tool = tool
        self.connected = []

    def GetConnectedInputs(self):
        return {i + 1: inp for i, inp in enumerate(self.connected)}


class FakeInput:
    def __init__(self, owner):
        self.owner = owner
        self.source = None

    def GetConnectedOutput(self):
        return self.source

    def ConnectTo(self, output):
        if self.source:
            self.source.connected.remove(self)
        self.source = output
        output.connected.append(self)


class FakeTool:
    def __init__(self, kind, comp=None):
        self.Name = kind
        self.kind = kind
        self.comp = comp
        self.Output = FakeOutput(self)
        self.Input = FakeInput(self)
        self.modifiers = {}
        self.values = {}

    def ConnectInput(self, name, tool):
        self.Input.ConnectTo(tool.Output)

    def AddModifier(self, name, kind):
        self.modifiers[name] = kind

    def SetInput(self, name, value, frame=None):
        self.values.setdefault(name, {})[frame] = value

    def SetAttrs(self, attrs):
        self.Name = attrs.get("TOOLS_Name", self.Name)

    def Delete(self):
        if self.Input.source:
            self.Input.source.connected.remove(self.Input)
        self.comp.tools.remove(self)


class FakeComp:
    def __init__(self):
        self.tools = []
        self.undo = []

    def AddTool(self, kind, x, y):
        tool = FakeTool(kind, self)
        self.tools.append(tool)
        return tool

    def GetToolList(self, selecionados=False, tipo=None):
        tools = [t for t in self.tools if tipo is None or t.kind == tipo]
        return {i + 1: t for i, t in enumerate(tools)}

    def StartUndo(self, name):
        self.undo.append(name)

    def EndUndo(self, keep):
        pass

    def Lock(self):
        pass

    def Unlock(self):
        pass


class TestEasings(unittest.TestCase):
    def test_easings_comecam_em_0_e_terminam_em_1(self):
        for f in list(an.EASINGS.values()) + [an.ease_in_back]:
            self.assertAlmostEqual(f(0), 0, places=6, msg=f.__name__)
            self.assertAlmostEqual(f(1), 1, places=6, msg=f.__name__)

    def test_pulse_volta_ao_inicio(self):
        self.assertAlmostEqual(an.pulse(0), 0)
        self.assertAlmostEqual(an.pulse(0.5), 1)
        self.assertAlmostEqual(an.pulse(1), 0, places=6)


class TestKeyframes(unittest.TestCase):
    def test_todos_os_presets_geram_keyframes(self):
        for preset in an.PRESETS:
            keys = an.gerar_keyframes(preset, 10, 24)
            for trilha in keys.values():
                self.assertEqual(len(trilha), 25)
                self.assertEqual(trilha[0][0], 10)
                self.assertEqual(trilha[-1][0], 34)

    def test_deslizar_termina_no_centro(self):
        keys = an.gerar_keyframes("Deslizar da esquerda", 0, 12)["Center"]
        self.assertEqual(keys[0][1], (-0.5, 0.5))
        self.assertAlmostEqual(keys[-1][1][0], 0.5)
        self.assertAlmostEqual(keys[-1][1][1], 0.5)

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            an.gerar_keyframes("Nao existe", 0, 10)
        with self.assertRaises(ValueError):
            an.gerar_keyframes("Fade In", 0, 0)


class TestAplicar(unittest.TestCase):
    def test_insere_transform_e_mantem_conexoes(self):
        comp = FakeComp()
        texto = FakeTool("Text1")
        merge = FakeTool("Merge1")
        merge.Input.ConnectTo(texto.Output)

        an.aplicar_preset(comp, texto, "Girar e aparecer", 0, 10)

        transform = comp.tools[0]
        self.assertEqual(transform.Name, "AnimadorTransform1")
        self.assertIs(transform.Input.source, texto.Output)
        self.assertIs(merge.Input.source, transform.Output)
        self.assertEqual(transform.modifiers, {"Angle": "BezierSpline", "Size": "BezierSpline"})
        self.assertEqual(transform.values["Size"][10], 1.0)
        self.assertEqual(comp.undo, ["Animador: Girar e aparecer"])

    def test_center_usa_xypath_com_pontos(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Text1"), "Deslizar de baixo", 0, 4)
        transform = comp.tools[0]
        self.assertEqual(transform.modifiers["Center"], "XYPath")
        self.assertEqual(transform.values["Center"][0], {1: 0.5, 2: -0.5})

    def test_fade_usa_brightness_contrast(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Text1"), "Fade In", 5, 10)
        self.assertEqual([t.kind for t in comp.tools], ["BrightnessContrast"])
        fade = comp.tools[0]
        self.assertEqual(fade.values["ProcessAlpha"][None], 1)
        self.assertEqual(fade.values["Gain"][5], 0.0)
        self.assertAlmostEqual(fade.values["Gain"][15], 1.0)


class TestOpcoes(unittest.TestCase):
    def test_curva_substitui_a_do_preset(self):
        padrao = an.gerar_keyframes("Zoom Pop", 0, 10)["Size"]
        linear = an.gerar_keyframes("Zoom Pop", 0, 10, easing="Linear")["Size"]
        self.assertAlmostEqual(linear[5][1], 0.5)
        self.assertNotAlmostEqual(padrao[5][1], 0.5)

    def test_oscilacao_ignora_curva(self):
        self.assertEqual(an.gerar_keyframes("Balançar", 0, 20),
                         an.gerar_keyframes("Balançar", 0, 20, easing="Linear"))

    def test_curva_invalida(self):
        with self.assertRaises(ValueError):
            an.gerar_keyframes("Fade In", 0, 10, easing="Nao existe")

    def test_intensidade_escala_a_distancia_do_repouso(self):
        dobro = an.gerar_keyframes("Ken Burns", 0, 10, intensidade=2)["Size"]
        self.assertAlmostEqual(dobro[-1][1], 1.4)
        metade = an.gerar_keyframes("Deslizar da esquerda", 0, 10, intensidade=0.5)
        self.assertAlmostEqual(metade["Center"][0][1][0], 0.0)

    def test_valores_limitados(self):
        keys = an.gerar_keyframes("Fade In", 0, 10, intensidade=2)["Gain"]
        self.assertTrue(all(0 <= v <= 1 for _, v in keys))
        tamanhos = an.gerar_keyframes("Zoom Pop", 0, 10, intensidade=2)["Size"]
        self.assertTrue(all(v >= 0 for _, v in tamanhos))

    def test_todo_preset_tem_categoria(self):
        self.assertEqual(set(an.PRESETS), set(an.CATEGORIAS))
        self.assertGreaterEqual(len(an.PRESETS), 25)


class TestNos(unittest.TestCase):
    def test_desfoque_cria_transform_blur_e_fade_em_ordem(self):
        comp = FakeComp()
        imagem = FakeTool("MediaIn1", comp)
        comp.tools.append(imagem)
        saida = FakeTool("MediaOut1", comp)
        comp.tools.append(saida)
        saida.Input.ConnectTo(imagem.Output)

        an.aplicar_preset(comp, imagem, "Desfoque de entrada", 0, 10)

        blur, fade = comp.tools[2], comp.tools[3]
        self.assertEqual((blur.kind, fade.kind), ("Blur", "BrightnessContrast"))
        self.assertIs(blur.Input.source, imagem.Output)
        self.assertIs(fade.Input.source, blur.Output)
        self.assertIs(saida.Input.source, fade.Output)

    def test_nomes_nao_se_repetem(self):
        comp = FakeComp()
        imagem = FakeTool("MediaIn1", comp)
        comp.tools.append(imagem)
        an.aplicar_preset(comp, imagem, "Zoom Pop", 0, 10)
        an.aplicar_preset(comp, imagem, "Pulsar", 0, 10)
        nomes = [t.Name for t in comp.tools if t.kind == "Transform"]
        self.assertEqual(sorted(nomes), ["AnimadorTransform1", "AnimadorTransform2"])

    def test_remover_religa_a_imagem(self):
        comp = FakeComp()
        imagem = FakeTool("MediaIn1", comp)
        saida = FakeTool("MediaOut1", comp)
        comp.tools += [imagem, saida]
        saida.Input.ConnectTo(imagem.Output)
        an.aplicar_preset(comp, imagem, "Desfoque de entrada", 0, 10)
        an.aplicar_preset(comp, imagem, "Girar e aparecer", 0, 10)

        self.assertEqual(an.remover_animacoes(comp), 3)
        self.assertEqual([t.Name for t in comp.tools], ["MediaIn1", "MediaOut1"])
        self.assertIs(saida.Input.source, imagem.Output)
        self.assertEqual(an.remover_animacoes(comp), 0)


if __name__ == "__main__":
    unittest.main()
