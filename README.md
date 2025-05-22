# mcp-ipython

A FastMCP backend that interfaces with an IPython kernel to execute Python commands and manage the kernel environment.

This package provides tools to interact with an IPython kernel, allowing for the execution of Python commands and management of the kernel's state through a FastMCP server.

## Installation

You can install `mcp-ipython` directly from its GitHub repository.

### Recommended (for CLI application): `pipx`

If you want to install `mcp-ipython-server` as a standalone command-line application, `pipx` is the recommended tool:

```bash
pipx install git+https://github.com/Kreijstal/mcp-ipython.git
```

### For library usage: `pip`

If you intend to use `mcp-ipython` as a library within your Python projects, you can install it using `pip`:

```bash
pip install git+https://github.com/Kreijstal/mcp-ipython.git
```