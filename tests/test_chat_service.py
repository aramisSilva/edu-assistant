import unittest
from unittest.mock import patch

from src.services.chat_service import classify_topic


class ChatServiceTest(unittest.TestCase):
    def test_classifies_derivatives_in_general_chat(self):
        self.assertEqual(classify_topic("general", "Pode me explicar derivadas?"), "Derivadas")

    def test_classifies_accentless_aliases(self):
        self.assertEqual(classify_topic("general", "Tenho dúvida sobre limite tendendo a zero"), "Limites")
        self.assertEqual(classify_topic("general", "Como resolver uma integral por partes?"), "Integrais")

    def test_unknown_subject_uses_general_fallback(self):
        self.assertEqual(classify_topic("general", "Boa tarde, tudo bem?"), "Dúvidas gerais")

    def test_uses_llm_for_unregistered_academic_topic(self):
        with patch("src.services.chat_service.generate_topic_label", return_value="Teorema de Stokes"):
            self.assertEqual(classify_topic("general", "Como aplico Stokes nessa curva fechada?"), "Teorema de Stokes")

    def test_discards_invalid_llm_topic(self):
        long_topic = "Este é um texto muito longo que parece explicação e não um rótulo de tópico acadêmico"
        with patch("src.services.chat_service.generate_topic_label", return_value=long_topic):
            self.assertEqual(classify_topic("general", "Como aplico Stokes nessa curva fechada?"), "Dúvidas gerais")


if __name__ == "__main__":
    unittest.main()
