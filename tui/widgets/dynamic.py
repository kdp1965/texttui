from __future__ import annotations

import sys
from rich.console import RenderableType
from rich.padding import Padding, PaddingDimensions
from rich.style import StyleType
from rich.styled import Styled
from textual.widget import Widget
from textual.reactive import Reactive
from textual.message import Message

class RenderableUpdate(Message):
    pass

class Dynamic(Widget):
    def __init__(
        self,
        renderable: RenderableType,
        name: str | None = None,
        style: StyleType = "",
        padding: PaddingDimensions = 0,
    ) -> None:
        super().__init__(name)
        self.renderable = renderable
        self.style = style
        self.padding = padding
        if not isinstance(renderable, str):
            renderable._parent = self

    renderable: Reactive[RenderableType] = Reactive("")

    def render(self) -> RenderableType:
        renderable = self.renderable
        if self.padding:
            renderable = Padding(renderable, self.padding)
        return Styled(renderable, self.style)

    async def update(self, renderable: RenderableType) -> None:
        self.renderable = renderable
        self.refresh()

    async def update_renderable(self, renderable: RenderableType):
        self.renderable = renderable
        await self._parent.post_message(RenderableUpdate(self))

    async def require_update(self):
        await self._parent.post_message(RenderableUpdate(self))
