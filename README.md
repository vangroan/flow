
# Flow

Flow is an experimental node-based scripting system built on Python.

It is aimed at automating common tasks for digital artists.

## Packages

- `flow_core`: The core graph model and execution engine.
- `flow_base`: Library of base nodes that are the foundational building blocks.
- `flow_serde`: Serialisation and deserialisation of the graph model.
- `flow_app`: Qt graphical user interface application.

## Ubuntu

```sh
sudo apt update
sudo apt install -y libxcb-cursor0
```

To debug Qt6's window manager plugin.

```sh
QT_DEBUG_PLUGINS=1 python flow_app/app.py
```

# License

This code based is licenced under the MIT open source licence. See [LICENSE](./LICENSE.md)
