import unittest
import sqlite3
import game


class TestSocketIOEvents(unittest.TestCase):
    def setUp(self):
        game.app.config['TESTING'] = True
        game.app.config['SECRET_KEY'] = 'test-secret'

        game.room_codes.clear()
        game.points.clear()
        game.readyplayers.clear()
        game.currentword.clear()

    def _create_and_connect_player(self, name, room_code):
        http_client = game.app.test_client()
        http_client.post('/', data={
            'entered_name': name,
            'join': 'true',
            'room_code': room_code
        })
        ws_client = game.socketio.test_client(game.app, flask_test_client=http_client)
        return ws_client

    def test_connect_unauthenticated(self):
        http_client = game.app.test_client()
        ws_client = game.socketio.test_client(game.app, flask_test_client=http_client)
        self.assertTrue(ws_client.is_connected())
        self.assertEqual(len(game.room_codes), 0)

    def test_connect_authenticated_player(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client = self._create_and_connect_player('Player1', room_id)
        self.assertTrue(ws_client.is_connected())

        self.assertEqual(game.room_codes[room_id]['player_count'], 1)
        self.assertIn('Player1', game.points[room_id])
        self.assertEqual(game.points[room_id]['Player1'], 0)
        self.assertFalse(game.readyplayers['Player1'])

        received = ws_client.get_received()
        player_added_event = next((e for e in received if e['name'] == 'playeradded'), None)
        self.assertIsNotNone(player_added_event)
        self.assertEqual(player_added_event['args'][0], {'Player1': 0})
        self.assertEqual(player_added_event['args'][1], room_id)

    def test_disconnect_cleans_up_state(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client = self._create_and_connect_player('Player1', room_id)
        self.assertEqual(game.room_codes[room_id]['player_count'], 1)

        ws_client.disconnect()
        self.assertNotIn(room_id, game.room_codes)
        self.assertNotIn(room_id, game.points)
        self.assertNotIn('Player1', game.readyplayers)

    def test_ready_starts_game_when_all_players_ready(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client1 = self._create_and_connect_player('Player1', room_id)
        ws_client2 = self._create_and_connect_player('Player2', room_id)

        ws_client1.emit('ready')
        self.assertFalse(game.room_codes[room_id]['started'])

        ws_client1.get_received()
        ws_client2.get_received()

        ws_client2.emit('ready')
        self.assertTrue(game.room_codes[room_id]['started'])
        self.assertIn(room_id, game.currentword)
        self.assertIn('Player1', game.currentword[room_id])
        self.assertIn('Player2', game.currentword[room_id])

        rec1 = ws_client1.get_received()
        rec2 = ws_client2.get_received()

        event1 = next((e for e in rec1 if e['name'] == 'startgame'), None)
        event2 = next((e for e in rec2 if e['name'] == 'startgame'), None)

        self.assertIsNotNone(event1)
        self.assertIsNotNone(event2)
        self.assertEqual(len(event1['args']), 3)

    def test_validate_correct_guess(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client = self._create_and_connect_player('Player1', room_id)
        game.currentword[room_id] = {'Player1': 'cat'}
        ws_client.get_received()

        ws_client.emit('validate', {'guess': 'cat'})
        rec = ws_client.get_received()

        val_event = next((e for e in rec if e['name'] == 'validatedguess'), None)
        self.assertIsNotNone(val_event)
        self.assertEqual(val_event['args'][0], 10)

        self.assertEqual(game.points[room_id]['Player1'], 10)
        pts_event = next((e for e in rec if e['name'] == 'ptsupdate'), None)
        self.assertIsNotNone(pts_event)
        self.assertEqual(pts_event['args'], ['Player1', 10])

        newword_event = next((e for e in rec if e['name'] == 'newword'), None)
        self.assertIsNotNone(newword_event)

    def test_validate_incorrect_guess(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client = self._create_and_connect_player('Player1', room_id)
        game.currentword[room_id] = {'Player1': 'elephant'}
        ws_client.get_received()

        ws_client.emit('validate', {'guess': 'wrongguess'})
        rec = ws_client.get_received()

        val_event = next((e for e in rec if e['name'] == 'validatedguess'), None)
        self.assertIsNotNone(val_event)
        self.assertEqual(val_event['args'][0], 0)
        self.assertEqual(game.points[room_id]['Player1'], 0)

    def test_skip_word_deducts_points(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client = self._create_and_connect_player('Player1', room_id)
        game.points[room_id]['Player1'] = 20
        game.currentword[room_id] = {'Player1': 'pear'}
        ws_client.get_received()

        ws_client.emit('skip')
        rec = ws_client.get_received()

        self.assertEqual(game.points[room_id]['Player1'], 10)

        pts_event = next((e for e in rec if e['name'] == 'ptsupdate'), None)
        self.assertIsNotNone(pts_event)
        self.assertEqual(pts_event['args'], ['Player1', 10])

        newword_event = next((e for e in rec if e['name'] == 'newword'), None)
        self.assertIsNotNone(newword_event)

    def test_gameover_calculates_winner_and_saves_scores(self):
        room_id = '5555'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        ws_client1 = self._create_and_connect_player('Alice', room_id)
        ws_client2 = self._create_and_connect_player('Bob', room_id)

        game.points[room_id]['Alice'] = 80
        game.points[room_id]['Bob'] = 40
        ws_client1.get_received()
        ws_client2.get_received()

        ws_client1.emit('gameover')

        rec1 = ws_client1.get_received()
        gameover_event = next((e for e in rec1 if e['name'] == 'gameovertoall'), None)
        self.assertIsNotNone(gameover_event)
        self.assertEqual(gameover_event['args'][0], 'Alice')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM scores WHERE name = 'Alice' ORDER BY id DESC LIMIT 1")
        alice_score = cursor.fetchone()
        self.assertIsNotNone(alice_score)
        self.assertEqual(alice_score[0], 80)

        cursor.execute("DELETE FROM scores WHERE name IN ('Alice', 'Bob')")
        conn.commit()
        conn.close()


if __name__ == '__main__':
    unittest.main()
