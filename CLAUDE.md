# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

mobstiq is a local multiplayer game host. A Python back-end ([chisel](https://github.com/craigahobbs/chisel) WSGI app served by waitress) holds the player and game state. The front-end is written in BareScript and runs in the browser through MarkdownUp. One "main" screen (for example a TV) shows a QR code. Players scan it on their phones, which opens the "controller" view (`#var.vView='control'`). From there they register, pick a game, join it and take turns.

## Build system

The build uses [python-build](https://github.com/craigahobbs/python-build). On first run, the `Makefile` downloads `Makefile.base` and `pylintrc`, or copies them from `../python-build` if that directory exists. Both files are gitignored, so don't edit or commit them. Venvs are created under `build/venv/` and have no pip. Add test-only packages to `TESTS_REQUIRE` in the `Makefile` instead of installing them with pip. If `../python-build/SKILL.md` exists, it is the full playbook for downstream packages.

| Command | Purpose |
| --- | --- |
| `make commit` | Full quality gate: `test`, `lint`, `doc`, `cover`, plus `test-app` |
| `make test` | Python unittests (`-W error`, discovered from `src/tests/`) |
| `make test TEST=tests.test_app.TestApp.test_init` | Run a single Python test (also works with `make cover`) |
| `make cover` | Branch coverage. **Fails below 100%.** |
| `make lint` | pylint. Docstring warnings are disabled in the `Makefile`. |
| `make test-app` | BareScript checks: static analysis (`bare -x` on `static/*.bare` and the test files, `bare -s` on `runTests.bare`), then the BareScript unit tests (`bare -d`) |
| `make test-app TEST=testMobstiq` | Run a single BareScript test |
| `make run ARGS='-n -v'` | Run the app locally (`-n` skips opening a browser, `-v` turns on access logging, `-p` sets the port, `-c` sets the config file) |

## Architecture

**Back-end (`src/mobstiq/app.py`).** `Mobstiq` is a `chisel.Application`. All API request and response types are defined in Schema Markdown in `src/mobstiq/static/mobstiq.smd`, which is parsed at import time into `MOBSTIQ_TYPES`. Every `@chisel.action` refers to its types by name, so a new API needs a matching `action` in `mobstiq.smd` and a matching `self.add_request(...)` call in `Mobstiq.__init__`.

**State.** The only state is a JSON config file, `mobstiq.json` by default. `main.py` looks for it in the current directory first, then in `$HOME`. `ConfigManager` is a lock-guarded context manager: `with ctx.app.config(save=True) as config:` writes the file back on exit unless `config['noSave']` is set. The config holds `players` (keyed by UUID) and at most one `game`. A game is in setup until `game['current']` is set by `gameStart`. After that, `gameUpdate` stores an opaque `state` from the current player and passes the turn to the next player.

**Front-end (`src/mobstiq/static/`).** `index.html` is a MarkdownUp shell that includes `mobstiq.bare` and calls `mobstiqMain()`. The MarkdownUp runtime files under `./markdown-up/` are served by `chisel.create_doc_requests()`. The UI stays in sync by polling `gameState` every 250 ms and re-rendering whenever the state changes.

**Static files have to be registered in three places.** Any new file under `static/` must be added to:
1. `Mobstiq.__init__` (`self.add_static(...)`)
2. `[tool.setuptools.package-data]` in `pyproject.toml`
3. The expected request list in `src/tests/test_app.py` (`test_init` and `test_init_missing_config`)

**Game plugin contract.** Games are listed in `GAMES` in `app.py` with a name, an include path, an entry function, and the minimum and maximum number of players. The `gameInclude` action returns generated BareScript that includes the active game's `.bare` file and sets `mobstiqGameIncludeFunction`. `mobstiqRunGame` loads it with `include 'gameInclude'` and calls the entry function with a `gameObj`:
- `self`: the player on this device, or `null` on the main screen
- `players`: the players, in turn order
- `game`: the `CurrentGame` from the back-end, including its opaque `state`
- `updateFn(state)`: only present when it is this device's turn
- `stopFn()`: only present for players in the game

To add a game, write `games/<name>.bare` (`games/ticTacToe.bare` is the reference implementation), add an entry to `GAMES`, and register the file as a static in all three places above.

## Tests

- Python tests in `src/tests/` cover the back-end and must keep coverage at 100%. `src/tests/util.py:create_test_files` builds temporary config files for them.
- BareScript tests live in `src/mobstiq/static/test/`. `runTests.bare` includes each `test*.bare` file and enforces `coverageMin`. You can also run them in a browser through `test/index.html`.
- Use the `bare-script` skill when writing or changing `.bare` files.
