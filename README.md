> Freat is an experiment that I started to learn more about game hacking and reverse engineering (so it uses Frida) and about game development (so it uses Godot).
> If you think these two concepts don't belong together, well, we definitely agree on something.

## Introduction

Freat is a tool that allows you to attach to arbitrary programs running on your machine – or your mobile phone, or any other platform that exposes a frida server – and mess with it.

In its current state, it supports CheatEngine-like features like memory scanning, freezing and writing.

## Architecture

Freat is made of the following components:

- Agent: developed in frida, it is injected in the target process to implement the dynamic instrumentation (e.g. memory scanning). The languages used are TypeScript, for the less intensive operations, and C, for heavy operations such as wide address space scanning.
- Hub: a Python program that manages agent creation and interaction. It exposes a WebSocket RPC API to implement the commands.
- GUI: the tool UI implemented in Godot. It connects to the Hub to send commands and receive updates.

## Development

In order to hack with this project, you need to make sure you have:

- The Godot editor (version 4.4+) installed.
- The `uv` Python package manager.
- Node.js and `npm`.

Freat task running is managed with the simple `run.py` script. For development mode, you should run:

`python run.py dev`
