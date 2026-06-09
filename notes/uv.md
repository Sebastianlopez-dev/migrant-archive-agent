# Why uv

**Decision**: use `uv` for Python environment + package management in this project.

## Options evaluated

| Tool | Environment | Package install | Speed | Single tool? |
|------|-------------|-----------------|-------|-------------|
| `venv` + `pip` | ✅ | ✅ | Slow | ❌ Two tools |
| `conda` | ✅ | ✅ (conda-forge) | Medium | ✅ |
| `poetry` | ✅ | ✅ | Medium | ✅ |
| **`uv`** | ✅ | ✅ | **10-100x faster** | ✅ |

## Why not the others

- **venv + pip**: works, but `pip` is slow on repeated installs. No lockfile.
- **conda**: overkill. Our stack (yt-dlp, faster-whisper, openai, fastapi) is pure Python. Conda shines with C/CUDA-heavy stacks like PyTorch.
- **poetry**: great for libraries with strict dependency resolution, but `uv` is faster and simpler for application projects.

## What uv gives us

| Feature | Benefit for this project |
|---------|-------------------------|
| `uv venv --python 3.12` | One command to create env with pinned Python |
| `uv pip install -r requirements.txt` | 10x faster resolves, no waiting |
| `uv python install 3.12` | Downloads any Python version without system package manager |
| Single binary | No pip + venv + virtualenvwrapper confusion |

## When to reconsider

If this project ever needs `PyTorch + CUDA` or `cuDNN`, `conda` becomes the pragmatic choice. Until then, `uv` is the right tool.

## Reference

- [uv documentation](https://docs.astral.sh/uv/)
- Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
