import unittest
import sqlite3
import os


class TestDatabase(unittest.TestCase):
    """Unit tests for SQLite database schema and operations."""

    DB_PATH = "database.db"

    def setUp(self):
        self.assertTrue(os.path.exists(self.DB_PATH), f"{self.DB_PATH} must exist.")
        self.conn = sqlite3.connect(self.DB_PATH)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_words_table_schema(self):
        """Test that the words table exists and has expected columns."""
        self.cursor.execute("PRAGMA table_info(words)")
        columns = {col[1]: col[2] for col in self.cursor.fetchall()}
        
        self.assertIn("id", columns)
        self.assertIn("word", columns)
        self.assertIn("len", columns)
        self.assertIn("difficulty", columns)

    def test_words_data_integrity(self):
        """Test that words table contains valid records with matching lengths."""
        self.cursor.execute("SELECT COUNT(*) FROM words")
        count = self.cursor.fetchone()[0]
        self.assertGreater(count, 1000, "Database should contain a significant word list.")

        self.cursor.execute("SELECT word, len, difficulty FROM words LIMIT 50")
        rows = self.cursor.fetchall()
        for word, length, diff in rows:
            self.assertEqual(len(word), length)
            self.assertIn(diff.lower(), ['easy', 'medium', 'hard'])

    def test_scores_table_schema(self):
        """Test that the scores table exists and has expected columns."""
        self.cursor.execute("PRAGMA table_info(scores)")
        columns = {col[1]: col[2] for col in self.cursor.fetchall()}
        
        self.assertIn("id", columns)
        self.assertIn("name", columns)
        self.assertIn("points", columns)
        self.assertIn("timestamp", columns)

    def test_score_insertion_and_leaderboard_query(self):
        """Test inserting a match score and querying aggregated leaderboard stats."""
        test_player = "__test_player_xyz__"
        
        # Insert test scores
        self.cursor.execute("INSERT INTO scores (name, points) VALUES (?, ?)", (test_player, 40))
        self.cursor.execute("INSERT INTO scores (name, points) VALUES (?, ?)", (test_player, 60))
        self.conn.commit()

        # Query aggregated total points
        self.cursor.execute('''
            SELECT name, SUM(points) as total_points,
                   (SELECT timestamp FROM scores s2 WHERE s2.name = s1.name ORDER BY points DESC LIMIT 1) as peak_time
            FROM scores s1
            WHERE name = ?
            GROUP BY name
        ''', (test_player,))
        
        result = self.cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], test_player)
        self.assertEqual(result[1], 100)  # 40 + 60

        # Clean up test rows
        self.cursor.execute("DELETE FROM scores WHERE name = ?", (test_player,))
        self.conn.commit()


if __name__ == '__main__':
    unittest.main()
