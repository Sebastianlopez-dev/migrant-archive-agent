# Why uv

**Decision**: use `uv` for Python environment + package management in this project.

## What we considered

The default Python workflow uses **two tools**: `venv` to create environments and `pip` to install packages. It works, but `pip` is painfully slow on repeated installs and there's no lockfile to freeze exact versions.

**Conda** handles both environment and packages in one tool, and it's great for stacks with heavy C/CUDA dependencies like PyTorch. But our stack is pure Python — `yt-dlp`, `faster-whisper`, `openai`, `fastapi` — so Conda would be carrying unnecessary weight.

**Poetry** is the go-to for libraries that need strict dependency resolution and lockfiles. It's excellent, but for an application project like this one, `uv` does the same thing faster and with less ceremony.

## Why uv won

`uv` is **a single binary** that replaces `venv`, `pip`, and `pip-tools` all at once. It resolves and installs packages 10-100x faster than `pip`. One command to install any Python version (`uv python install 3.12`), one command to create an environment (`uv venv --python 3.12`), and one command to install dependencies (`uv pip install -r requirements.txt`). No virtualenvwrapper, no pyenv, no confusion.

## When to revisit

If this project ever needs `PyTorch + CUDA` or `cuDNN`, `conda` becomes the pragmatic choice. Until then, `uv` is the right tool.

## Reference

- [uv documentation](https://docs.astral.sh/uv/)
- Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
