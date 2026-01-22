> Freat is an experiment that I started to learn more about game hacking and reverse engineering (so it uses Frida) and about game development (so it uses Godot).
> If you think these two concepts don't belong together, well, we definitely agree on something.

## Introduction

Freat is a tool that allows you to attach to arbitrary programs running on your machine – or your mobile phone, or any other platform that exposes a frida server – and mess with it.

In its current state, it supports CheatEngine-like features like memory scanning, freezing and writing.

## Features

- **Memory scanning**: scan the entire address space for values, then refine results with subsequent scans
- **Scan types**: exact match, greater than, less than
- **Data types**: U8, U16, U32, U64, float, double
- **Watch list**: monitor addresses in real-time
- **Freeze list**: lock addresses to specific values
- **Write values**: directly modify memory

### Target providers

- **Local**: attach to processes on your machine
- **Remote**: connect to a frida-server over the network
- **Wine** (experimental): attach to Windows programs running under Wine

## Architecture

Freat is made of the following components:

- **Agent**: developed in frida, it is injected in the target process to implement the dynamic instrumentation (e.g. memory scanning). The languages used are TypeScript, for the less intensive operations, and C, for heavy operations such as wide address space scanning.
- **Hub**: a Python program that manages agent creation and interaction. It exposes a WebSocket RPC API to implement the commands.
- **GUI**: the tool UI implemented in Godot. It connects to the Hub to send commands and receive updates.

## Configuration

Freat looks for a config file at `~/.config/freat/config.toml` (Linux). Examples:

```toml
# Local (default)
[target]
provider = "local"
```

```toml
# Remote
[target]
provider = "remote"

[target.options]
host = "192.168.1.100"
port = 27042
```

```toml
# Wine
[target]
provider = "wine"

[target.options]
wine_prefix = "/home/user/.wine"
```

## Installation

If you just want to use Freat (not develop it), here's what you need to do:

1. Install the server:
   ```bash
   pip install freat_server-0.1.0-py3-none-any.whl
   ```

2. Start the server:
   ```bash
   freat-server
   ```

3. Launch the GUI by opening the Freat app from the DMG.

The server and GUI need to run simultaneously – the GUI connects to the server on `localhost:8765`. Keep the server running in a terminal while you use the app.

## Development

In order to hack with this project, you need to make sure you have:

- The Godot editor (version 4.4+) installed.
- The `uv` Python package manager.
- Node.js and `npm`.

Freat task running is managed with the simple `run.py` script. For development mode, you should run:

`python run.py dev`
