# Licensed under the MIT License
# https://github.com/craigahobbs/mobstiq/blob/main/LICENSE

import json
import os
import unittest
import unittest.mock
import uuid

from mobstiq.app import Mobstiq

from .util import create_test_files


class TestApp(unittest.TestCase):

    def test_init(self):
        test_files = [
            (('mobstiq.json',), json.dumps({'players': {}}))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)
            self.assertEqual(app.config.config_path, config_path)
            with app.config() as config:
                self.assertDictEqual(config, {'players': {}})
            self.assertListEqual(
                sorted(request.name for request in app.requests.values() if request.doc_group.startswith('mobstiq ')),
                [
                    'gameAddPlayer',
                    'gameInclude',
                    'gameRemovePlayer',
                    'gameSetup',
                    'gameStart',
                    'gameState',
                    'gameStop',
                    'gameUpdate',
                    'games/checkers.bare',
                    'games/ticTacToe.bare',
                    'getGameList',
                    'getServiceURL',
                    'index.html',
                    'mobstiq.bare',
                    'playerRegister',
                    'playerValidate'
                ]
            )


    def test_init_missing_config(self):
        with unittest.mock.patch('os.path.isfile', return_value=False) as mock_isfile:
            app = Mobstiq('mobstiq.json')
            mock_isfile.assert_called_once_with('mobstiq.json')
            self.assertEqual(app.config.config_path, 'mobstiq.json')
            with app.config() as config:
                self.assertDictEqual(config, {'players': {}})
            self.assertListEqual(
                sorted(request.name for request in app.requests.values() if request.doc_group.startswith('mobstiq ')),
                [
                    'gameAddPlayer',
                    'gameInclude',
                    'gameRemovePlayer',
                    'gameSetup',
                    'gameStart',
                    'gameState',
                    'gameStop',
                    'gameUpdate',
                    'games/checkers.bare',
                    'games/ticTacToe.bare',
                    'getGameList',
                    'getServiceURL',
                    'index.html',
                    'mobstiq.bare',
                    'playerRegister',
                    'playerValidate'
                ]
            )


class TestAPI(unittest.TestCase):

    def test_get_service_url(self):
        with create_test_files([]) as temp_dir, \
             unittest.mock.patch('socket.getaddrinfo', return_value=[
                 (2, 1, 6, '', ('127.0.0.1', 0)),
                 (2, 1, 6, '', ('192.168.1.100', 0))
             ]) as mock_getaddrinfo:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/getServiceURL')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'url': 'http://192.168.1.100:8080'})
            mock_getaddrinfo.assert_called_once()

            # Verify the app config
            expected_config = {'players': {}}
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertFalse(os.path.exists(config_path))


    def test_get_game_list(self):
        with create_test_files([]) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/getGameList')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {
                'games': [
                    {
                        'function': 'checkersMain',
                        'include': 'games/checkers.bare',
                        'maxPlayers': 2,
                        'minPlayers': 2,
                        'name': 'Checkers'
                    },
                    {
                        'function': 'ticTacToeMain',
                        'include': 'games/ticTacToe.bare',
                        'maxPlayers': 2,
                        'minPlayers': 2,
                        'name': 'Tic Tac Toe'
                    }
                ]
            })

            # Verify the app config
            expected_config = {'players': {}}
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertFalse(os.path.exists(config_path))


    def test_player_register(self):
        with create_test_files([]) as temp_dir, \
             unittest.mock.patch('uuid.uuid4', return_value=uuid.UUID('123e4567e89b12d3a456426614174000')):
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('POST', '/playerRegister', wsgi_input=b'{"name": "Player 1"}')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'name': 'Player 1'
            })

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_player_register_name_in_use(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('POST', '/playerRegister', wsgi_input=b'{"name": "Player 1"}')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NameInUse'})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_player_validate(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = \
                app.request('POST', '/playerValidate', wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'name': 'Player 1'
            })

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_player_validate_invalid_player(self):
        with create_test_files([]) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = \
                app.request('POST', '/playerValidate', wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config
            expected_config = {'players': {}}
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertFalse(os.path.exists(config_path))


    def test_game_state(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/gameState')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            })

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_state_no_game(self):
        with create_test_files([]) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/gameState')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {'players': {}}
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertFalse(os.path.exists(config_path))


    def test_game_setup(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameSetup',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Tic Tac Toe"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_setup_invalid_player(self):
        with create_test_files([]) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameSetup',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Tic Tac Toe"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config
            expected_config = {'players': {}}
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertFalse(os.path.exists(config_path))


    def test_game_setup_invalid_function(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameSetup',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Invalid Game"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidName'})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_setup_in_use(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Chess',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameSetup',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Tic Tac Toe"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InUse'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Chess',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_add_player(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameAddPlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_add_player_already_added(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameAddPlayer',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_add_player_invalid_player(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameAddPlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_add_player_no_game(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameAddPlayer',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInSetup'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_add_player_not_in_setup(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {}
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameAddPlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertDictEqual(response, {'error': 'NotInSetup'})
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {}
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_add_player_too_many(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    },
                    '323e4567-e89b-12d3-a456-426614174000': {
                        'id': '323e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 3'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameAddPlayer',
                wsgi_input=b'{"id": "323e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'TooManyPlayers'})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    },
                    '323e4567-e89b-12d3-a456-426614174000': {
                        'id': '323e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 3'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_remove_player(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameRemovePlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_remove_player_invalid_player(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameRemovePlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_remove_player_not_in_setup(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {}
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameRemovePlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInSetup'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {}
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_remove_player_not_in_game(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameRemovePlayer',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_start(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStart',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000'
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_start_no_game(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStart',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInSetup'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_start_not_in_setup(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000'
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStart',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInSetup'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000'
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_start_invalid_player(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStart',
                wsgi_input=b'{"id": "323e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_start_too_few_players(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStart',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'TooFewPlayers'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': ['123e4567-e89b-12d3-a456-426614174000']
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_update(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000'
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameUpdate',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000", "state": {"board": ["X", "", "", "", "", "", "", "", ""]}}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '223e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_update_round_robin(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '223e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameUpdate',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000", "state": {"board": ["X", "O", "", "", "", "", "", "", ""]}}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', 'O', '', '', '', '', '', '', '']}
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_update_not_in_play(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameUpdate',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000", "state": {"board": ["X", "", "", "", "", "", "", "", ""]}}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInPlay'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_update_invalid_player_not_current(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000'
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameUpdate',
                wsgi_input=b'{"id": "223e4567-e89b-12d3-a456-426614174000", "state": {"board": ["X", "", "", "", "", "", "", "", ""]}}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000'
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_stop(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStop',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config - game should be removed
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_stop_not_in_play(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStop',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_stop_no_game(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStop',
                wsgi_input=b'{"id": "123e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInPlay'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_stop_invalid_player(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    },
                    '323e4567-e89b-12d3-a456-426614174000': {
                        'id': '323e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 3'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request(
                'POST', '/gameStop',
                wsgi_input=b'{"id": "323e4567-e89b-12d3-a456-426614174000"}'
            )
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'InvalidPlayer'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    },
                    '323e4567-e89b-12d3-a456-426614174000': {
                        'id': '323e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 3'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_include(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/gameInclude')
            response = content_bytes.decode('utf-8')
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'text/plain; charset=utf-8')])
            self.assertEqual(response, "include 'games/ticTacToe.bare'\n")

            # Verify the app config - game should be removed
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ],
                    'current': '123e4567-e89b-12d3-a456-426614174000',
                    'state': {'board': ['X', '', '', '', '', '', '', '', '']}
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_include_not_in_play(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/gameInclude')
            response = content_bytes.decode('utf-8')
            self.assertEqual(status, '200 OK')
            self.assertListEqual(headers, [('Content-Type', 'text/plain; charset=utf-8')])
            self.assertEqual(response, "include 'games/ticTacToe.bare'\n")

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    },
                    '223e4567-e89b-12d3-a456-426614174000': {
                        'id': '223e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 2'
                    }
                },
                'game': {
                    'name': 'Tic Tac Toe',
                    'players': [
                        '123e4567-e89b-12d3-a456-426614174000',
                        '223e4567-e89b-12d3-a456-426614174000'
                    ]
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)


    def test_game_include_no_game(self):
        test_files = [
            ('mobstiq.json', json.dumps({
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }))
        ]
        with create_test_files(test_files) as temp_dir:
            config_path = os.path.join(temp_dir, 'mobstiq.json')
            app = Mobstiq(config_path)

            status, headers, content_bytes = app.request('GET', '/gameInclude')
            response = json.loads(content_bytes.decode('utf-8'))
            self.assertEqual(status, '400 Bad Request')
            self.assertListEqual(headers, [('Content-Type', 'application/json')])
            self.assertDictEqual(response, {'error': 'NotInPlay'})

            # Verify the app config (unchanged)
            expected_config = {
                'players': {
                    '123e4567-e89b-12d3-a456-426614174000': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'name': 'Player 1'
                    }
                }
            }
            with app.config() as config:
                self.assertDictEqual(config, expected_config)

            # Verify the config file
            self.assertTrue(os.path.exists(config_path))
            with open(config_path, 'r', encoding='utf-8') as fh:
                saved_config = json.loads(fh.read())
                self.assertDictEqual(saved_config, expected_config)
