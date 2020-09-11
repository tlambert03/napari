from unittest import mock

from IPython.terminal.interactiveshell import TerminalInteractiveShell

from napari._qt.widgets.qt_console import QtConsole


def test_console(qtbot):
    """Test creating the console."""
    console = QtConsole()
    qtbot.addWidget(console)
    assert console.kernel_client is not None


def test_console_user_variables(qtbot):
    """Test creating the console with user variables."""
    console = QtConsole({'var': 3})
    qtbot.addWidget(console)
    assert console.kernel_client is not None
    assert 'var' in console.shell.user_ns
    assert console.shell.user_ns['var'] == 3


def test_multiple_consoles(qtbot):
    """Test creating multiple consoles."""
    console_a = QtConsole({'var_a': 3})
    qtbot.addWidget(console_a)
    console_b = QtConsole({'var_b': 4})
    qtbot.addWidget(console_b)

    assert console_a.kernel_client is not None
    assert console_b.kernel_client is not None
    assert 'var_a' in console_a.shell.user_ns
    assert 'var_b' in console_a.shell.user_ns


def test_ipython_console(qtbot):
    """Test mock-creating a console from within ipython."""

    def mock_get_ipython():
        return TerminalInteractiveShell()

    with mock.patch(
        'napari._qt.widgets.qt_console.get_ipython',
        side_effect=mock_get_ipython,
    ):
        console = QtConsole()
        qtbot.addWidget(console)
        assert console.kernel_client is None
