## Introduction

Freat is a tool that allows you to attach to arbitrary programs (probably, games) running on your machine – or your mobile phone, or any other platform that can expose a frida server – and mess with it.

In its current state, it supports CheatEngine-like features like memory scanning, freezing and writing.

If you're interested, please read more about Freat's development and design in the [linked blogpost](https://suidpit.sh/freat-intro).

> DISCLAIMER
>
> Freat was developed just for fun and learning purposes.
> I do not condone the use of this tool to cheat in online multiplayer games.
> Reverse engineering and hacking to learn and experiment is fun.
> Ruining the experience of other fellow gamers is lame.

## Features

- **Memory scanning**: scan the entire address space for values, then refine results with subsequent scans
- **Scan types**: exact match, greater than, less than, relative (increased/decreased), unknown
- **Data types**: U8, U16, U32, U64, float, double
- **Watch list**: monitor addresses in real-time
- **Freeze list**: lock addresses to specific values, or scale the game-applied values
- **Write values**: directly modify memory
- **Watchpoints**: monitor addresses for changes and get a stacktrace upon read/write

### Target providers

- **Local**: attach to processes on your machine
- **Remote**: connect to a frida-server over the network
- **Wine**: attach to Windows programs running under Wine
- **Proton**: an extension of the Wine provider, allowing to attach to games running under Steam's Proton layer

## Architecture

Freat is made of the following components:

- **Agent**: developed in frida, it is injected in the target process to implement the dynamic instrumentation (e.g. memory scanning). The languages used are TypeScript, for management and RPC interaction, and native C modules, for heavy operations such as wide address space scanning.
- **Hub**: a Python program that manages agent creation and interaction. It exposes a WebSocket RPC API to implement the commands sent by the UI.
- **GUI**: the tool UI implemented in Godot. It connects to the Hub to send commands and receive updates.

## Configuration

Right now, most of the values are hardcoded in the source code. The only configurable value is the target provider, which can be set using the `FREAT_PROVIDER` environment variable. Currently, the following providers are supported:

- **Local**: attach to processes on your machine (`FREAT_PROVIDER=local`)
- **Remote**: connect to a frida-server over the network (`FREAT_PROVIDER=remote://<host>:<port>`)
- **Wine**: attach to Windows programs running under Wine (`FREAT_PROVIDER=wine:///<prefix_path>`)
- **Proton**: an extension of the Wine provider, allowing to attach to games running under Steam's Proton layer (`FREAT_PROVIDER=proton`)

## Installation

### Prerequisites

- Python 3.12+

### Server

1. Install the server with pip, or use any other method you prefer (e.g. uv, pipx):

```bash
git clone https://github.com/suidpit/freat
cd freat/server-python
pip install .
```

2. Run the server (remember to set `FREAT_PROVIDER` to attach on anything other than local processes):

```bash
FREAT_PROVIDER=<provider> freat-server
```

### GUI

Download the latest GUI release for your platform from the [release page](https://github.com/suidpit/freat/releases) and launch it.

The server and GUI need to run simultaneously – the GUI connects to the server on `localhost:8765`. Keep the server running in a terminal while you use the app.

## Development

In order to hack with this project, you need to make sure you have:

- The Godot editor (version 4.4+) installed.
- The `uv` Python package manager.
- Node.js and `npm`.

Freat task running is managed with the simple `run.py` script. For development mode, you should run:

`python run.py dev`
