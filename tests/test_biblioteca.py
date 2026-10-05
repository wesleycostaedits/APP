import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import interface
except ImportError:  # PySide6 não instalado: pula estes testes
    interface = None


@unittest.skipIf(interface is None, "PySide6 não instalado")
class TestBiblioteca(unittest.TestCase):
    def setUp(self):
        self.b = interface.Biblioteca()

    def test_filtra_por_categoria_e_busca(self):
        fotos = self.b.filtrar("Fotos")
        self.assertIn("Ken Burns", fotos)
        self.assertNotIn("Fade In", fotos)
        self.assertEqual(self.b.filtrar("Todos", "panorâmica para a dir"),
                         ["Panorâmica para a direita"])

    def test_meus_presets(self):
        self.b.salvar_meu("Pop forte", "Zoom Pop", "Elástico", 1.5, 30)
        self.assertEqual(self.b.filtrar("Meus presets"), ["Pop forte"])
        self.assertEqual(self.b.info("Pop forte")[2], "Zoom Pop")
        self.assertIn("Pop forte", self.b.filtrar("Todos", "zoom pop"))
        with self.assertRaises(ValueError):
            self.b.salvar_meu("Fade In", "Fade In", None, 1, 24)
        with self.assertRaises(ValueError):
            self.b.salvar_meu("  ", "Fade In", None, 1, 24)

    def test_excluir_limpa_favorito_e_recente(self):
        self.b.salvar_meu("X", "Pulsar", None, 1, 24)
        self.b.favoritos.add("X")
        self.b.usar("X")
        self.b.excluir_meu("X")
        self.assertEqual((self.b.filtrar("Favoritos"), self.b.filtrar("Recentes")), ([], []))

    def test_recentes_sem_repetir_e_limitados(self):
        for nome in list(interface.Animador.PRESETS)[:10]:
            self.b.usar(nome)
        self.b.usar("Fade In")
        self.assertEqual(self.b.recentes[0], "Fade In")
        self.assertEqual(len(self.b.recentes), interface.MAX_RECENTES)
        self.assertEqual(len(set(self.b.recentes)), len(self.b.recentes))

    def test_estilo_monta_para_todos_os_temas(self):
        for tema in interface.TEMAS:
            for cor in interface.CORES:
                self.assertNotIn("$", interface.montar_estilo(tema, cor))


if __name__ == "__main__":
    unittest.main()
