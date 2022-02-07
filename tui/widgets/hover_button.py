from __future__ import annotations

import rich
from rich.console import RenderableType
from rich.text import Text

from textual.widgets import Button, ButtonPressed
from textual.widget import Reactive

class HoverButtonRenderable:
    def __init__(self, width, label: RenderableType, indent = 0, style: StyleType = "") -> None:
        self.label = label
        self.style = style
        self.width = width
        self.indent = indent

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        height = options.height or 1
        label_len = len(str(self.label))
        pre = int((self.width - label_len) / 2)
        post = self.width - label_len - pre

        if self.indent > 0:
            yield Text.assemble(
                f'{" ":{self.indent}s}',
                (Text(f'{" ":{pre}s}{self.label}{" ":{post}}', style=self.style))
            )
        else:
            yield Text(f'{" ":{pre}s}{self.label}{" ":{post}}', style=self.style)

class HoverButton(Button):
    def __init__(
        self,
        label: RenderableType,
        name: str | None = None,
        width: int = 0,
        style: StyleType = "white on dark_blue",
        hover_style: StyleType = "black on grey84",
        visible: bool = True,
        indent: int = 0,
    ):
        super().__init__(label=label,name=name)
        self.name = name or str(label)
        self.button_style = style
        self.hover_style = hover_style
        self.width = width
        self.visible = visible
        self.label = label
        self.indent = indent

    label: Reactive[RenderableType] = Reactive("")
    mouse_over: Reactive[bool] = Reactive(False)
    visible: Reactive[bool] = Reactive(True)

    def render(self) -> RenderableType:
        style = self.hover_style if self.mouse_over else self.button_style 
        width = self.width if self.width > 0 else len(self.label)+2
        if self.visible:
            return HoverButtonRenderable(width, self.label, indent=self.indent, style=style)
        else:
            return Text('')

    async def on_click(self, event: events.Click) -> None:
        event.prevent_default().stop()
        await self.emit(ButtonPressed(self))

    async def on_leave(self, event: events.Leave) -> None:
        self.mouse_over = False

    async def on_enter(self, event: events.Enter) -> None:
        self.mouse_over = True
