from __future__ import annotations

from dataclasses import dataclass

from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from textual.reactive import Reactive
from textual.widget import Widget
import math

@dataclass
class PlotAxis:
    min_value:  float
    max_value:  float
    divisions:  int
    format_str: str = ":.1f"

@dataclass
class PlotAnnotation:
    x:  float
    y:  float
    text:   Text

class TuiPlot(Widget):
    def __init__(
        self,
        style: StyleType = "white on black",
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        border: bool = True,
        padding: PaddingDimensions = (0, 1),
    ):
        """ Graphs data using Braille dot pattern unicode characters """

        super().__init__(name=name)
        self.width = width
        self.height = height
        self.style = style
        # These set the virtual x and y extents
        self.x_min = 0.0
        self.x_max = 1.0
        self.y_min = 0.0
        self.y_max = 1.0
        self.border_style = style
        self.style = Style(color="color(7)")
        self.style_stack = []
        self.border = border
        self.y_label = None
        self.y_axis = None
        self.x_label = None
        self.x_axis = None
        self.annotations = []

    def render(self) -> RenderableType:
        """ Renders the graph canvas to a Panel with unicode characters """

        # Create a canvas on which to render graphics
        self.canvas = [[0 for col in range(self.width*2)] for row in range(self.height*4)]
        self.palette = [[None for col in range(self.width)] for row in range(self.height)]

        # Calculate Y axis size
        axis_width = int(self.plot_width/2)+2
        x_offset = 0
        y_axis_width = 0
        if self.y_axis is not None:
            axis_width += 1
            index = 0
            y_span = self.y_axis.max_value - self.y_axis.min_value
            y_vals = []
            for i in range(self.y_axis.divisions):
                ratio = i / float(self.y_axis.divisions-1)
                axis_val = self.y_axis.min_value + ratio * y_span
                axis_str = f'{axis_val:{self.y_axis.format_str}}'
                y_vals.append(axis_str)
                axis_str_len = len(axis_str)
                if axis_str_len > y_axis_width:
                    y_axis_width = axis_str_len
        x_offset += y_axis_width
        axis_width -= y_axis_width

        # ============================================
        # Render graphics to the raw canvas
        # ============================================
        save_width = self.plot_width
        self.plot_width -= y_axis_width
        self.render_canvas()
        self.plot_width = save_width

        # Convert the canvas to and ASCII representation
        text_lines = []
        c = self.canvas
        color = "none"
        for y in range(self.plot_height-4,-1,-4):
            text = f"[{color}]"
            for x in range(0,self.plot_width,2):
                p =  c[y+0][x] * 64
                p += c[y+1][x] * 4
                p += c[y+2][x] * 2
                p += c[y+3][x] 
                p += c[y+0][x+1] * 128
                p += c[y+1][x+1] * 32
                p += c[y+2][x+1] * 16
                p += c[y+3][x+1] * 8
        
                if p == 0:
                    text += ' '
                else:
                    pp = self.palette[int(y/4)][int(x/2)].color.name
                    if pp != color:
                        text += f"[{pp}]{chr(10240 + p)}"
                        color = pp
                    else:
                        text += f"{chr(10240 + p)}"
            text += "\n"
            text_lines.append(text)

        # Render annotations
        self.render_annotations(text_lines)

        # Add Y axis
        if self.y_axis is not None:
            lines = [int(i * int(self.plot_height/4) / (self.y_axis.divisions-1)) for i in range(self.y_axis.divisions)]
            index = 0
            res = {lines[i] : y_vals[i] for i in range(len(y_vals))}
            for l in text_lines:
                if index in res:
                    l = f"[white]{res[index]:>{y_axis_width}}├" + l
                else:
                    l = f"[white]{' ' * y_axis_width}│" + l
                text_lines[index] = l
                index += 1

        # Add Y label
        if self.y_label is not None:
            index = 0
            x_offset += 2
            label_str = str(self.y_label).center(len(text_lines))
            for l in text_lines:
                l = f"[white]{label_str[index]} " + l
                text_lines[index] = l
                index += 1

        # Add X axis
        if self.x_axis is not None:
            centers = [int(i * (axis_width-1) / (self.x_axis.divisions-1)) for i in range(self.x_axis.divisions)]

            axis_text = "└" + "─" * (axis_width-2) + "┘\n"
            for i in range(len(centers)):
                if i != 0 and i != len(centers)-1:
                    axis_text = axis_text[:centers[i]] + '┴' + axis_text[centers[i]+1:]
            if self.y_axis:
                axis_text = (" " * (x_offset-y_axis_width)) + f'[white]{y_vals[-1]:>{y_axis_width}}' + axis_text
            else:
                axis_text = (" " * x_offset) + "[white]" + axis_text
            text_lines.append(axis_text)
            x_span = self.x_axis.max_value - self.x_axis.min_value
            axis_text = ''


            for i in range(self.x_axis.divisions):
                ratio = i / float(self.x_axis.divisions-1)
                axis_val = self.x_axis.min_value + ratio * x_span
                axis_str = f'{axis_val:{self.x_axis.format_str}}'
                axis_str_len = len(axis_str)
                if i == 0:
                    axis_text += axis_str
                    axis_text += ' ' * (axis_width - axis_str_len)
                else:
                    # Substitute text in the axis_text string
                    pre_len = int(axis_str_len/2)
                    axis_text = axis_text[:centers[i]-pre_len] + axis_str + axis_text[centers[i]+axis_str_len:]

            axis_text += '\n'
            text_lines.append(("[white]" + " " * x_offset) + axis_text)

        # Add X label
        if self.x_label is not None:
            if isinstance(self.x_label, Text):
                text = f"[{self.x_label.style.color.name}]" + str(self.x_label).center(axis_width)
            else:
                text = "[white]" + self.x_label.center(axis_width)
            text += "\n"
            text_lines.append(text)

        # Return the renderable
        text = ''.join(text_lines)
        if self.border:
            return Panel(
                    text,
                    width=self.width,
                    height=self.height,
                    style=self.border_style,
            )
        else:
            return text

    def set_x_extents(self, x_min, x_max) -> None:
        """ Sets the virtual X extents for drawing """

        self.x_min = x_min
        self.x_max = x_max

    def set_y_extents(self, y_min, y_max) -> None:
        """ Sets the virtual Y extents for drawing """

        self.y_min = y_min
        self.y_max = y_max

    def set_height(self, height: int) -> None:
        """ Sets the plot window height in rows """

        self.height = height
        self.plot_height = (height - 2) * 4
        if self.x_label is not None:
            self.plot_height -= 4
        if self.x_axis is not None:
            self.plot_height -= 4

    def set_width(self, width: int) -> None:
        """ Sets the plot window width in columns """

        self.width = width
        self.plot_width = (width - 8) * 2
        if self.y_label is not None:
            self.plot_width -= 2

    def draw_line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """ Renders a line to the canvas using the current style """

        # Account for frame and padding
        xscale = self.plot_width / (self.x_max - self.x_min)
        yscale = self.plot_height / (self.y_max - self.y_min)

        x_min = int(self.x_min * xscale)
        x_max = int(self.x_max * xscale)
        y_min = int(self.y_min * yscale)
        y_max = int(self.y_max * yscale)

        xl = int(x1 * xscale)
        xr = int(x2 * xscale)
        yl = int(y1 * yscale) - y_min
        yr = int(y2 * yscale) - y_min

        steep = False
        if abs(xl-xr) < abs(yl-yr):
            xl,yl = yl,xl
            xr,yr = yr,xr
            steep = True

        if xr < xl:
            xr,xl = xl,xr
            yr,yl = yl,yr

        # Start at left endpoint
        x = xl
        y = yl

        # Delta X and Y
        dx = xr - xl
        dy = yr - yl

        # Test for vertical line
        if dx == 0:
            if dy == 0:
                # Single plot point
                if steep:
                    if y >= x_min and y < x_max and x >= (y_min-y_min) and x < (y_max-y_min):
                        self.canvas[x][y] = 1
                        self.palette[int(x/4)][int(y/2)] = self.style or self.palette[int(x/4)][int(y/2)]
                else:
                    if x >= x_min and x < x_max and y >= (y_min-y_min) and y < (y_max-y_min):
                        self.canvas[y][x] = 1
                        self.palette[int(y/4)][int(x/2)] = self.style or self.palette[int(y/4)][int(x/2)]
                return

            if yr < yl:
                yr,yl = yl,yr
            for y in range(yl, yr+1):
                # Single vertical line
                if steep:
                    if y >= x_min and y < x_max and x >= (y_min-y_min) and x < (y_max-y_min):
                        self.canvas[x][y] = 1
                        self.palette[int(x/4)][int(y/2)] = self.style or self.palette[int(x/4)][int(y/2)]
                else:
                    if x >= x_min and x < x_max and y >= (y_min-y_min) and y < (y_max-y_min):
                        self.canvas[y][x] = 1
                        self.palette[int(y/4)][int(x/2)] = self.style or self.palette[int(y/4)][int(x/2)]
                return
            
        # Error terms
        derror = abs(dy/dx)
        err = 0

        while x <= xr:
            if steep:
                if y >= x_min and y < x_max and x >= (y_min-y_min) and x < (y_max-y_min):
                    self.canvas[x][y] = 1
                    self.palette[int(x/4)][int(y/2)] = self.style or self.palette[int(x/4)][int(y/2)]
            else:
                if x >= x_min and x < x_max and y >= (y_min-y_min) and y < (y_max-y_min):
                    self.canvas[y][x] = 1
                    self.palette[int(y/4)][int(x/2)] = self.style or self.palette[int(y/4)][int(x/2)]

            err += derror
            if err > 0.5:
                y += (1 if yr > yl else -1)
                err -= 1
            x += 1

    def push_line_color(self, color: str) -> None:
        """ Push a new line color / style to the style stack. """

        self.style_stack.append(self.style)
        self.style = Style(color = color)

    def pop_line_color(self) -> None:
        """ Pop the current line color / style from the style stack. """

        if len(self.style_stack) > 0:
            self.style = self.style_stack.pop()

    def render_canvas(self) -> None:
        """ Draws the data to the bare canvas """
        pass

    def add_x_label(self, label: str | Text) -> None:
        """ Add an X label to the graph """
        self.x_label = label

    def add_y_label(self, label: str | Text) -> None:
        """ Add a Y label to the graph """
        self.y_label = label

    def add_x_axis(self, axis: PlotAxis) -> None:
        """ Add an X axis to the graph """
        self.x_axis = axis

    def add_y_axis(self, axis: PlotAxis) -> None:
        """ Add an Y axis to the graph """
        self.y_axis = axis

    def add_annotation(self, x: float, y: float, text: Text) -> None:
        """ Add a Text annotation at the given coordinate """

        self.annotations.append(PlotAnnotation(x, y, text))

    def render_annotations(self, text_lines: list(str)) -> None:
        """ Renders text annotations to the list of strings rendered from the canvas """

        if len(self.annotations) == 0:
            return
        
        # Account for frame and padding
        xscale = self.plot_width / (self.x_max - self.x_min)
        yscale = self.plot_height / (self.y_max - self.y_min)

        x_min = int(self.x_min * xscale)
        x_max = int(self.x_max * xscale)
        y_min = int(self.y_min * yscale)
        y_max = int(self.y_max * yscale)

        # Loop for all annotations
        for a in self.annotations:
            x = int(a.x * xscale / 2)
            y = len(text_lines) - int((a.y * yscale - y_min) / 4) - 1

            # Find the 'x' location within the 'y' string
            if y>= 0 and y < len(text_lines):
                text_len = 0
                s = text_lines[y]
                in_attr = False
                for idx in range(len(s)):
                    if s[idx] == '[':
                        in_attr = True
                    elif in_attr:
                        if s[idx] == ']':
                            in_attr = False
                    else:
                        # Test if we found the insertion point
                        if text_len == x:
                            break
                        text_len += 1

                # Insert the text at 'idx' within the string
                if isinstance(a.text, Text):
                    s = s[:idx] + f"[{a.text.style.color.name}]" + str(a.text) + s[idx+len(a.text):]
                else:
                    s = s[:idx] + f"[white]" + str(a.text) + s[idx+len(a.text):]
                text_lines[y] = s

