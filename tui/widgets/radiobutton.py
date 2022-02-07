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


class Radiobutton(Button):
    def __init__(
        self,
        label: str,
        style: StyleType = "white on black",
        hover_style: StyleType = "white on grey39",
        name: str | None = None,
        *,
        selected: bool = False,
        radiotype: str = 'large',
        radiocolor: str = 'blue',
        radiogroup: RenderableType | None = None,
        indent: int = 0
    ):
        super().__init__(label=label, style=style, name=name)
        self.selected = selected
        self.name = name or label
        self.radiotype = radiotype.lower() or "large"
        self.radiocolor = radiocolor
        self.radiogroup = radiogroup
        self.indent = indent
        self.style = style
        self.hover_style = hover_style

    mouse_over: Reactive[bool] = Reactive(False)
    selected: Reactive[bool] = Reactive(False, layout=True)
    label: Reactive[str] = Reactive("")
    radiocolor: Reactive[str] = Reactive("")
    radiotype: Reactive[str] = Reactive("")

    def __rich_repr__(self) -> Result:
      yield self.label

    def is_selected(self) -> bool:
      return self.selected

    def render(self) -> RenderableType:
        width = 2
        if self.radiotype == 'large':
            if self.radiocolor == 'yellow':
                boxes = [ "⚫", '🌕' ]
            else:
                boxes = [ "⚫", f':{self.radiocolor}_circle:' ]
        elif self.radiotype == 'medium' or self.radiotype == 'small':
            boxes =  ["၀", "◉"] 
            width = 1
        elif self.radiotype == 'ascii':
            boxes =  ["( )", "(o)"] 
            width = 3
        elif self.radiotype == 'pointer':
            boxes =  [" ", "👉"] 

        radiobox_table = Table.grid(padding=(0, 1), expand=True)
        radiobox_table.style = self.style
        if self.indent > 0:
          radiobox_table.add_column(ratio=0, width=min(0,self.indent-2))
        radiobox_table.add_column(ratio=0, width=width)
        radiobox_table.add_column("label",  ratio=1, no_wrap=True, overflow="crop")

        if self.mouse_over:
            label = f'[{self.hover_style}]{self.label}' if self.hover_style is not None else self.label
        else:
            label = f'[{self.style}]{self.label}' if self.style is not None else self.label
        if self.indent > 0:
            radiobox_table.add_row('', boxes[1] if self.selected else boxes[0], label)
        else:
            radiobox_table.add_row(boxes[1] if self.selected else boxes[0], label)
        radiobox: RenderableType
        radiobox = radiobox_table
        return radiobox

    async def on_click(self, event: events.Click) -> None:
        self.selected = True 
        if self.radiogroup is not None:
            self.radiogroup.select(self.name)
        event.prevent_default().stop()
        await self.emit(ButtonPressed(self))
    async def on_enter(self, event: events.Enter) -> None:
        self.mouse_over = True

    async def on_leave(self, event: events.Leave) -> None:
        self.mouse_over = False

class RadioGroup:
    def __init__(
        self,
        buttons: str,
        style: StyleType = "white on black",
        name: str | None = None,
        *,
        selected: str = '',
        radiotype: str = 'large',
        radiocolor: str = 'blue',
        indent: int = 0
    ):
        self.name = name
        self.indent = indent

        # Create the Radiobuttons
        self.buttons = {
            name.lower().replace(" ","_"): Radiobutton(
                name,
                radiotype=radiotype,
                radiocolor=radiocolor,
                style=style,
                name=name.lower().replace(" ","_"),
                indent=self.indent
            )
            for name in buttons.split(",")
        }

        # Add this radio group to all buttons
        for b in self.buttons:
            self.buttons[b].radiogroup = self
            if b == selected:
                self.buttons[b].selected = True

    def get_button(self, name) -> Radiobutton:
        return self.buttons[name]

    def select(self, button) -> None:
        for b in self.buttons:
            if b == button:
                if not self.buttons[b].selected:
                    self.buttons[b].selected = True
            else:
                if self.buttons[b].selected:
                    self.buttons[b].selected = False


