from __future__ import annotations

import sys
from typing import Optional, TYPE_CHECKING, NamedTuple
from dataclasses import dataclass
from contextlib import suppress

from rich.box import Box, ROUNDED

from rich import get_console
from rich.align import AlignMethod
from rich.jupyter import JupyterMixin
from rich.measure import Measurement, measure_renderables
from rich.padding import Padding, PaddingDimensions
from rich.style import StyleType, Style
from rich.text import Text, TextType
from rich.segment import Segment
from rich.ansi import AnsiDecoder, _ansi_tokenize, SGR_STYLE_MAP
from rich.color import Color
from rich.region import Region

from textual.widget import Widget
from textual.reactive import Reactive

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

class TabContent(NamedTuple):
    """ Defines a renderable object on the Tab and if it should wrap based on tab width """

    renderable: RenderableType
    wrap: int
    expand_height: bool

@dataclass
class Tab:
    """ Class for holding all information about a tab """

    name: str
    label: str
    line_cache: list(Segment)
    renderables: list(TabContent)
    new_renderables: list(TabContent)
    scroll_offset: int = 0
    at_bottom: bool = True
    render_width: int = 0
    render_height: int = 0
    need_rerender: int = 0
    dynamic_content: bool = False
    has_close: bool = False
    has_scroll: bool = True
    _parent: Tabs = None

class TabsRenderable(JupyterMixin):
    """A console renderable that draws a border around its contents.

    Args:
        renderable (RenderableType): A console renderable object.
        box (Box, optional): A Box instance that defines the look of the border (see :ref:`appendix_box`.
            Defaults to box.ROUNDED.
        safe_box (bool, optional): Disable box characters that don't display on windows legacy terminal with *raster* fonts. Defaults to True.
        expand (bool, optional): If True the panel will stretch to fill the console
            width, otherwise it will be sized to fit the contents. Defaults to True.
        style (str, optional): The style of the panel (border and contents). Defaults to "none".
        border_style (str, optional): The style of the border. Defaults to "none".
        border_focus_style (str, optional): The style of the border when tabs have focus. Defaults to "none".
        width (Optional[int], optional): Optional width of panel. Defaults to None to auto-detect.
        height (Optional[int], optional): Optional height of panel. Defaults to None to auto-detect.
        padding (Optional[PaddingDimensions]): Optional padding around renderable. Defaults to 0.
        highlight (bool, optional): Enable automatic highlighting of panel title (if str). Defaults to False.
    """

    def __init__(
        self,
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        expand: bool = True,
        style: StyleType = "none",
        border_style: StyleType = "none",
        border_focus_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> None:
        self.box = box
        self.title = title
        self.title_align: AlignMethod = title_align
        self.subtitle = subtitle
        self.subtitle_align = subtitle_align
        self.safe_box = safe_box
        self.expand = expand
        self.style = style
        self.border_style = border_style
        self.border_focus_style = border_focus_style
        self.width = width
        self.height = height
        self.padding = padding
        self.highlight = highlight
        self.tabs = {}
        self.tab_extents = {}
        self.first_tab = 0
        self.selected = None
        self._has_focus = False
        self.prev_tab = None
        self._line_cache: list(Segment) = []

    @classmethod
    def fit(
        cls,
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        style: StyleType = "none",
        border_style: StyleType = "none",
        border_focus_style: StyleType = "none",
        width: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
    ) -> "Panel":
        """An alternative constructor that sets expand=False."""
        return cls(
            box,
            title=title,
            title_align=title_align,
            subtitle=subtitle,
            subtitle_align=subtitle_align,
            safe_box=safe_box,
            style=style,
            border_style=border_style,
            border_focus_style=border_focus_style,
            width=width,
            padding=padding,
            expand=False,
        )

    @property
    def _title(self) -> Optional[Text]:
        if self.title:
            title_text = (
                Text.from_markup(self.title)
                if isinstance(self.title, str)
                else self.title.copy()
            )
            title_text.end = ""
            title_text.plain = title_text.plain.replace("\n", " ")
            title_text.no_wrap = True
            title_text.expand_tabs()
            title_text.pad(1)
            return title_text
        return None

    @property
    def _subtitle(self) -> Optional[Text]:
        if self.subtitle:
            subtitle_text = (
                Text.from_markup(self.subtitle)
                if isinstance(self.subtitle, str)
                else self.subtitle.copy()
            )
            subtitle_text.end = ""
            subtitle_text.plain = subtitle_text.plain.replace("\n", " ")
            subtitle_text.no_wrap = True
            subtitle_text.expand_tabs()
            subtitle_text.pad(1)
            return subtitle_text
        return None

    def render_tabs(self, box, width, style, border_style):
        # Calculate the width of each tab
        tab_widths = []
        total_width = 0
        selected_tab = 0
        tab_count = 0
        for t in self.tabs:
            t_width = len(self.tabs[t].label) + 4 + (2 if self.tabs[t].has_close else 0)
            tab_widths.append(t_width)
            total_width += t_width
            if t == self.selected:
                selected_tab = tab_count
            tab_count += 1

        # Determine the first tab to be displayed
        if total_width <= width-3:
            self.first_tab = 0
        else:
            sel_tab_index = 0
            for t in self.tabs:
                if t == self.selected:
                    break
                sel_tab_index += 1

            # Ensure the selected tab is fully visible
            tab_index = 0
            partial_width = 0
            match_found = False
            while not match_found:
                # Calculate width including selected tab
                for i in range(tab_index, sel_tab_index+1):
                    partial_width += tab_widths[i]

                # Test if selected tab fits in the given space
                if partial_width <= width - 3:
                    self.first_tab = tab_index
                    match_found = True
                    break
                else:
                    # Test if selected tab is already the first tab and
                    # is simply too wide
                    if tab_index == sel_tab_index:
                        self.first_tab = tab_index
                        match_found = True
                        break
                    else:
                        # Remove the left-most tab and test again
                        tab_index += 1
                        partial_width = 5

            # Update the total_width
            total_width = partial_width
            for i in range(sel_tab_index + 1, len(tab_widths)):
                total_width += tab_widths[i]

        new_line = Segment.line()

        # ============================
        # Render the tabs
        # ============================
        if len(self.tabs) == 0:
            if title_text is None or width <= 4:
                yield Segment(box.get_top([width - 2]), border_style)
            else:
                title_text.align(self.title_align, width - 4, character=box.top)
                yield Segment(box.top_left + box.top, border_style)
                yield from console.render(title_text)
                yield Segment(box.top + box.top_right, border_style)
        else:
            # ==========================
            # Top line of the tabs
            # ==========================
            yield Segment("  ", border_style)
            tabno = 0
            x = 2
            rem = width-2
            self.tab_extents = {}

            # If the first tab isn't displayed, then show a "-" tab
            if self.first_tab > 0:
                yield Segment(box.get_top([3]), border_style)
                x += 5
                total_width += 5
                rem -= 5
            else:
                self.prev_tab = None

            for t in self.tabs:
                if tabno >= self.first_tab:
                    tab = self.tabs[t]
                    w = tab_widths[tabno]-2
                    if w+2 >= rem:
                        w = rem-3
                    if w >= 0:
                        yield Segment(box.get_top([w]), border_style)
                        self.tab_extents[t] = (x, x+w+1)
                        x += w+2
                        rem -= w+2
                tabno += 1
            if width-2 > total_width:
                yield Segment(f"{' ':{width-total_width-2}}", border_style)
            yield new_line

            # ==========================
            # The tab text
            # ==========================
            yield Segment("  ", border_style)
            rem = width-2

            # If the first tab isn't displayed, then show a "-" tab
            if self.first_tab > 0:
                yield Segment(box.mid_left, border_style)
                yield Segment(f' - ', style)
                yield Segment(box.mid_right, border_style)
                rem -= 5

            tabno = 0
            for t in self.tabs:
                if tabno >= self.first_tab:
                    w = tab_widths[tabno]-4
                    #w = tab_widths[tabno]
                    tab = self.tabs[t]
                    if w+5 > rem:
                        w = rem-5

                    if w > 1:
                        yield Segment(box.mid_left, border_style)
                        yield Segment(f' {tab.label[:(w-2 if tab.has_close else w)]} {"❎" if tab.has_close else ""}', style)
                        yield Segment(box.mid_right, border_style)
                        rem -= w+4
                    elif w > -2:
                        yield Segment(box.mid_left, border_style)
                        yield Segment(f'{tab.label[:w+2]}', style)
                        yield Segment(box.mid_right, border_style)
                        break
                    elif w > -3:
                        yield Segment(box.mid_left, border_style)
                        yield Segment(box.mid_right, border_style)
                        break
                else:
                    self.prev_tab = t
                tabno += 1
            if width-2 > total_width:
                yield Segment(f"{' ':{width-total_width-2}}", border_style)
            yield new_line

            # ==========================
            # The tab bottom
            # ==========================
            tabno = 0
            rem = width-2
            yield Segment(box.top_left+box.top, border_style)
            if self.first_tab > 0:
                yield Segment(box.bottom_divider, border_style)
                yield Segment(box.bottom*3, border_style)
                yield Segment(box.bottom_divider, border_style)
                rem -= 5

            for t in self.tabs:
                if tabno >= self.first_tab:
                    w = tab_widths[tabno]-4
                    tab = self.tabs[t]
                    if w+5 > rem:
                        w = rem-5
                    if t == self.selected:
                        if w > -2:
                            yield Segment(box.bottom_right + f'{" ":{w+2}}' + box.bottom_left, border_style)
                            rem -= w+4
                    else:
                        if w > -3:
                            yield Segment(box.bottom_divider + f'{box.bottom*(w+2)}' + box.bottom_divider, border_style)
                            rem -= w+4
                            if w < tab_widths[tabno]-4:
                                break
                        elif w == -3:
                            yield Segment(box.bottom, border_style)
                            rem -= 1
                            break
                tabno += 1
            #yield Segment(f"{box.top*(width-total_width-3)}{box.top_right}", border_style)
            yield Segment(f"{box.top*(rem-1)}{box.top_right}", border_style)
        yield new_line

    def render_tab_content(self,
            tab,
            renderables,
            console,
            child_options,
            max_options,
            style,
            pad_total,
            decoder,
            width,
            height
        ) -> None:
        """ Renders the tab content into it's line_cache list """
        lines = []
        line = 0
        for x in range(len(renderables)):
            if hasattr(renderables[x], 'expand_height'):
                if hasattr(renderables[x].renderable, 'set_height'):
                    renderables[x].renderable.set_height(height - line)
                elif not isinstance(renderables[x].renderable, str):
                    renderables[x].renderable.height = height - line
                if hasattr(renderables[x].renderable, 'set_width'):
                    renderables[x].renderable.set_width(width)
            if renderables[x].wrap:
                lines.extend(console.render_lines(renderables[x].renderable, child_options, pad=False))
            else:
                lines.extend(console.render_lines(renderables[x].renderable, max_options, style=style, pad=False))
            line += len(lines)

        for l in lines:
            new_l = []
            col = 0
            emojis = [ "⚫", '🌕', '👉', "🔳", "✅", '🔵', '🔴', '⚪', "❎" ]
            for s in l:
                if isinstance(s, Segment) and not "\x1b" in s.text:
                    new_l.append(s)
                    col += len(s.text)
                    col += len([x for x in emojis if x in s.text])
                elif len(s.text.strip()) > 0 or len(s.text) == 1:
                    for item in self.decode_line(s.text):
                        seg = Segment(str(item), item.style)
                        new_l.append(seg)
                    line = decoder.decode_line(s.text)
                    col += len(line)
                    col += len([x for x in emojis if x in line])
            if width-col-2-pad_total > 0:
                new_l.append(Segment(f"{' ':{width-col-2-pad_total}}"))
            tab.line_cache.append(new_l)

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        try:
            tab = self.tabs[self.selected]
        except:
            tab = None

        decoder = AnsiDecoder()
        top, right, bottom, left = Padding.unpack(self.padding)
        style = console.get_style(self.style)
        border_style = style + console.get_style(self.border_style if not self._has_focus else self.border_focus_style)
        width = (
            options.max_width
            if self.width is None
            else min(options.max_width, self.width)
        )

        safe_box: bool = console.safe_box if self.safe_box is None else self.safe_box
        box = self.box.substitute(options, safe=safe_box)

        title_text = self._title
        if title_text is not None:
            title_text.style = border_style

        child_width = width - 2 - right - left
        child_height = self.height or options.height or None
        height = child_height
        if child_height:
            child_height -= 2
            if len(self.tabs) > 0:
                child_height -= 2
        child_options = options.update(
            #width=child_width, height=child_height, highlight=self.highlight
            width=child_width, height=None, highlight=self.highlight
        )
        self.child_height = child_height

        # ============================
        # Render the tabs
        # ============================
        yield from self.render_tabs(box, width, style, border_style)

        # ============================
        # Render the tab content
        # ============================
        left_pad = Segment(f"{' ' * left}", self.style)
        right_pad = Segment(f"{' ' * right}", self.style)
        line_start = Segment(box.mid_left, border_style)
        line_end = Segment(f"{box.mid_right}", border_style)
        new_line = Segment.line()

        max_options = options.update(
            width=350, height=None, highlight=self.highlight
        )

        rows = 0
        if tab is not None:
            pad_total = left + right
            # Test if re-render required
            if tab.render_width != width or tab.render_height != height or tab.need_rerender or tab.dynamic_content:
                tab.line_cache = []
                if len(tab.renderables) > 0:
                    self.render_tab_content(
                            tab, tab.renderables,
                            console, child_options,
                            max_options, style,
                            pad_total, decoder, width,
                            child_height
                    )
                tab.need_rerender = False
                tab.render_width = width
                tab.render_height = height

            # Test for new items to render
            if len(tab.new_renderables) > 0:
                self.render_tab_content(
                        tab, tab.new_renderables,
                        console, child_options,
                        max_options, style,
                        pad_total, decoder, width,
                        child_height
                )
                tab.renderables.extend(tab.new_renderables)
                tab.new_renderables = []

            lines = tab.line_cache
            start = 0
            if tab.at_bottom:
                tab.scroll_offset = len(lines)-child_height
                if tab.scroll_offset < 0:
                    tab.scroll_offset = 0
            for line in lines:
                if start >= tab.scroll_offset:
                    yield line_start
                    yield left_pad
                    rem = child_width
                    for s in line:
                        w = len(decoder.decode_line(s.text))
                        if w <= rem:
                            yield s
                            rem -= w
                        else:
                            # Create a partial segment
                            yield Segment(s.text[:rem], s.style)
                            break
                    yield right_pad
                    yield line_end
                    yield new_line
                    rows += 1
                    if rows == child_height:
                        break
                else:
                    start += 1

        if self.expand and rows != child_height:
            for x in range(child_height-rows):
                yield line_start
                yield left_pad
                yield Segment(f"{' ' * child_width}", style)
                yield right_pad
                yield line_end
                yield new_line

        subtitle_text = self._subtitle
        if subtitle_text is not None:
            subtitle_text.style = border_style

        if subtitle_text is None or width <= 4:
            yield Segment(box.get_bottom([width - 2]), border_style)
        else:
            subtitle_text.align(self.subtitle_align, width - 4, character=box.bottom)
            yield Segment(box.bottom_left + box.bottom, border_style)
            yield from console.render(subtitle_text)
            yield Segment(box.bottom + box.bottom_right, border_style)

        yield new_line

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        try:
            renderable = self.tabs[self.selected]
        except:
            renderable = ""

        _title = self._title
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        renderables = [renderable, _title] if _title else [renderable]

        if self.width is None:
            width = (
                measure_renderables(
                    console,
                    options.update_width(options.max_width - padding - 2),
                    renderables,
                ).maximum
                + padding
                + 2
            )
        else:
            width = self.width
        return Measurement(width, width)

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

# ======================================================================
# The actual Tab widget
# ======================================================================
class Tabs(Widget, can_focus=True):
    def __init__(
        self,
        style: StyleType = "",
        name: str | None = None,
        border_style: StyleType = "none",
        border_focus_style: StyleType = "none",
        *,
        box: Box = ROUNDED,
        padding: int = 0,
    ):
        super().__init__(name=name)
        self._tabs = TabsRenderable(
                box=box,style=style,
                border_style=border_style,
                border_focus_style=border_focus_style
        )

    _tabs: Reactive[TabsRenderable] = Reactive(TabsRenderable)
    _has_focus: Reactive[bool] = Reactive(False)
    _update_required: Reactive[int] = Reactive(0)

    def __rich_repr__(self) -> Result:
      yield self.name

    def render(self) -> RenderableType:
        region, clip = self._parent.layout.regions[self]
        self.child_region = Region(region.x+3, region.y+4, region.width-5, region.height-4)
        return self._tabs

    def add_tab(self,
            name: str,
            label: str,
            has_close: bool = False,
            has_scroll: bool = True,
        ) -> None:
        self._tabs.tabs[name] = Tab(
            name=name,
            label=label,
            new_renderables=[],
            line_cache=[],
            renderables=[],
            has_close = has_close,
            _parent = self,
        )
        if self._tabs.selected == None:
            self._tabs.selected = name
            self._update_required += 1

    def add_renderable(self,
            tab_name: str,
            content: RenderableType,
            wrap: bool = True,
            expand_height: bool = False,
        ) -> None:
        if not isinstance(content, str):
            content._parent = self
        self._tabs.tabs[tab_name].new_renderables.append(TabContent(content, wrap, expand_height))
        self._update_required += 1

    def select_tab(self, name: str) -> None:
        if name in self._tabs.tabs:
            self._tabs.selected = name
            self._update_required += 1

    async def on_focus(self, event: events.Focus) -> None:
        self._tabs._has_focus = True
        self._has_focus = True

    async def on_blur(self, event: events.Blur) -> None:
        self._has_focus = False
        self._tabs._has_focus = False

    @property
    def has_focus(self) -> bool:
        """Produces True if widget is focused"""
        return self._has_focus

    async def on_click(self, event: events.Click) -> None:
        y = event.y
        x = event.x
        if y <= 2:
            # Determine if x is within any of the tabs
            prev = None
            for t in self._tabs.tab_extents:
                x1, x2 = self._tabs.tab_extents[t]
                if x >= x1 and x <= x2:
                    # Check if has_close and mouse is in the "X"
                    if self._tabs.tabs[t].has_close and x >= x2-2:
                        # Find the name of the next tab in case this is the first
                        next_tab = None
                        found_tab = False
                        for t2 in self._tabs.tab_extents:
                            if found_tab:
                                next_tab = t2
                                break
                            elif t2 == t:
                                found_tab = True
                        await self.on_close_tab(t)
                        if not t in self._tabs.tabs:
                            if prev is not None:
                                self._tabs.selected = prev
                            else:
                                self._tabs.selected = next_tab
                    else:
                        self._tabs.selected = t

                    self._update_required += 1
                    break
                prev = t
            else:
                # Test for click in prev_tab 
                if self._tabs.prev_tab is not None:
                    if x >= 2 and x <= 6:
                        self._tabs.selected = self._tabs.prev_tab
                        self._update_required += 1

    async def handle_renderable_update(self, message: RenderableUpdate) -> None:
        # re-render all tabs
        for t in self._tabs.tabs:
            self._tabs.tabs[t].need_rerender = True
        self._update_required += 1

    async def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self._tabs.selected is not None:
            tab = self._tabs.tabs[self._tabs.selected]
            if len(tab.line_cache) - (self._tabs.child_height) - tab.scroll_offset > 0:
                tab.scroll_offset += 3
                if tab.scroll_offset > len(tab.line_cache) - (self._tabs.child_height):
                    tab.scroll_offset = len(tab.line_cache) - (self._tabs.child_height)
                if tab.scroll_offset + self._tabs.child_height == len(tab.line_cache):
                    tab.at_bottom = True
                self._update_required += 1

    async def on_mouse_scroll_down(self, event: events.MouseScrollUp) -> None:
        if self._tabs.selected is not None:
            tab = self._tabs.tabs[self._tabs.selected]
            if tab.scroll_offset > 0:
                tab.scroll_offset -= 3
                if tab.scroll_offset < 0:
                    tab.scroll_offset = 0
                tab.at_bottom = False
                self._update_required += 1
    
    async def on_close_tab(self, tab: Tab) -> None:
        del self._tabs.tabs[tab]

    def has_tab(self, tab_name: str) -> bool:
        return tab_name in self._tabs.tabs

    def get_active_tab(self) -> Tab:
        if self._tabs.selected is not None:
            return self._tabs.tabs[self._tabs.selected]
        return None

