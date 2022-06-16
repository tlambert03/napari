from __future__ import annotations

from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    NewType,
    Sequence,
    Set,
    Tuple,
    Union,
)

from psygnal import Signal
from napari.utils import context
from napari.utils.translations import TranslationString
from pydantic import BaseModel
import os
import sys

CommandId = NewType("CommandId", str)
KeyCode = NewType("CommandId", str)
WINDOWS = os.name == 'nt'
MACOS = sys.platform == 'darwin'
LINUX = sys.platform.startswith("linux")


class _Keybindings(BaseModel):
    primary: Optional[KeyCode] = None
    secondary: Optional[List[KeyCode]] = None
    win: Optional[Tuple[KeyCode, List[KeyCode]]] = None
    linux: Optional[Tuple[KeyCode, List[KeyCode]]] = None
    mac: Optional[Tuple[KeyCode, List[KeyCode]]] = None


class KeybindingAssociation(_Keybindings):
    weight: int = 0
    args: Any = None
    when: Optional[context.Expr] = None


class KeybindingRule(KeybindingAssociation):
    id: CommandId


class MenuId(Enum):
    ...


class _MenuItemBase(BaseModel):
    when: context.Expr = None
    group: str = "navigation"
    order: Optional[int] = None


class MenuItem(_MenuItemBase):
    command: ICommandAction

    class Config:
        extra = 'ignore'


class SubMenuItem(_MenuItemBase):
    ...


class MenuItemAssociation(_MenuItemBase):
    id: MenuId


class Icon(BaseModel):
    dark: Optional[str] = None
    light: Optional[str] = None


class ICommandAction(BaseModel):
    id: CommandId
    title: Union[TranslationString, str]
    short_title: Optional[Union[TranslationString, str]] = None
    category: Optional[Union[TranslationString, str]] = None
    tooltip: Optional[Union[TranslationString, str]] = None
    icon: Optional[Icon] = None
    source: Optional[str] = None
    precondition: Optional[context.Expr] = None
    toggled: Optional[context.Expr] = None


class Action(ICommandAction):
    run: Callable
    add_to_command_palette: bool = True
    menus: Optional[List[MenuItemAssociation]] = None
    keybindings: Optional[List[KeybindingAssociation]] = None
    description: Optional[str] = None


# Registries
class _Command(NamedTuple):
    id: str
    run: Callable
    description: Optional[str] = None


class CommandsRegistry:
    registered = Signal(str)
    _commands: Dict[CommandId, List[_Command]] = {}
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

        cmd = _Command(id, run=callback, description=description)
        commands.insert(0, cmd)

        def _dispose():
            commands.remove(cmd)
            if not commands:
                del self._commands[id]

        self.registered.emit(id)
        return _dispose


class KeyBindingPrimarySecondary(NamedTuple):
    primary: Optional[KeyCode]
    secondar: Optional[List[KeyCode]]


class IKeybindingItem(BaseModel):
    keybinding: KeyCode
    command: str
    weight1: int
    isBuiltinExtension: bool
    args: Optional[Any] = None
    when: Optional[context.Expr] = None
    extensionId: Optional[str] = None


class KeybindingsRegistry:
    _coreKeybindings: List[IKeybindingItem] = []
    __instance: Optional[KeybindingsRegistry] = None

    @classmethod
    def instance(cls) -> KeybindingsRegistry:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @staticmethod
    def _bind_to_current_platform(
        kb: _Keybindings,
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
        when: Optional[context.Expr],
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


class MenuRegistry:
    menu_changed = Signal(set)
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
            self.menu_changed.emit(changed_ids)

    def add_commands(self, *commands: ICommandAction):
        for command in commands:
            self._commands[command.id] = command


def register_action(action: Action):
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
