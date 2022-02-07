from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from textual_inputs.text_input import TextInput

import rich.box
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

class FixedTitleTextInput(TextInput):
    def render(self) -> RenderableType:
        """
        Produce a Panel object containing placeholder text or value
        and cursor.
        """
        if self.has_focus:
            segments = self._render_text_with_cursor()
        else:
            if len(self.value) == 0:
                if not self.placeholder:
                    segments = [""]
                else:
                    segments = [self.placeholder]
            else:
                segments = [self._conceal_or_reveal(self.value)]

        text = Text.assemble(*segments)

        title = self.title
        return Panel(
            text,
            title=title,
            title_align="left",
            height=3,
            style=self.style or "",
            border_style=self.border_style or Style(color="blue"),
            box=rich.box.DOUBLE if self.has_focus else rich.box.SQUARE,
        )

