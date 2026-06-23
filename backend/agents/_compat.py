"""Compatibility shim for langchain-classic in this environment.

`langchain-classic` eagerly imports `langchain_text_splitters`, which in turn
imports `sentence_transformers` and therefore `torch`. The project pins
`torch==2.2.2` and `numpy==2.4.6`, which are incompatible (PyTorch < 2.4 does
not support NumPy 2.x). Since the agent does not use the sentence-transformer
text splitter, we stub that submodule before any langchain_classic import.

This shim should be imported before any `langchain_classic.*` import in the
agent or test modules.
"""

import sys
import types


# Only patch once.
if "langchain_text_splitters.sentence_transformers" not in sys.modules:
    _fake = types.ModuleType("langchain_text_splitters.sentence_transformers")

    class _DummySplitter:
        pass

    _fake.SentenceTransformersTokenTextSplitter = _DummySplitter
    sys.modules["langchain_text_splitters.sentence_transformers"] = _fake
