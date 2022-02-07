"""
Simple text input
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

#from contextlib import redirect_stdout
#import io

import rich
import rich.box
from rich.box import Box
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from rich.segment import Segment, Segments
from rich import get_console
from rich import print
from rich.color import Color
from rich.ansi import AnsiDecoder, _ansi_tokenize, SGR_STYLE_MAP
from rich.console import Group
from rich.jupyter import JupyterMixin

from textual import events
from textual.reactive import Reactive
from textual.widget import Widget
from textual_inputs.events import InputOnChange, InputOnFocus
from textual.views import WindowView

try:
    import tkinter as tk
    HaveTk = True
except:
    try:
        import Tkinter as tk
        HaveTk = True
    except:
        HaveTk = False

def getClipboardText():
    root = tk.Tk()
    root.withdraw()
    return root.clipboard_get()

if TYPE_CHECKING:
    from rich.console import RenderableType

HORIZONTALS_HEAVY: Box = Box(
    """\
 ━━ 
    
 ━━ 
    
 ━━ 
 ━━ 
    
 ━━ 
"""
)

class CliInput(Widget):
    """
    A CLI-style input widget.

    Args:
        name (Optional[str]): The unique name of the widget. If None, the
            widget will be automatically named.
        value (str, optional): Defaults to "". The starting text value.
        prompt (str, optional): Defaults to ">>>". Text that appears
            in the widget as the CLI prompt.
        title (str, optional): Defaults to "". A title on the top left
            of the widget's border.
        password (bool, optional): Defaults to False. Hides the text
            input, replacing it with bullets.
        height (int): Height of the CLI window

    Attributes:
        value (str): the value of the text field
        placeholder (str): The placeholder message.
        title (str): The displayed title of the widget.
        has_password (bool): True if the text field masks the input.
        has_focus (bool): True if the widget is focused.
        cursor (Tuple[str, Style]): The character used for the cursor
            and a rich Style object defining its appearance.

    Messages:
        InputOnChange: Emitted when the contents of the input changes.
        InputOnFocus: Emitted when the widget becomes focused.

    Examples:

    .. code-block:: python

        from textual_inputs import TextInput

        email_input = TextInput(
            name="email",
            placeholder="enter your email address...",
            title="Email",
        )

    """

    command: Reactive[str] = Reactive("")
    cursor: Tuple[str, Style] = (
        "|",
        Style(
            color="white",
            blink=True,
            bold=True,
        ),
    )
    _cursor_position: Reactive[int] = Reactive(0)
    _has_focus: Reactive[bool] = Reactive(False)
    command_count: Reactive[int] = Reactive(0)
    scroll_offset: Reactive[int] = Reactive(0)

    def __init__(
        self,
        proc_func,
        *,
        name: Optional[str] = None,
        prompt: str = ">>> ",
        width: int = None,
        height: int = 7,
        history: int = 0,
        placeholder: str = "",
        title: str = "",
        password: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, **kwargs)
        self.prompt = prompt
        self.placeholder = placeholder
        self.title = title
        self.height = height
        self.width = width
        self.command = ''
        self._cursor_position = 0
        self.history = history
        self.history_lines = []
        self.command_lines = []
        self.command_count = 0
        self.history_idx = 0
        self.scroll_offset = 0
        self.proc_func = proc_func
        self.max_options = get_console().options.update(
            width=400, height=None, 
        )

    def __rich_repr__(self):
        yield "name", self.name
        yield "title", self.title
        yield "prompt", self.prompt

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        return Measurement(console.width-4, console.width-4)

    @property
    def has_focus(self) -> bool:
        """Produces True if widget is focused"""
        return self._has_focus

    def render(self) -> RenderableType:
        """
        Produce a Panel object containing command line plus cursor
        and command history.
        """

        if self.has_focus:
            cmd_line = f'{self.prompt}{self._render_text_with_cursor()}'
        else:
            cmd_line = f'{self.prompt}{self.command}'

        # Add history lines to the render
        segments = []
        new_line = Segment("\n", style=None)
        if len(self.command_lines) > 0:
            for x in range(self.height-3,0,-1):
                if x+self.scroll_offset <= len(self.command_lines):
                    for s in self.command_lines[-(x+self.scroll_offset)]:
                        segments.append(Segment(str(s), s.style))
                    segments.append(new_line)
        segments.append(Segment(cmd_line, style=self.style))
        title = self.title

        return Panel(
            Segments(segments),
            title=title,
            title_align="left",
            height=self.height,
            width=self.width,
            style=self.style or "",
            border_style=self.border_style or Style(color="green") if self.has_focus else Style(color="blue"),
            box=rich.box.DOUBLE if self.has_focus else rich.box.SQUARE,
            #box=HORIZONTALS_HEAVY if self.has_focus else rich.box.HORIZONTALS,
            padding=(0,1),
        )

    def _render_text_with_cursor(self) -> List[Union[str, Tuple[str, Style]]]:
        """
        Produces the renderable Text object combining value and cursor
        """
        if len(self.command) == 0:
            segments = [self.cursor]
        elif self._cursor_position == 0:
            segments = [self.cursor, self.command]
        elif self._cursor_position == len(self.command):
            segments = [self.command, self.cursor]
        else:
            segments = [
                self.command[: self._cursor_position],
                self.cursor,
                self.command[self._cursor_position :],
            ]

        return Text.assemble(*segments)

    async def on_focus(self, event: events.Focus) -> None:
        self._has_focus = True
        await self._emit_on_focus()

    async def on_blur(self, event: events.Blur) -> None:
        self._has_focus = False

    async def process_enter(self):
        self.command.strip()
        command = self.command
        if len(self.command) > 0:
            if len(self.history_lines) == 0 or self.command != self.history_lines[-1]:
                self.history_lines.append(self.command)

        segs = []
        for s in self.decode_line(f'{self.prompt}{self.command}'):
            segs.append(s)
        self.command_lines.append(*segs)
        self.command = ""
        self.command_count += 1
        self._cursor_position = 0
        self.scroll_offset = 0
        self.history_idx = 0
        if len(command) > 0:
            await self.process_command(command)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            if self._cursor_position == 0:
                self._cursor_position = 0
            else:
                self._cursor_position -= 1

        elif event.key == "right":
            if self._cursor_position != len(self.command):
                self._cursor_position = self._cursor_position + 1

        elif event.key == "up":
            self.history_idx += 1
            if self.history_idx <= len(self.history_lines):
                self.command = self.history_lines[-self.history_idx]
                self._cursor_position = len(self.command)
            else:
                self.history_idx -= 1

        elif event.key == "down":
            if self.history_idx > 0:
                self.history_idx -= 1
                if self.history_idx > 0:
                    self.command = self.history_lines[-self.history_idx]
                    self._cursor_position = len(self.command)
                else:
                    self.command = ""
                    self._cursor_position = 0

        elif event.key == "home":
            self._cursor_position = 0

        elif event.key == "end":
            self._cursor_position = len(self.command)

        elif event.key == "ctrl+a":
            self._cursor_position = 0

        elif event.key == "ctrl+e":
            self._cursor_position = len(self.command)

        elif event.key == "ctrl+d":
            self._cursor_position = len(self.command)

        elif event.key == "ctrl+v":
            if not HaveTk:
                segs = [
                    get_console().render_lines("Please pip3 install tkinter",
                         self.max_options,
                         style=Style(),
                         pad=False
                     )
                ]
                self.command_lines.append(segs)
                self.command = ""
                self.command_count += 1
                self._cursor_position = 0
                self.scroll_offset = 0
                self.history_idx = 0
            else:
                s = getClipboardText()
                if len(s) > 0:
                    lines = s.split("\n")
                    if self._cursor_position == 0:
                        self.command = lines[0] + self.command
                    elif self._cursor_position == len(self.command):
                        self.command = self.command + lines[0]
                    else:
                        self.command = (
                            self.command[: self._cursor_position]
                            + lines[0]
                            + self.command[self._cursor_position :]
                        )
                    self._cursor_position += len(lines[0])

                    if len(lines) > 1:
                        await self.process_enter()

        elif event.key == "ctrl+h":  # Backspace
            if self._cursor_position == 0:
                return
            elif len(self.command) == 1:
                self.command = ""
                self._cursor_position = 0
            elif len(self.command) == 2:
                if self._cursor_position == 1:
                    self.command = self.command[1]
                    self._cursor_position = 0
                else:
                    self.command = self.command[0]
                    self._cursor_position = 1
            else:
                if self._cursor_position == 1:
                    self.command = self.command[1:]
                    self._cursor_position = 0
                elif self._cursor_position == len(self.command):
                    self.command = self.command[:-1]
                    self._cursor_position -= 1
                else:
                    self.command = (
                        self.command[: self._cursor_position - 1]
                        + self.command[self._cursor_position :]
                    )
                    self._cursor_position -= 1

            await self._emit_on_change(event)

        elif event.key == "delete":
            if self._cursor_position == len(self.command):
                return
            elif len(self.command) == 1:
                self.command = ""
            elif len(self.command) == 2:
                if self._cursor_position == 1:
                    self.command = self.command[0]
                else:
                    self.command = self.command[1]
            else:
                if self._cursor_position == 0:
                    self.command = self.command[1:]
                else:
                    self.command = (
                        self.command[: self._cursor_position]
                        + self.command[self._cursor_position + 1 :]
                    )
            await self._emit_on_change(event)

        elif event.key == "enter":
            await self.process_enter()

        elif event.key == "escape":
            self.command = ""
            self._cursor_position = 0
            self.history_idx = 0
            self.scroll_offset = 0

        elif len(event.key) == 1 and event.key.isprintable():
            if self._cursor_position == 0:
                self.command = event.key + self.command
            elif self._cursor_position == len(self.command):
                self.command = self.command + event.key
            else:
                self.command = (
                    self.command[: self._cursor_position]
                    + event.key
                    + self.command[self._cursor_position :]
                )

            if not self._cursor_position > len(self.command):
                self._cursor_position += 1

            await self._emit_on_change(event)

    async def _emit_on_change(self, event: events.Key) -> None:
        event.stop()
        await self.emit(InputOnChange(self))

    async def _emit_on_focus(self) -> None:
        await self.emit(InputOnFocus(self))

    async def on_mouse_scroll_down(self, event: events.MouseScrollUp) -> None:
        if len(self.command_lines) - (self.height-3) - self.scroll_offset > 0:
            self.scroll_offset += 1

    async def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.scroll_offset > 0:
            self.scroll_offset -= 1

    async def process_command(self, command) -> None:
        if command == "reset":
            self.command_lines = []
            self.command_count += 1
        else:
            if self.width is None:
                width, height = self.size
            else:
                width = self.width
            resp = await self.proc_func(command, width-2)
            style = Style()
            if resp is not None:
                for l in resp.split("\n"):
                    segs = []
                    for seg in self.decode_line(l):
                        segs.append(seg)
                    self.command_lines.append(segs)

    def decode_line(self, line: str) -> Iterable[Text]:
        """Decode a line containing ansi codes.

        Args:
            line (str): A line of terminal output.

        Returns:
            Text: A Text instance marked up according to ansi codes.
        """
        from_ansi = Color.from_ansi
        from_rgb = Color.from_rgb
        _Style = Style
        line = line.rsplit("\r", 1)[-1]
        style = Style()
        for token in _ansi_tokenize(line):
            plain_text, sgr, osc = token
            if osc:
                if osc.startswith("8;"):
                    _params, semicolon, link = osc[2:].partition(";")
                    if semicolon:
                        style = style.update_link(link or None)
            if sgr:
                # Translate in to semi-colon separated codes
                # Ignore invalid codes, because we want to be lenient
                codes = [
                    min(255, int(_code)) for _code in sgr.split(";") if _code.isdigit()
                ]
                iter_codes = iter(codes)
                for code in iter_codes:
                    if code == 0:
                        # reset
                        style = _Style.null()
                    elif code in SGR_STYLE_MAP:
                        # styles
                        style += _Style.parse(SGR_STYLE_MAP[code])
                    elif code == 38:
                        #  Foreground
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                style += _Style.from_color(
                                    from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                style += _Style.from_color(
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    )
                                )
                    elif code == 48:
                        # Background
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                style += _Style.from_color(
                                    None, from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                style += _Style.from_color(
                                    None,
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    ),
                                )
            if plain_text:
                yield Text(plain_text, style)
                style = Style()

