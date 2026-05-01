"""通用撤销/重做管理器"""

from collections import deque


class UndoManager:
    """操作栈管理器，支持撤销/重做

    每个操作是一个 dict: {"desc": str, "undo": callable, "redo": callable}
    """

    def __init__(self, max_size: int = 100):
        self._undo_stack = deque(maxlen=max_size)
        self._redo_stack = deque(maxlen=max_size)

    def push(self, desc: str, undo_fn, redo_fn):
        """记录一个操作"""
        self._undo_stack.append({"desc": desc, "undo": undo_fn, "redo": redo_fn})
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self) -> str:
        """撤销最近一个操作，返回操作描述"""
        if not self._undo_stack:
            return ""
        action = self._undo_stack.pop()
        action["undo"]()
        self._redo_stack.append(action)
        return action["desc"]

    def redo(self) -> str:
        """重做最近一个操作，返回操作描述"""
        if not self._redo_stack:
            return ""
        action = self._redo_stack.pop()
        action["redo"]()
        self._undo_stack.append(action)
        return action["desc"]

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()

    def undo_desc(self) -> str:
        """获取可撤销操作的描述"""
        if self._undo_stack:
            return f"撤销: {self._undo_stack[-1]['desc']}"
        return "撤销"

    def redo_desc(self) -> str:
        """获取可重做操作的描述"""
        if self._redo_stack:
            return f"重做: {self._redo_stack[-1]['desc']}"
        return "重做"
