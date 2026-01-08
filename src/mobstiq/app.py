# Licensed under the MIT License
# https://github.com/craigahobbs/mobstiq/blob/main/LICENSE

"""
The mobstiq back-end application
"""

from contextlib import contextmanager
import json
import os
import importlib.resources
import socket
import threading
import uuid

import chisel
import schema_markdown


# The mobstiq back-end API WSGI application class
class Mobstiq(chisel.Application):
    __slots__ = ('config',)


    def __init__(self, config_path):
        super().__init__()
        self.config = ConfigManager(config_path)

        # Back-end documentation
        self.add_requests(chisel.create_doc_requests())

        # Back-end APIs
        self.add_request(game_add_player)
        self.add_request(game_include)
        self.add_request(game_remove_player)
        self.add_request(game_setup)
        self.add_request(game_start)
        self.add_request(game_state)
        self.add_request(game_stop)
        self.add_request(game_update)
        self.add_request(get_game_list)
        self.add_request(get_service_url)
        self.add_request(player_register)
        self.add_request(player_validate)

        # Front-end statics
        self.add_static('index.html', urls=(('GET', None), ('GET', '/')))
        self.add_static('mobstiq.bare')
        self.add_static('games/ticTacToe.bare')


    def add_static(self, filename, urls=(('GET', None),), doc_group='mobstiq Statics'):
        with importlib.resources.files('mobstiq.static').joinpath(filename).open('rb') as fh:
            self.add_request(chisel.StaticRequest(filename, fh.read(), urls=urls, doc_group=doc_group))


# The mobstiq configuration context manager
class ConfigManager:
    __slots__ = ('config_path', 'config_lock', 'config')


    def __init__(self, config_path):
        self.config_path = config_path
        self.config_lock = threading.Lock()

        # Ensure the config file exists with default config if it doesn't exist
        if os.path.isfile(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as fh_config:
                self.config = schema_markdown.validate_type(MOBSTIQ_TYPES, 'MobstiqConfig', json.loads(fh_config.read()))
        else:
            self.config = {'players': {}}


    @contextmanager
    def __call__(self, save=False):
        # Acquire the config lock
        self.config_lock.acquire()

        try:
            # Yield the config on context entry
            yield self.config

            # Save the config file on context exit, if requested
            if save and not self.config.get('noSave'):
                with open(self.config_path, 'w', encoding='utf-8') as fh_config:
                    config_json = schema_markdown.JSONEncoder(indent=4).encode(self.config)
                    fh_config.write(config_json)
        finally:
            # Release the config lock
            self.config_lock.release()


# The mobstiq API type model
with importlib.resources.files('mobstiq.static').joinpath('mobstiq.smd').open('r') as cm_smd:
    MOBSTIQ_TYPES = schema_markdown.parse_schema_markdown(cm_smd.read())


# The game list
GAMES = schema_markdown.validate_type(MOBSTIQ_TYPES, 'GameInfos', [
    {
        'name': 'Checkers',
        'include': 'games/checkers.bare',
        'function': 'checkersMain',
        'minPlayers': 2,
        'maxPlayers': 2
    },
    {
        'name': 'Tic Tac Toe',
        'include': 'games/ticTacToe.bare',
        'function': 'ticTacToeMain',
        'minPlayers': 2,
        'maxPlayers': 2
    }
])


@chisel.action(name='getServiceURL', types=MOBSTIQ_TYPES)
def get_service_url(unused_ctx, unused_req):
    # Get the first non-loopback IP
    hostname = socket.gethostname()
    addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
    local_ips = [info[4][0] for info in addr_info if not info[4][0].startswith('127.')]
    local_ip = local_ips[0]
    return {
        'url': f'http://{local_ip}:8080'
    }


@chisel.action(name='getGameList', types=MOBSTIQ_TYPES)
def get_game_list(unused_ctx, unused_req):
    return {
        'games': sorted(GAMES, key=lambda x: x['name'])
    }


@chisel.action(name='playerRegister', types=MOBSTIQ_TYPES)
def player_register(ctx, req):
    with ctx.app.config(save=True) as config:
        # Name in use?
        name = req['name']
        players = config['players']
        if any(player for player in players.values() if name == player['name']):
            raise chisel.ActionError('NameInUse')

        # Add the new player
        player_id = str(uuid.uuid4())
        player = {'id': player_id, 'name': name}
        players[player_id] = player
        return player


@chisel.action(name='playerValidate', types=MOBSTIQ_TYPES)
def player_validate(ctx, req):
    with ctx.app.config() as config:
        # Unknown ID?
        id_ = req['id']
        players = config['players']
        if id_ not in players:
            raise chisel.ActionError('InvalidPlayer')

        # Return the player
        return players[id_]


@chisel.action(name='gameState', types=MOBSTIQ_TYPES)
def game_state(ctx, unused_req):
    with ctx.app.config() as config:
        if 'game' in config:
            return {'game': config['game']}
        return {}


@chisel.action(name='gameSetup', types=MOBSTIQ_TYPES)
def game_setup(ctx, req):
    with ctx.app.config(save=True) as config:
        # Unknown ID?
        id_ = req['id']
        if id_ not in config['players']:
            raise chisel.ActionError('InvalidPlayer')

        # Unknown function?
        game_name = req['name']
        if not any(game_info for game_info in GAMES if game_info['name'] == game_name):
            raise chisel.ActionError('InvalidName')

        # Game in play?
        if 'game' in config:
            raise chisel.ActionError('InUse')

        # Create new game
        config['game'] = {
            'name': game_name,
            'players': [id_]
        }


@chisel.action(name='gameAddPlayer', types=MOBSTIQ_TYPES)
def game_add_player(ctx, req):
    with ctx.app.config(save=True) as config:
        # Unknown ID?
        id_ = req['id']
        if id_ not in config['players']:
            raise chisel.ActionError('InvalidPlayer')

        # No game?
        game = config.get('game')
        if game is None or 'current' in game:
            raise chisel.ActionError('NotInSetup')

        # Already added?
        if id_ in game['players']:
            raise chisel.ActionError('InvalidPlayer')

        # Too many players?
        game_name = game['name']
        game_info = next(game_info for game_info in GAMES if game_info['name'] == game_name)
        if len(game['players']) >= game_info['maxPlayers']:
            raise chisel.ActionError('TooManyPlayers')

        # Add the player
        game['players'].append(id_)


@chisel.action(name='gameRemovePlayer', types=MOBSTIQ_TYPES)
def game_remove_player(ctx, req):
    with ctx.app.config(save=True) as config:
        # No game in setup?
        game = config.get('game')
        if game is None or 'current' in game:
            raise chisel.ActionError('NotInSetup')

        # Not in the game?
        id_ = req['id']
        if id_ not in game['players']:
            raise chisel.ActionError('InvalidPlayer')

        # Remove the player
        game['players'].remove(id_)


@chisel.action(name='gameStart', types=MOBSTIQ_TYPES)
def game_start(ctx, req):
    with ctx.app.config(save=True) as config:
        # No game in setup?
        game = config.get('game')
        if game is None or 'current' in game:
            raise chisel.ActionError('NotInSetup')

        # Player not in the game?
        id_ = req['id']
        if id_ not in game['players']:
            raise chisel.ActionError('InvalidPlayer')

        # Too few players?
        game_name = game['name']
        game_info = next(game_info for game_info in GAMES if game_info['name'] == game_name)
        if len(game['players']) < game_info['minPlayers']:
            raise chisel.ActionError('TooFewPlayers')

        # Start the game
        game['current'] = game['players'][0]


@chisel.action(name='gameUpdate', types=MOBSTIQ_TYPES)
def game_update(ctx, req):
    with ctx.app.config(save=True) as config:
        # Check game in play
        game = config.get('game')
        if game is None or 'current' not in game:
            raise chisel.ActionError('NotInPlay')

        # Check player is in the game and is the current player
        id_ = req['id']
        if game['current'] != id_:
            raise chisel.ActionError('InvalidPlayer')

        # Update the game state
        game['state'] = req['state']

        # Advance to the next player
        players = game['players']
        current_index = players.index(id_)
        next_index = (current_index + 1) % len(players)
        game['current'] = players[next_index]


@chisel.action(name='gameStop', types=MOBSTIQ_TYPES)
def game_stop(ctx, req):
    with ctx.app.config(save=True) as config:
        # Check game in play
        game = config.get('game')
        if game is None:
            raise chisel.ActionError('NotInPlay')

        # Player not in the game?
        id_ = req['id']
        if id_ not in game['players']:
            raise chisel.ActionError('InvalidPlayer')

        # Stop the game
        del config['game']


@chisel.action(name='gameInclude', types=MOBSTIQ_TYPES, wsgi_response=True)
def game_include(ctx, unused_req):
    with ctx.app.config() as config:
        # Check game in play
        game = config.get('game')
        if game is None:
            raise chisel.ActionError('NotInPlay')

        # Get the game info
        game_name = game['name']
        game_info = next(game_info for game_info in GAMES if game_info['name'] == game_name)
        game_info_include = game_info['include']

        # Return the BareScript with the game include
        ctx.start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
        return [f"include '{game_info_include}'\n".encode('utf-8')]
