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

    def ConnectTo(self, output):
        if self.source:
            self.source.connected.remove(self)
        self.source = output
        output.connected.append(self)


class FakeTool:
    def __init__(self, kind):
        self.Name = kind
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


class FakeComp:
    def __init__(self):
        self.tools = []
        self.undo = []

    def AddTool(self, kind, x, y):
        tool = FakeTool(kind)
        self.tools.append(tool)
        return tool

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
        for f in (an.linear, an.ease_in_out_sine, an.ease_out_cubic,
                  an.ease_out_back, an.ease_out_bounce):
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
        self.assertEqual(transform.Name, "Transform")
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
        self.assertEqual([t.Name for t in comp.tools], ["BrightnessContrast"])
        fade = comp.tools[0]
        self.assertEqual(fade.values["ProcessAlpha"][None], 1)
        self.assertEqual(fade.values["Gain"][5], 0.0)
        self.assertAlmostEqual(fade.values["Gain"][15], 1.0)


if __name__ == "__main__":
    unittest.main()
