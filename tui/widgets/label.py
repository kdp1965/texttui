from __future__ import annotations

import rich
from rich.align import Align
from rich.style import Style, StyleType

from textual.widget import Reactive, Widget

class Label(Widget):
    def __init__(
        self,
        label: str,
        style: StyleType = "bold",
        name: str | None = None,
        align: str = "left",
    ):
        super().__init__(name=name)
        self.name = name or label
        self.label = label
        self.style = style
        self.align = align

    label: Reactive[str] = Reactive('')

    def render(self) -> RenderableType:
        if self.align == "left":
            return Align.left(self.label, style=self.style)
        elif self.align == "center":
            return Align.center(self.label, style=self.style)
        else:
            return Align.right(self.label, style=self.style)

    def set_label(self, label):
        self.label = label

