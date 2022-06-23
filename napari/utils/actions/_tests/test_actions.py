from typing import Callable, Optional
from unittest.mock import Mock, patch

import pytest

from napari.utils.actions import register_action
from napari.utils.actions._menus import MenuId
from napari.utils.actions._registries import (
    CommandsRegistry,
    KeybindingsRegistry,
    MenuRegistry,
)

KWARGS = [
    {},
    dict(menus=[{'id': MenuId.LAYERS_CONTEXT}]),
    dict(keybindings=[{'primary': 'ctrl+a'}]),
]


@pytest.fixture
def cmd_reg():
    reg = CommandsRegistry()
    reg.registered_emit = Mock()  # type: ignore
    reg.registered.connect(reg.registered_emit)
    with patch.object(CommandsRegistry, 'instance', return_value=reg):
        yield reg
    reg._commands.clear()


@pytest.fixture
def key_reg():
    reg = KeybindingsRegistry()
    reg.registered_emit = Mock()  # type: ignore
    reg.registered.connect(reg.registered_emit)
    with patch.object(KeybindingsRegistry, 'instance', return_value=reg):
        yield reg
    reg._coreKeybindings.clear()


@pytest.fixture
def menu_reg():
    reg = MenuRegistry()
    reg.menus_changed_emit = Mock()  # type: ignore
    reg.menus_changed.connect(reg.menus_changed_emit)
    with patch.object(MenuRegistry, 'instance', return_value=reg):
        yield reg
    reg._menu_items.clear()


@pytest.mark.parametrize('kwargs', KWARGS)
@pytest.mark.parametrize('deco', [True, False])
def test_register_action_decorator(kwargs, cmd_reg, key_reg, menu_reg, deco):
    assert not (list(menu_reg) or list(key_reg) or list(cmd_reg))
    dispose: Optional[Callable] = None
    cmd_id = 'cmd.id'

    if deco:

        @register_action(cmd_id, 'Test title', **kwargs)
        def f1():
            return 1

    else:
        dispose = register_action(
            cmd_id, 'Test title', run=lambda: 1, **kwargs
        )

    assert 'cmd.id' in cmd_reg
    assert list(cmd_reg)
    cmd_reg.registered_emit.assert_called_once_with(cmd_id)

    if menus := kwargs.get('menus'):
        for entry in menus:
            assert entry['id'] in menu_reg
            menu_reg.menus_changed_emit.assert_called_with({entry['id']})
    else:
        assert not list(menu_reg)

    if keybindings := kwargs.get('keybindings'):
        for entry in keybindings:
            assert any(i.keybinding == entry['primary'] for i in key_reg)
            key_reg.registered_emit.assert_called()
    else:
        assert not list(key_reg)

    if dispose:
        dispose()
        assert not list(cmd_reg)


def test_instances():
    assert isinstance(MenuRegistry().instance(), MenuRegistry)
    assert isinstance(
        KeybindingsRegistry().instance(),
        KeybindingsRegistry,
    )
    assert isinstance(CommandsRegistry().instance(), CommandsRegistry)
