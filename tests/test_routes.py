import unittest
import game


class TestRoutes(unittest.TestCase):
    def setUp(self):
        game.app.config['TESTING'] = True
        game.app.config['SECRET_KEY'] = 'test-secret'
        self.client = game.app.test_client()

        game.room_codes.clear()
        game.points.clear()
        game.readyplayers.clear()
        game.currentword.clear()

    def test_home_get(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SCRAMBLE', response.data)

    def test_home_empty_name(self):
        response = self.client.post('/', data={'entered_name': '', 'create': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'empty name', response.data)

    def test_home_missing_room_code(self):
        response = self.client.post('/', data={
            'entered_name': 'Player1',
            'join': 'true',
            'room_code': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'no room code', response.data)

    def test_home_invalid_room_code(self):
        response = self.client.post('/', data={
            'entered_name': 'Player1',
            'join': 'true',
            'room_code': '9999'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'invalid code', response.data)

    def test_home_create_room(self):
        response = self.client.post('/', data={
            'entered_name': 'HostUser',
            'create': 'true'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/game', response.headers['Location'])
        self.assertEqual(len(game.room_codes), 1)

    def test_home_join_room(self):
        game.room_codes['1234'] = {'player_count': 1, 'players': {}, 'started': False}

        response = self.client.post('/', data={
            'entered_name': 'GuestUser',
            'join': 'true',
            'room_code': '1234'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/game', response.headers['Location'])

    def test_home_join_started_room(self):
        game.room_codes['1234'] = {'player_count': 2, 'players': {}, 'started': True}

        response = self.client.post('/', data={
            'entered_name': 'LateUser',
            'join': 'true',
            'room_code': '1234'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'round has already started', response.data)

    def test_game_page_without_room(self):
        response = self.client.get('/game')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'room not found', response.data)

    def test_leaderboard_endpoint(self):
        response = self.client.get('/leaderboard')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIsInstance(json_data, dict)
        self.assertIn('leaderboard', json_data)
        self.assertIsInstance(json_data['leaderboard'], list)


if __name__ == '__main__':
    unittest.main()
