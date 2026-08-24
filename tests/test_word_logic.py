import unittest
import game


class TestWordLogic(unittest.TestCase):
    def test_getcode_format(self):
        code = game.getcode()
        self.assertIsInstance(code, str)
        self.assertEqual(len(code), 4)
        self.assertTrue(code.isdigit())
        self.assertTrue(1000 <= int(code) <= 9999)

    def test_getword_structure_and_scramble(self):
        for _ in range(15):
            chosen_word, scrambled_word, word_len, difficulty = game.getword()

            self.assertIsInstance(chosen_word, str)
            self.assertIsInstance(scrambled_word, str)
            self.assertEqual(len(chosen_word), word_len)
            self.assertEqual(len(scrambled_word), word_len)
            self.assertEqual(sorted(list(chosen_word)), sorted(list(scrambled_word)))
            if len(chosen_word) > 1:
                self.assertNotEqual(chosen_word, scrambled_word)

    def test_difficulty_classification(self):
        for _ in range(15):
            chosen_word, scrambled_word, word_len, difficulty = game.getword()

            if word_len <= 4:
                self.assertEqual(difficulty, 'easy')
            elif word_len <= 6:
                self.assertEqual(difficulty, 'medium')
            else:
                self.assertEqual(difficulty, 'hard')


if __name__ == '__main__':
    unittest.main()
