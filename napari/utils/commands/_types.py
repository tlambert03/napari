from __future__ import annotations

from typing import Any, Callable, List, NewType, Optional, Tuple, Union

from pydantic import BaseModel

from napari.utils import context
from napari.utils.translations import TranslationString

from ._menus import MenuId

CommandId = NewType("CommandId", str)
KeyCode = NewType("KeyCode", str)


class Keybindings(BaseModel):
    primary: Optional[KeyCode] = None
    secondary: Optional[List[KeyCode]] = None
    win: Optional[Tuple[KeyCode, List[KeyCode]]] = None
    linux: Optional[Tuple[KeyCode, List[KeyCode]]] = None
    mac: Optional[Tuple[KeyCode, List[KeyCode]]] = None


class KeybindingAssociation(Keybindings):
    weight: int = 0
    args: Any = None  # ??
    when: Optional[context.Expr] = None


class KeybindingRule(KeybindingAssociation):
    id: CommandId


class _MenuItemBase(BaseModel):
    when: Optional[context.Expr] = None
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


class IKeybindingItem(BaseModel):
    keybinding: KeyCode
    command: str
    weight1: int
    isBuiltinExtension: bool
    args: Optional[Any] = None
    when: Optional[context.Expr] = None
    extensionId: Optional[str] = None
