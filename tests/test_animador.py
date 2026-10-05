import os
import re
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

    def GetTool(self):
        return self.tool


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
    """Imita um nó (ou modificador) do Fusion: inputs como atributos, valores e keyframes."""

    def __init__(self, kind, comp=None):
        self.Name = kind
        self.kind = kind
        self.comp = comp
        self.Output = FakeOutput(self)
        self.entradas = {"Input": FakeInput(self)}
        self.values = {}
        self.keyframes = None

    @property
    def Input(self):
        return self.entradas["Input"]

    def __getattr__(self, nome):
        if nome[:1].isupper():
            return self.entradas.setdefault(nome, FakeInput(self))
        raise AttributeError(nome)

    def ConnectInput(self, name, tool):
        getattr(self, name).ConnectTo(tool.Output)

    def AddModifier(self, name, kind):
        modificador = FakeTool(kind, self.comp)
        getattr(self, name).ConnectTo(modificador.Output)
        return True

    def mod(self, nome):
        """Modificador ligado ao input `nome` (para os testes)."""
        saida = getattr(self, nome).source
        return saida.tool if saida else None

    def SetInput(self, name, value, frame=None):
        self.values[name] = value

    def SetKeyFrames(self, chaves, substituir):
        self.keyframes = {f: v[1] for f, v in chaves.items()}

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


def entrada(setting, bloco, nome):
    """Valor numérico do input `nome` dentro do bloco `bloco` de um texto colado."""
    corpo = re.search(r"\t\t%s = \w+ \{(.*?)\n\t\t\}" % bloco, setting, re.S).group(1)
    return float(re.search(r"%s = Input \{ Value = ([-\d.e]+)" % nome, corpo).group(1))


def chaves(setting, bloco):
    """Frames dos keyframes de um BezierSpline do texto colado."""
    corpo = re.search(r"\t\t%s = BezierSpline \{(.*?)\n\t\t\}" % bloco, setting, re.S).group(1)
    return [int(f) for f in re.findall(r"\[(-?\d+)\] = \{", corpo)]


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
    def test_insere_um_transform_e_mantem_conexoes(self):
        comp = FakeComp()
        texto = FakeTool("Text1", comp)
        merge = FakeTool("Merge1", comp)
        merge.Input.ConnectTo(texto.Output)

        an.aplicar_preset(comp, texto, "Girar e aparecer", 0, 10)

        self.assertEqual(len(comp.tools), 1)
        transform = comp.tools[0]
        self.assertEqual((transform.kind, transform.Name), ("Transform", "AnimadorTransform1"))
        self.assertIs(transform.Input.source, texto.Output)
        self.assertIs(merge.Input.source, transform.Output)
        self.assertEqual(comp.undo, ["Animador: Girar e aparecer"])

    def test_curva_vem_do_animcurves_com_dois_keyframes(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Img", comp), "Zoom Pop", 5, 30, easing="Elástico")
        curvas = comp.tools[0].mod("Size")
        self.assertEqual(curvas.kind, "LUTLookup")
        self.assertEqual(curvas.values, {"Source": "Custom", "Curve": "Easing", "EaseIn": "Linear",
                                         "EaseOut": "Elastic", "Scale": 1.0, "Offset": 0.0})
        rampa = curvas.mod("Input")
        self.assertEqual((rampa.kind, rampa.keyframes), ("BezierSpline", {5: 0.0, 35: 1.0}))

    def test_center_usa_xypath_com_eixos_separados(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Img", comp), "Deslizar de baixo", 0, 4)
        xy = comp.tools[0].mod("Center")
        self.assertEqual(xy.kind, "XYPath")
        self.assertEqual(xy.values["X"], 0.5)
        y = xy.mod("Y")
        self.assertEqual((y.values["Offset"], y.values["Scale"]), (-0.5, 1.0))
        self.assertEqual(y.mod("Input").keyframes, {0: 0.0, 4: 1.0})

    def test_valor_constante_nao_cria_animacao(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Img", comp), "Panorâmica para a direita", 0, 10)
        transform = comp.tools[0]
        self.assertEqual(transform.values["Size"], 1.2)
        self.assertIsNone(transform.mod("Size"))

    def test_oscilacao_usa_keyframes(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Img", comp), "Balançar", 10, 20)
        spline = comp.tools[0].mod("Angle")
        self.assertEqual(spline.kind, "BezierSpline")
        self.assertEqual(sorted(spline.keyframes), list(range(10, 31)))

    def test_fade_usa_um_brightness_contrast(self):
        comp = FakeComp()
        an.aplicar_preset(comp, FakeTool("Img", comp), "Fade In", 5, 10)
        self.assertEqual([t.kind for t in comp.tools], ["BrightnessContrast"])
        fade = comp.tools[0]
        self.assertEqual(fade.values["ProcessAlpha"], 1)
        self.assertEqual(fade.mod("Gain").mod("Input").keyframes, {5: 0.0, 15: 1.0})

    def test_todos_os_presets_e_curvas_funcionam(self):
        for preset in an.PRESETS:
            for easing in [None] + list(an.EASINGS):
                comp = FakeComp()
                an.aplicar_preset(comp, FakeTool("Img", comp), preset, 0, 12, easing, 1.5)
                self.assertIn(len(comp.tools), (1, 2))


class TestSetting(unittest.TestCase):
    """montar_setting gera o mesmo nó como texto .setting, para colar no Fusion."""

    def test_formato_igual_ao_exportado_pelo_fusion(self):
        s = an.montar_setting("Transform", "T1", an.gerar_trilhas("Zoom Pop", "Elástico"), 5, 30)
        self.assertTrue(s.startswith("{\n\tTools = ordered() {"))
        self.assertIn("T1Size = LUTLookup", s)
        self.assertIn('EaseOut = Input { Value = FuID { "Elastic" }, }', s)
        self.assertEqual(chaves(s, "T1SizeTempo"), [5, 35])
        self.assertEqual(entrada(s, "T1Size", "Scale"), 1)

    def test_center_e_constantes(self):
        s = an.montar_setting("Transform", "T1",
                              an.gerar_trilhas("Panorâmica para a direita"), 0, 10)
        self.assertEqual(entrada(s, "T1", "Size"), 1.2)
        self.assertEqual(entrada(s, "T1Center", "Y"), 0.5)
        self.assertEqual(entrada(s, "T1CenterX", "Offset"), 0.44)


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

        self.assertEqual(len(comp.tools), 4)
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
