from re import L
from typing import List, Optional

from npe2 import PluginManager
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import QHBoxLayout, QLineEdit, QWidget
from superqt import QSearchableComboBox


def matches_prefix(
    word: str, word_to_match_against: str, ignore_case: bool = True
):
    if not word_to_match_against or len(word_to_match_against) < len(word):
        return None

    if ignore_case:
        matches = word_to_match_against.lower().startswith(word.lower())
    else:
        matches = word_to_match_against.startswith(word)

    if matches:
        [{'start': 0, 'end': len(word)}] if word != '' else []
    return None


def join(head: dict, tail: List[dict]) -> List[dict]:
    if not tail:
        tail = [head]
    elif head['end'] == tail[0]['start']:
        tail[0]['start'] = head['start']
    else:
        tail.insert(0, head)
    return tail


def _matches_words(
    word: str, target: str, i: int, j: int, contiguous: bool = False
):
    if len(word) == i:
        return []
    if len(target) == j:
        return None
    if word[i] != target[j]:
        return None
    result = _matches_words(word, target, i + 1, j + 1)
    next_word_idx = j + 1
    if not contiguous:
        while not result and (
            next_word_idx := next_word(target, next_word_idx)
        ) < len(target):
            result = _matches_words(
                word, target, i + 1, next_word_idx, contiguous
            )
            next_word_idx += 1
    if result:
        return join({'start': j, 'end': j + 1}, result)


def matches_words(word: str, word_to_match_against: str):
    word = word.lower()
    word_to_match_against = word_to_match_against.lower()

    i = 0
    while i < len(word_to_match_against):
        if result := _matches_words(word, word_to_match_against, 0, i):
            return result
        i = next_word(word_to_match_against, i + 1)
    return None


SEPS = '()[]{}<>`\'"-/;:,.?!\n\t '


def next_word(word: str, start: str) -> int:
    for i in range(start, len(word)):
        if word[i] in SEPS or (i > 0 and word[i - 1] in SEPS):
            return i
    return len(word)


class QCommandPallete(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        flags = Qt.WindowType.Sheet
        super().__init__(parent, flags)
        self.setLayout(QHBoxLayout())
        self._input = QSearchableComboBox()
        self.layout().addWidget(self._input)

        pm = PluginManager.instance()
        pm.discover()
        for cmd, plugin_name in pm._contrib._commands.values():
            # if cmd.icon is not None: ...
            name = pm.get_manifest(plugin_name).display_name
            self._input.addItem(f'{name}: {cmd.title}', cmd.id)
        self._pm = pm

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if a0.key() == Qt.Key.Key_Return:
            from napari.plugins import _npe2

            cmd_id = self._input.currentData()
            _npe2._exec_command(cmd_id)

            self.close()
            return

        return super().keyPressEvent(a0)


if __name__ == '__main__':
    import napari

    viewer = napari.Viewer()

    @viewer.bind_key('Shift-Control-I')
    def _onkey(_viewer):
        wdg = QCommandPallete(_viewer.window._qt_window)
        wdg.show()

    napari.run()
