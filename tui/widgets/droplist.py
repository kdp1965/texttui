from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from asyncio import Event
from rich.align import Align
from rich.console import Console, ConsoleOptions, RenderResult, RenderableType
from rich.style import StyleType
from rich.table import Table
from rich.text import TextType
import rich.repr
from textual.widgets._button import Button, ButtonPressed

from textual import events
from textual.message import Message
from textual.reactive import Reactive
from textual.widget import Widget
from textual.case import camel_to_snake

class ListCollapse(Message, bubble=True):
    pass

class RowHeightUpdate(Message):
    def __init__(self, sender: MessageTarget, row: int, new_height: int):
        super().__init__(sender)
        self.row = row
        self.new_height = new_height


class ListRenderable:
    def __init__(
        self,
        items: list,
        selected: str,
        expanded: bool,
        max_height: int,
        listindex: int,
        top: int,
        style: StyleType = ""
    ) -> None:
        self.items = items
        self.style = style
        self.max_height = max_height
        self.expanded = expanded
        self.selected = selected
        self.listindex = listindex
        self.top = top

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = options.max_width
        max_height = self.max_height or options.height

        if not self.expanded:
            drop_table = Table.grid(padding=(0, 1), expand=True)
            drop_table.style = self.style
            drop_table.add_column("label",  ratio=1, no_wrap=True, overflow="crop")
            drop_table.add_column("control", ratio=0, width=2)
            drop_table.box=None
            drop_table.show_lines=False
            drop_table.show_edge=False
            drop_table.show_header=False
            
            drop_table.add_row(f'[on grey39]{self.selected:{width-2}s}[on black]⬇️')
            drop: RenderResult
            drop = drop_table
            yield drop

        else:
            drop_table = Table.grid(padding=(0, 1), expand=True)
            drop_table.style = self.style
            drop_table.add_column("label",  ratio=1, no_wrap=True, overflow="crop")
            drop_table.add_column("control", ratio=0, width=2)
            drop_table.box=None
            drop_table.show_lines=False
            drop_table.show_edge=False
            drop_table.show_header=False
            
            drop_table.add_row(f'[on grey39]{self.selected:{width-2}s}[on black]⬇️')
            rows = 1
            item = 0
            items = len(self.items)
            for s in self.items:
                if item < self.top:
                    item += 1
                    continue
                if (rows + 1 == max_height and item+2 < items) or (rows == 1 and self.top != 0):
                    if self.listindex == rows:
                        drop_table.add_row(f'[white on blue]{"...":{width-2}s}')
                    else:
                        drop_table.add_row(f'[black on white]{"...":{width-2}s}')
                elif self.listindex == 0 and s == self.selected:
                    drop_table.add_row(f'[white on blue]{s:{width-2}s}')
                elif self.listindex > 0 and self.listindex == rows:
                    drop_table.add_row(f'[white on blue]{s:{width-2}s}')
                else:
                    drop_table.add_row(f'[black on white]{s:{width-2}s}')
                rows += 1
                item += 1
                if rows >= max_height:
                    break
              
            drop: RenderResult
            drop = drop_table
            yield drop

class Droplist(Button):
    def __init__(
        self,
        label: str,
        items: str,
        max_height: int = 8,
        style: StyleType = "white on black",
        name: str | None = None,
        *,
        select: str = '',
    ):
        super().__init__(label=label, style=style, name=name)
        self.name = name or label
        self.expanded = False
        self.items = items.split(',')
        self.selected = select
        self.max_height = max_height
        self.top = 0

    expanded: Reactive[bool] = Reactive(False)
    listindex: Reactive[int] = Reactive(0)
    top: Reactive[int] = Reactive(0)
    selected: Reactive[str] = Reactive("", layout=True)
    label: Reactive[str] = Reactive("")

    def __rich_repr__(self) -> Result:
      yield self.label

    def render(self) -> RenderableType:
        return ListRenderable(
                    self.items,
                    self.selected,
                    self.expanded,
                    self.max_height,
                    self.listindex,
                    self.top,
                    self.style
                )

    def count(self) -> int:
        return len(self.items)

    async def on_click(self, event: events.Click) -> None:
        if not self.expanded:
            self.expanded = True
            event.prevent_default().stop()
            await self.emit(RowHeightUpdate(
                    self, self.ctrl_panel_row, min(len(self.items)+1,self.max_height))
                  )
        else:
            # Test if a new item was selected
            if self.listindex > 0:
                self.selected = self.items[self.listindex+self.top-1]
            self.listindex = 0
            self.expanded = False
            event.prevent_default().stop()
            await self.emit(RowHeightUpdate(self, self.ctrl_panel_row, 1))
            await self.emit(ButtonPressed(self))

    async def on_leave(self, event: events.Leave) -> None:
        if self.expanded:
            self.expanded = False
            event.prevent_default().stop()
            await self.emit(RowHeightUpdate(self, self.ctrl_panel_row, 1))

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.expanded:
            self.listindex = event.y
        else:
            self.listindex = 0

    async def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.expanded:
            if self.top < len(self.items) - self.max_height:
                self.top += 1

    async def on_mouse_scroll_down(self, event: events.MouseScrollUp) -> None:
        if self.expanded:
            if self.top > 0:
                self.top -= 1


