from __future__ import annotations

from rich.align import Align
from rich.console import Console, ConsoleOptions, RenderResult, RenderableType
from rich.style import StyleType
from rich.table import Table
from rich.text import TextType
from textual.widgets._button import Button, ButtonPressed

from textual import events
from textual.message import Message
from textual.reactive import Reactive
from textual.widget import Widget


class Checkbutton(Button):
    def __init__(
        self,
        label: str,
        style: StyleType = "",
        hover_style: StyleType = "white on grey39",
        name: str | None = None,
        *,
        checked: bool = False,
        checktype: str = 'large',
        indent: int = 0,
        top_margin: int = 0,
    ):
        super().__init__(label=label, style=style, name=name)
        self.checked = checked
        self.name = name or label
        self.checktype = checktype.lower() or "large"
        self.indent = indent
        self.top_margin = top_margin
        self.hover_style = hover_style
        self.style = style

    mouse_over: Reactive[bool] = Reactive(False)
    checked: Reactive[bool] = Reactive(False, layout=True)
    label: Reactive[str] = Reactive("")
    checktype: Reactive[str] = Reactive("")

    def __rich_repr__(self) -> Result:
      yield self.label

    def is_selected(self) -> bool:
      return self.checked

    def render(self) -> RenderableType:
        width = 2
        if self.checktype == 'large':
            boxes = [ "🔳", "✅" ]
        elif self.checktype == 'medium':
            boxes = ["□", "■"] 
            width = 1
        elif self.checktype == 'small':
            boxes = ["▫", "▪" ]
            width = 1
        elif self.checktype == 'cross':
            boxes = [ "🔳", "❎" ]
        elif self.checktype == 'ascii':
            boxes = [ "[ ]", "[X]" ]
            width = 3

        checkbox_table = Table.grid(padding=(0, 1), expand=True)
        checkbox_table.style = self.style
        if self.indent > 0:
            checkbox_table.add_column(ratio=0, width=min(0,self.indent-2))
        checkbox_table.add_column(ratio=0, width=width)
        checkbox_table.add_column("label",  ratio=1, no_wrap=True, overflow="crop")

        for i in range(self.top_margin):
            checkbox_table.add_row('')
        
        if self.mouse_over:
            style = "" if self.hover_style == "" else f'[{self.hover_style}]'
        else:
            style = "" if self.style == "" else f'[{self.style}]'
        label = f'{style}{self.label}'
        if self.indent > 0:
            checkbox_table.add_row('', boxes[1] if self.checked else boxes[0], label)
        else:
            checkbox_table.add_row(boxes[1] if self.checked else boxes[0], label)
        checkbox: RenderableType
        checkbox = checkbox_table
        return checkbox

    async def on_click(self, event: events.Click) -> None:
        self.checked = not self.checked
        event.prevent_default().stop()
        await self.emit(ButtonPressed(self))

    async def on_enter(self, event: events.Enter) -> None:
        self.mouse_over = True

    async def on_leave(self, event: events.Leave) -> None:
        self.mouse_over = False
