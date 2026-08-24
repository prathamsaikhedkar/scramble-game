import unittest
import game


class TestSecurity(unittest.TestCase):
    def setUp(self):
        game.app.config['TESTING'] = True
        self.client = game.app.test_client()

        game.room_codes.clear()
        game.points.clear()
        game.readyplayers.clear()
        game.currentword.clear()

    def test_secret_key_is_set_and_secure(self):
        """Verify SECRET_KEY is not default insecure string."""
        secret = game.app.config.get("SECRET_KEY")
        self.assertIsNotNone(secret)
        self.assertNotEqual(secret, "idk")

    def test_reject_oversized_username(self):
        """Verify usernames longer than 15 characters are rejected."""
        response = self.client.post('/', data={
            'entered_name': 'A' * 20,
            'create': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name too long', response.data)

    def test_reject_whitespace_only_username(self):
        """Verify usernames with only spaces are rejected as empty."""
        response = self.client.post('/', data={
            'entered_name': '     ',
            'create': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'empty name', response.data)

    def test_validate_handles_malformed_payload(self):
        """Verify WebSocket validate event ignores non-dict or non-string inputs safely."""
        room_id = '7777'
        game.room_codes[room_id] = {'player_count': 0, 'players': {}, 'started': False}

        self.client.post('/', data={
            'entered_name': 'TestUser',
            'join': 'true',
            'room_code': room_id
        })
        ws_client = game.socketio.test_client(game.app, flask_test_client=self.client)
        game.currentword[room_id] = {'TestUser': 'apple'}

        # Non-dict payload
        ws_client.emit('validate', 'not-a-dict')
        # Dict with non-string guess
        ws_client.emit('validate', {'guess': 12345})
        # Empty dict
        ws_client.emit('validate', {})

        # Ensure no exception and points unchanged
        self.assertEqual(game.points[room_id]['TestUser'], 0)


if __name__ == '__main__':
    unittest.main()
