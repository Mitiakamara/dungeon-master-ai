"""
pytest bootstrap for backend/tests (instrucción 239).

- puts backend/ on sys.path so `agents.*` resolves from any cwd
- stubs `langchain_core.messages` — narrator/interpreter import it lazily
  inside their methods, so message containers with `.content` are enough.
  Zero network, zero LLM, zero DB, no venv needed.

Run (from backend/):  PYTHONUTF8=1 python3.14 -m pytest tests/ -q
"""
import os
import sys
import types

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


class _Msg:
    def __init__(self, content=""):
        self.content = content

    def __repr__(self):
        return f"{type(self).__name__}({self.content[:50]!r})"


class SystemMessage(_Msg):
    pass


class HumanMessage(_Msg):
    pass


class AIMessage(_Msg):
    pass


_lc = types.ModuleType("langchain_core")
_msgs = types.ModuleType("langchain_core.messages")
_msgs.SystemMessage, _msgs.HumanMessage, _msgs.AIMessage = SystemMessage, HumanMessage, AIMessage
_lc.messages = _msgs
sys.modules.setdefault("langchain_core", _lc)
sys.modules.setdefault("langchain_core.messages", _msgs)
