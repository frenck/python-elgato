# Python: Asynchronous client for Elgato Lights

[![GitHub Release][releases-shield]][releases]
[![Python Versions][python-versions-shield]][pypi]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE.md)

[![Build Status][build-shield]][build]
[![Code Coverage][codecov-shield]][codecov]
[![OpenSSF Scorecard][scorecard-shield]][scorecard]
[![Open in Dev Containers][devcontainer-shield]][devcontainer]

[![Sponsor Frenck via GitHub Sponsors][github-sponsors-shield]][github-sponsors]

[![Support Frenck on Patreon][patreon-shield]][patreon]

Asynchronous Python client for Elgato Lights.

## About

This package allows you to control and monitor Elgato Light devices
programmatically. It is mainly created to allow third-party programs to automate
the behavior of an Elgato Light device.

Known compatible and tested Elgato devices:

- Elgato Key Light
- Elgato Key Light Air
- Elgato Key Light Mini
- Elgato Light Strip

## Installation

```bash
pip install elgato
```

To install with the optional CLI:

```bash
pip install "elgato[cli]"
```

## CLI

The optional CLI lets you control Elgato Lights directly from the terminal.
The `--host` option can also be set via the `ELGATO_HOST` environment variable.

```bash
# Show device information
elgato info --host elgato-key-light.local

# Show the current light state
elgato state --host elgato-key-light.local

# Turn the light on (optionally set brightness and temperature)
elgato on --host elgato-key-light.local --brightness 80 --temperature 200

# Turn the light off
elgato off --host elgato-key-light.local

# Identify the light (makes it blink)
elgato identify --host elgato-key-light.local

# Restart the device
elgato restart --host elgato-key-light.local

# Emit machine-readable JSON
elgato state --host elgato-key-light.local --json

# Scan the network for Elgato Lights (uses mDNS/Zeroconf)
elgato scan
```

## Usage

The client is an async context manager; every API call is a coroutine. A
quick status check and toggle looks like this:

```python
import asyncio

from elgato import Elgato, Info, State


async def main() -> None:
    """Show example on controlling your Elgato Light device."""
    async with Elgato("elgato-key-light.local") as elgato:
        info: Info = await elgato.info()
        print(info)

        state: State = await elgato.state()
        print(state)

        # Toggle the light
        await elgato.light(on=(not state.on))


if __name__ == "__main__":
    asyncio.run(main())
```

### Light control

The `light()` method supports both color-temperature mode and full-color
(hue/saturation) mode. Parameters can be combined in a single call:

```python
async with Elgato("elgato-key-light.local") as elgato:
    # Set brightness and color temperature (in mired, 143-344)
    await elgato.light(on=True, brightness=80, temperature=200)

    # Set brightness with hue/saturation (Light Strip only)
    await elgato.light(on=True, brightness=50, hue=240.0, saturation=100.0)
```

### Battery-powered devices

The Key Light Mini runs on battery. Battery-specific methods are guarded
and raise `ElgatoNoBatteryError` when called on a device without one:

```python
from elgato import Elgato, BatteryInfo

async with Elgato("elgato-key-light-mini.local") as elgato:
    battery: BatteryInfo = await elgato.battery()
    print(f"Level: {battery.level}%, Power: {battery.charge_power}W")

    # Toggle studio mode (bypass the battery)
    await elgato.battery_bypass(on=True)

    # Configure energy saving
    await elgato.energy_saving(
        on=True,
        brightness=10,
        minimum_battery_level=15,
        adjust_brightness=True,
        disable_wifi=False,
    )
```

### Device management

```python
async with Elgato("elgato-key-light.local") as elgato:
    # Make the light blink to identify it
    await elgato.identify()

    # Change the display name
    await elgato.display_name("Studio Left")

    # Reboot the device
    await elgato.restart()
```

### Power-on behavior

Configure what the light does when it powers on:

```python
from elgato import Elgato, PowerOnBehavior

async with Elgato("elgato-key-light.local") as elgato:
    await elgato.power_on_behavior(
        behavior=PowerOnBehavior.USE_DEFAULTS,
        brightness=50,
        temperature=230,
    )
```

### Connection options

All constructor arguments are keyword-only (except `host`):

```python
Elgato(
    "elgato-key-light.local",
    port=9123,             # default Elgato API port
    request_timeout=8,     # per-request timeout in seconds
)
```

You may also pass your own `aiohttp.ClientSession` via `session=...` to
share a connection pool across multiple clients.

### Error handling

All exceptions inherit from `ElgatoError`, so a single `except` covers
every failure mode:

```python
from elgato import Elgato, ElgatoConnectionError, ElgatoError, ElgatoNoBatteryError

try:
    async with Elgato("elgato-key-light.local") as elgato:
        await elgato.light(on=True)
except ElgatoConnectionError:
    # Timeout or network issue
    ...
except ElgatoNoBatteryError:
    # Battery method called on a device without one
    ...
except ElgatoError:
    # Any other Elgato-specific error (invalid parameters, HTTP errors, etc.)
    ...
```

The library does **not** retry failed requests. If you need retry logic,
wrap calls with a library like [tenacity](https://github.com/jd/tenacity):

```python
from tenacity import retry, stop_after_attempt, wait_exponential

from elgato import Elgato, ElgatoConnectionError


@retry(
    retry=retry_if_exception_type(ElgatoConnectionError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
)
async def toggle_light(elgato: Elgato) -> None:
    """Toggle the light with retries."""
    state = await elgato.state()
    await elgato.light(on=(not state.on))
```

## Changelog & Releases

This repository keeps a change log using [GitHub's releases][releases]
functionality. The format of the log is based on
[Keep a Changelog][keepchangelog].

Releases are based on [Semantic Versioning][semver], and use the format
of `MAJOR.MINOR.PATCH`. In a nutshell, the version will be incremented
based on the following:

- `MAJOR`: Incompatible or major changes.
- `MINOR`: Backwards-compatible new features and enhancements.
- `PATCH`: Backwards-compatible bugfixes and package updates.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Setting up development environment

The easiest way to start, is by opening a CodeSpace here on GitHub, or by using
the [Dev Container][devcontainer] feature of Visual Studio Code.

[![Open in Dev Containers][devcontainer-shield]][devcontainer]

This Python project is fully managed using the [Poetry][poetry] dependency
manager. But also relies on the use of NodeJS for certain checks during
development.

You need at least:

- Python 3.11+
- [Poetry][poetry-install]
- NodeJS 24+ (including NPM)

To install all packages, including all development requirements:

```bash
npm install
poetry install
```

As this repository uses the [prek][prek] framework, all changes
are linted and tested with each commit. You can run all checks and tests
manually, using the following command:

```bash
poetry run prek run --all-files
```

To run just the Python tests:

```bash
poetry run pytest
```

## Authors & contributors

The original setup of this repository is by [Franck Nijhof][frenck].

For a full list of all authors and contributors,
check [the contributor's page][contributors].

## License

MIT License

Copyright (c) 2019-2026 Franck Nijhof

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[build-shield]: https://github.com/frenck/python-elgato/actions/workflows/tests.yaml/badge.svg
[build]: https://github.com/frenck/python-elgato/actions/workflows/tests.yaml
[codecov-shield]: https://codecov.io/gh/frenck/python-elgato/branch/main/graph/badge.svg
[codecov]: https://codecov.io/gh/frenck/python-elgato
[contributors]: https://github.com/frenck/python-elgato/graphs/contributors
[devcontainer-shield]: https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode
[devcontainer]: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/frenck/python-elgato
[frenck]: https://github.com/frenck
[github-sponsors-shield]: https://frenck.dev/wp-content/uploads/2019/12/github_sponsor.png
[github-sponsors]: https://github.com/sponsors/frenck
[keepchangelog]: http://keepachangelog.com/en/1.0.0/
[license-shield]: https://img.shields.io/github/license/frenck/python-elgato.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg
[patreon-shield]: https://frenck.dev/wp-content/uploads/2019/12/patreon.png
[patreon]: https://www.patreon.com/frenck
[poetry-install]: https://python-poetry.org/docs/#installation
[poetry]: https://python-poetry.org
[prek]: https://github.com/frenck/prek
[project-stage-shield]: https://img.shields.io/badge/project%20stage-production%20ready-brightgreen.svg
[pypi]: https://pypi.org/project/elgato/
[python-versions-shield]: https://img.shields.io/pypi/pyversions/elgato
[releases-shield]: https://img.shields.io/github/release/frenck/python-elgato.svg
[releases]: https://github.com/frenck/python-elgato/releases
[scorecard]: https://scorecard.dev/viewer/?uri=github.com/frenck/python-elgato
[scorecard-shield]: https://api.scorecard.dev/projects/github.com/frenck/python-elgato/badge
[semver]: http://semver.org/spec/v2.0.0.html
