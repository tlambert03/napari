from __future__ import annotations

import os
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    overload,
)

from psygnal import Signal

from napari.utils.translations import TranslationString

from ._menus import MenuId
from ._types import Action, IKeybindingItem

if TYPE_CHECKING:
    from napari.utils import context

    from ._types import (
        CommandId,
        ICommandAction,
        Icon,
        KeybindingAssociation,
        KeybindingRule,
        Keybindings,
        KeyCode,
        MenuItem,
        MenuItemAssociation,
        SubMenuItem,
    )

WINDOWS = os.name == 'nt'
MACOS = sys.platform == 'darwin'
LINUX = sys.platform.startswith("linux")


class RegisteredCommand(NamedTuple):
    id: str
    run: Callable
    description: Optional[str] = None


class KeyBindingPrimarySecondary(NamedTuple):
    primary: Optional[KeyCode]
    secondar: Optional[List[KeyCode]]


class CommandsRegistry:
    registered = Signal(str)
    _commands: Dict[CommandId, List[RegisteredCommand]] = {}
    __instance: Optional[CommandsRegistry] = None

    @classmethod
    def instance(cls) -> CommandsRegistry:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def register_command(
        self,
        id: CommandId,
        callback: Callable,
        description: Optional[str] = None,
    ) -> Callable:
        commands = self._commands.setdefault(id, [])

        cmd = RegisteredCommand(id, run=callback, description=description)
        commands.insert(0, cmd)

        def _dispose():
            commands.remove(cmd)
            if not commands:
                del self._commands[id]

        self.registered.emit(id)
        return _dispose


class KeybindingsRegistry:
    registered = Signal()
    _coreKeybindings: List[IKeybindingItem] = []
    __instance: Optional[KeybindingsRegistry] = None

    @classmethod
    def instance(cls) -> KeybindingsRegistry:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @staticmethod
    def _bind_to_current_platform(
        kb: Keybindings,
    ) -> KeyBindingPrimarySecondary:
        if WINDOWS and kb.win:
            return KeyBindingPrimarySecondary(*kb.win)
        if MACOS and kb.mac:
            return KeyBindingPrimarySecondary(*kb.mac)
        if LINUX and kb.linux:
            return KeyBindingPrimarySecondary(*kb.linux)
        return KeyBindingPrimarySecondary(kb.primary, kb.secondary)

    def register_keybinding_rule(self, rule: KeybindingRule):
        actual_kb = self._bind_to_current_platform(rule)
        if kk := actual_kb.primary:
            self._register_default_keybinding(
                kk, rule.id, rule.args, rule.weight, rule.when
            )

    def _register_default_keybinding(
        self,
        keybinding: KeyCode,
        command_id: CommandId,
        args: Any,
        weight: int,
        when: Optional[context.Expr] = None,
    ):
        item = IKeybindingItem(
            keybinding=keybinding,
            command=command_id,
            args=args,
            weight1=weight,
            extensionId=None,
            isBuiltinExtension=False,
            when=when,
        )
        self._coreKeybindings.append(item)
        self.registered.emit()


class MenuRegistry:
    menus_changed = Signal(set)
    _menu_items: Dict[MenuId, List[Union[MenuItem, SubMenuItem]]] = {}
    _commands: Dict[CommandId, ICommandAction] = {}
    __instance: Optional[MenuRegistry] = None

    @classmethod
    def instance(cls) -> MenuRegistry:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def append_menu_items(
        self, items: Sequence[Tuple[MenuId, Union[MenuItem, SubMenuItem]]]
    ):
        if not items:
            return
        changed_ids: Set[MenuId] = set()

        for id, item in items:
            menu_list = self._menu_items.setdefault(id, [])
            menu_list.append(item)
            changed_ids.add(id)

        if changed_ids:
            self.menus_changed.emit(changed_ids)

    def add_commands(self, *commands: ICommandAction):
        for command in commands:
            self._commands[command.id] = command


@overload
def register_action(
    id_or_action: str,
    title: Union[TranslationString, str],
    short_title: Optional[Union[TranslationString, str]] = None,
    category: Optional[Union[TranslationString, str]] = None,
    tooltip: Optional[Union[TranslationString, str]] = None,
    icon: Optional[Icon] = None,
    source: Optional[str] = None,
    toggled: Optional[context.Expr] = None,
    run: Literal[None] = None,
    add_to_command_palette: bool = True,
    menus: Optional[List[MenuItemAssociation]] = None,
    keybindings: Optional[List[KeybindingAssociation]] = None,
    description: Optional[str] = None,
) -> Callable:
    ...


@overload
def register_action(
    id_or_action: str,
    title: Union[TranslationString, str],
    short_title: Optional[Union[TranslationString, str]] = None,
    category: Optional[Union[TranslationString, str]] = None,
    tooltip: Optional[Union[TranslationString, str]] = None,
    icon: Optional[Icon] = None,
    source: Optional[str] = None,
    precondition: Optional[context.Expr] = None,
    toggled: Optional[context.Expr] = None,
    run: Callable = ...,
    add_to_command_palette: bool = True,
    menus: Optional[List[MenuItemAssociation]] = None,
    keybindings: Optional[List[KeybindingAssociation]] = None,
    description: Optional[str] = None,
) -> None:
    ...


@overload
def register_action(id_or_action: Action) -> None:
    ...


def register_action(
    id_or_action: Union[str, Action],
    title: Union[TranslationString, str, None] = None,
    short_title: Optional[Union[TranslationString, str]] = None,
    category: Optional[Union[TranslationString, str]] = None,
    tooltip: Optional[Union[TranslationString, str]] = None,
    icon: Optional[Icon] = None,
    source: Optional[str] = None,
    precondition: Optional[context.Expr] = None,
    toggled: Optional[context.Expr] = None,
    run: Optional[Callable] = None,
    add_to_command_palette: bool = True,
    menus: Optional[List[MenuItemAssociation]] = None,
    keybindings: Optional[List[KeybindingAssociation]] = None,
    description: Optional[str] = None,
):
    if isinstance(id_or_action, Action):
        return _register_action(id_or_action)
    if isinstance(id_or_action, str):
        if title is None:
            raise ValueError("title is required")
        _kwargs = locals().copy()
        _kwargs['id'] = _kwargs.pop("id_or_action")
        return _register_action_str(**_kwargs)
    raise ValueError('id_or_action must be a string or an Action')


def _register_action_str(**_kwargs):
    if _kwargs.get('run') is None:

        def decorator(callable: Callable, **kwargs):
            _kwargs.update({**kwargs, 'run': callable})
            return _register_action(Action(**_kwargs))

        decorator.__doc__ = (
            f"Decorate function as callback for command {_kwargs['id']!r}"
        )
        return decorator
    return _register_action(Action(**_kwargs))


def _register_action(action: Action):
    # command
    CommandsRegistry.instance().register_command(
        action.id, action.run, action.description
    )

    # menu
    MenuRegistry.instance().append_menu_items(
        [
            (entry.id, MenuItem(command=action, **entry.dict()))
            for entry in action.menus or ()
        ]
    )
    if action.add_to_command_palette:
        MenuRegistry.instance().add_commands(action)

    # keybinding
    for keyb in action.keybindings or ():
        rule = KeybindingRule(id=action.id, **keyb.dict())
        KeybindingsRegistry.instance().register_keybinding_rule(rule)
