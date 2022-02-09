from __future__ import annotations

import os
import sys

import rich
import rich.repr
import io
import math
from contextlib import redirect_stdout
from rich import box
from rich import print
from rich.console import RenderableType
from rich.console import Group
from rich.screen import Screen
from rich.control import Control
from rich.style import Style
from rich import inspect
from rich import get_console
from rich.protocol import is_renderable

from rich.syntax import Syntax
from rich.traceback import Traceback
from rich.text import Text
from rich.panel import Panel
from rich.pretty import Pretty
from rich.align import Align
from rich.table import Table
from rich.columns import Columns
from rich.box import DOUBLE

from textual.app import App
from textual.widgets import Header, Footer, FileClick, ScrollView, DirectoryTree, Static, Placeholder
from textual.views import GridView, WindowView
from textual.layouts.grid import GridLayout
from textual._timer import Timer

from textual.widgets import Button, ButtonPressed
from textual.widget import Reactive, Widget

from textual_inputs import TextInput

# Custom control import
from tui import Checkbutton, Radiobutton, RadioGroup, Droplist, ListCollapse, CliInput, HoverButton, Label
from tui import RowHeightUpdate, Tabs, Dynamic, DynamicTable, TuiPlot, PlotAxis
from tui.widgets.fixed_title_textinput import FixedTitleTextInput
from tui.views.control_panel_view import ControlPanelView
from tui.screen_driver import ScreenDriver
from tui.widgets.dynamic import RenderableUpdate

class TimePlot(TuiPlot):
    def render_canvas(self) -> None:
        """ Draws the a simple sine wave to the bare canvas """

        self.push_line_color("bright_yellow")
        lastx = 0
        lasty = math.sin(0) + 0.5
        for x in range(4, self.width*2, 4):
            xf = x / (self.width*2)
            waves = 3
            y = math.sin(xf * waves * 2 * math.pi) / 2 + .5
            if xf != lastx:
                self.draw_line(lastx, lasty, xf, y)
                lastx = xf
                lasty = y
        self.pop_line_color()

class FftPlot(TuiPlot):
    def __init__(
        self,
        style: StyleType = "white on black",
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ):
        """ Initialize an FFT graph with FFT data from a file """
        super().__init__(style, name, width, height, border=False)

        self.f_list = []
        with open("fft_data/fft1.txt", "r") as file1:
            self.f_list.append([float(line) for line in file1][8:])
        with open("fft_data/fft2.txt", "r") as file1:
            self.f_list.append([float(line) for line in file1][8:])
        with open("fft_data/fft3.txt", "r") as file1:
            self.f_list.append([float(line) for line in file1][8:])
        with open("fft_data/fft4.txt", "r") as file1:
            self.f_list.append([float(line) for line in file1][8:])
        self.which_fft = 0

        self._timer = None
        self.add_x_label(Text("Frequency (GHz)",style=Style(color="blue")))
        self.add_x_axis(PlotAxis(0, 8, 9, ".2f"), style=Style(color="navajo_white1"))
        self.add_y_label(Text("Amplitude / dBM",style=Style(color="yellow")))
        self.add_y_axis(PlotAxis(0, -120, 7, ".0f"), style=Style(color="navajo_white1"))
        self.add_annotation(560, -10, Text("ENOB: 8.2",style=Style(color="bright_yellow")))
        self.add_annotation(560, -15, Text("SNR:  48.7",style=Style(color="bright_yellow")))
        self.add_title(Text("ADC 1 - 12 Bit",style=Style(color="bright_blue")))

    def render_canvas(self) -> None:
        if self._timer is None:
            frames_per_second = 4
            self._timer = Timer(
                self._parent,
                1 / frames_per_second,
                self._parent,
                name="Animator",
                callback=self,
                pause=True,
            )
            self._timer.start()

        """ Draws the FFT to the bare canvas """

        fft = self.f_list[self.which_fft]

        # Set the graph X and Y extents
        self.set_y_extents(-120, 0)
        self.set_x_extents(0, len(fft))

        #self.push_line_color("grey74")
        self.push_line_color("grey50")
        lastx = 0
        lasty = fft[0]
        x = 0
        harmonic_bins = [860, 1290, 1760]
        spur_bins = [610, 1040, 1160]
        signal_bin = 420
        pop_bins = [460]
        pop_bins.extend([b+35 for b in harmonic_bins])
        pop_bins.extend([b+35 for b in spur_bins])
        for f in fft:
            if x == 420:
                self.push_line_color("bright_green")
            elif x in pop_bins:
                self.pop_line_color()
            elif x in harmonic_bins:
                self.push_line_color("bright_blue")
            elif x in spur_bins:
                self.push_line_color("bright_red")

            self.draw_line(lastx, lasty, x, f)
            lastx = x
            lasty = f
            x += 1

        self.pop_line_color()

    async def __call__(self) -> None:
        if self._timer is not None:
            if self.which_fft == 3:
                self.which_fft = 0
            else:
                self.which_fft += 1
            await self._parent.post_message(RenderableUpdate(self))
            self._timer.start()

class SampleAppHeader(Header):
    def render(self) -> RenderableType:
        """ Create a custom header with cool emojis """

        header_table = Table.grid(padding=(0, 1), expand=True)
        header_table.style = self.style
        header_table.add_column(justify="left", ratio=0, width=8)
        header_table.add_column("title", justify="center", ratio=1)
        header_table.add_column("clock", justify="right", width=8)
        header_table.add_row(
            "❄🔥", self.full_title, self.get_clock() if self.clock else ""
        )
        header: RenderableType
        header = Panel(header_table, style=self.style) if self.tall else header_table
        return header

class Controls(ControlPanelView, can_focus=True):
    """Controls for Sample TUI."""

    def on_mount(self) -> None:
        """Event when widget is first mounted (added to a parent view)."""

        # Create drop lists
        self.drop_radiocolors = Droplist(
            "radiocolors", 
            "blue,red,white,yellow",
            select="blue",
            max_height=9)
        self.drop_radiotype = Droplist(
            "radiotype",
            "large,small,ascii,pointer",
            select="large",
            max_height=5)

        self.drop_checktype = Droplist(
            "checktype",
            "large,medium,small,cross,ascii",
            select="large",
            max_height=6)

        # Create example controls
        radio_type = "large"
        radio_color = "blue"
        checkbox_type = "large"

        self.samp_radio_group = RadioGroup("Option 1,Option 2,Option 3", indent=2,radiotype=radio_type, radiocolor=radio_color)
        self.samp_radio = {
            'option_1' : self.samp_radio_group.get_button('option_1'),
            'option_2' : self.samp_radio_group.get_button('option_2'),
            'option_3' : self.samp_radio_group.get_button('option_3'),
        }
        self.samp_radio['option_1'].selected = True
        self.samp_retain = Checkbutton("Retain", indent=2, checktype=checkbox_type )

        self.edit1 = FixedTitleTextInput(title="Edit 1", value="-20")
        self.edit2 = FixedTitleTextInput(title="Edit 2", value="100")
        self.edit3 = FixedTitleTextInput(title="Edit 3", value="20")
        self.edit4 = FixedTitleTextInput(title="Edit 4", value="8")

        # Create checkbox controls
        self.checks = {}
        self.checks['chk1'] = Checkbutton("Check 1", indent=2, checktype=checkbox_type )
        self.checks['chk2'] = Checkbutton("Check 2", indent=2, checktype=checkbox_type )
        self.checks['chk3'] = Checkbutton("Check 3", indent=2, checktype=checkbox_type )
        self.checks['chk4'] = Checkbutton("Check 4", indent=2, checktype=checkbox_type )
        self.checks['chk1'].checked = True
        self.pause_on_error = Checkbutton("Pause on error", indent=1, top_margin=1, checktype=checkbox_type )

        # Reset and start/stop buttons
        self.reset_enable = Checkbutton("Enable reset", name="enable_reset", indent=1, checktype=checkbox_type )
        self.reset_button = HoverButton("Reset", width=7, style="white on red", visible=False, indent=4)
        self.start_stop   = HoverButton("Start", name='start', width=7, indent = 4)
        self.pause_button = HoverButton("Pause", name='pause', visible=False, indent = 4)
        self.running = False
        self.paused = False
        self.status_label = Label("")

        # Create the control panel header labels
        HEADER = "white on dark_sea_green4"
        control_panel_label = Label("Control Panel", style=HEADER, align="center")
        self.panel = [
                # The top label that spans both columns.  NOTE: Column spans can be added seperately also (see below)
            {'row': "name='title',size=1,spacer=1,span='col1|col2'", 'controls' : [ control_panel_label ] },

            # Actual controls
            {'row': "name='rtype',size=1,spacer=1",          'controls' : [ Label("Radio Type"),          self.drop_radiotype ]          },

            {'row': "name='rcolor',size=1,spacer=1",         'controls' : [ Label("Radio Color"),         self.drop_radiocolors ]        },

            {'row': "name='order',size=1,spacer=1",          'controls' : [ Label("Check Type"),          self.drop_checktype ]          },

            {'row': "name='ctrl1',size=1,repeat=5,spacer=1", 'controls' : [ Label("Sample Radio"),        Label("Sample Checkbox") ]     },
            {                                                'controls' : [ self.samp_radio['option_1'],  self.checks['chk1'] ]          },
            {                                                'controls' : [ self.samp_radio['option_2'],  self.checks['chk2'] ]          },
            {                                                'controls' : [ self.samp_radio['option_3'],  self.checks['chk3'] ]          },
            {                                                'controls' : [ Label(""),                    self.checks['chk4'] ]          },

            {'row': "name='edit',size=3,repeat=2,spacer=1",  'controls' : [ self.edit1,                   self.edit2 ]                   },
            {                                                'controls' : [ self.edit3,                   self.pause_on_error ]          },
                                                                
            {'row': "name='reset',size=1,spacer=1",          'controls' : [ self.reset_enable,            self.reset_button ]            },
                                                                
            {'row': "name='run1',size=1,spacer=2",           'controls' : [ self.start_stop,              self.pause_button ]            },

            {'row': "name='status',size=1",                  'controls' : [ self.status_label ]                                          },
        ]

        # Create columns and rows
        self.grid.add_column("col1", max_size=17)
        self.grid.add_column("col2", max_size=32)
        self.grid.set_gutter(1)

        # This is an alternate way of adding column spans if not in-line above
#        self.grid.add_col_spans(
#            clear="col1-start|col2-end,title",
#        )
        
        # Add rows and controls to the control panel grid
        for r in self.panel:
            if 'row' in r:
                eval(f'self.grid.add_row({r["row"]})')
            self.grid.place(*r['controls'])

    async def handle_button_pressed(self, message: ButtonPressed) -> None:
        """A message sent by the button widget"""

        global ctrl_table

        assert isinstance(message.sender, Button)
        button_name = message.sender.name

        if button_name == 'radiotype':
            radiotype = self.drop_radiotype.selected
            for r in self.samp_radio:
                self.samp_radio[r].radiotype = radiotype

            # Update the table in the Controls tab
            await ctrl_table.update_row(
                0,
                *[None, self.drop_radiotype.selected,
                Radiobutton("Modified",radiotype=radiotype,radiocolor="blue",selected=True)]
            )

        elif button_name == 'radiocolors':
            color = self.drop_radiocolors.selected
            for r in self.samp_radio:
                self.samp_radio[r].radiocolor = color

            # Update the table in the Controls tab
            await ctrl_table.update_row(
                1,
                *[None, self.drop_radiocolors.selected,
                Radiobutton("Modified",radiotype="large",radiocolor=color,selected=True)]
            )

        if button_name == 'checktype':
            checktype = self.drop_checktype.selected
            for r in self.checks:
                self.checks[r].checktype = checktype
            self.pause_on_error.checktype = checktype
            self.reset_enable.checktype = checktype

            # Update the table in the Controls tab
            await ctrl_table.update_row(
                2,
                *[None, self.drop_checktype.selected,
                Checkbutton("Modified",checktype=checktype,checked=True)]
            )

        elif button_name == 'start':
            if not self.running:
                self.running = True
                self.start_stop.label = "Stop"
                self.status_label.label = "Running sweep..."
                self.pause_button.visible = True
            else:      
                self.running = False
                self.paused = False
                self.start_stop.label = "Start"
                self.pause_button.label = "Pause"
                self.status_label.label = ""
                self.pause_button.visible = False
        elif button_name == 'pause':
            if self.running:
                if self.paused:
                    self.paused = False
                    self.pause_button.label = "Pause"
                    self.status_label.label = "Running sweep..."
                else:
                    self.paused = True
                    self.pause_button.label = "Resume"
                    self.status_label.label = "Sweep paused"
        elif button_name == "enable_reset":
            if self.reset_enable.checked:
                self.reset_button.visible = True
            else:
                self.reset_button.visible = False

# ========================================================================
# This is a super simple CLI command processor that somewhat mimics
# the Python REPL
# ========================================================================
async def process_command(command, width) -> str:
    """Process a command from the CliInput"""

    global tabs

    console_width = get_console().width
    get_console().width = width - 4

    # Test if assigning a variable
    process_command_var = ''
    process_command_expression = ''
    for xxxxx1 in range(len(command)):
        if command[xxxxx1] == '=':
            # Process the command as an assignment
            process_command_var=command[:xxxxx1].strip()
            process_command_expression = command[xxxxx1+1:].strip()

            # Add command to our history window
            hist_cmd = command.replace('"[', '"\\[').replace("'[","'\\[")
            cmd = "\n" + hist_cmd
            if not tabs.has_tab("history"):
                tabs.add_tab("history", "Command History", True)
                tabs.select_tab("history")
            tabs.add_renderable("history", cmd, False)
            
            try:
                f = io.StringIO()
                with redirect_stdout(f):
                    globals()[process_command_var] = eval(process_command_expression)
                return
            except Exception as e:
                resp = 'ERROR: ' + str(e)
                break
        elif command[xxxxx1] == '(' or command[xxxxx1] == '"':
            break

    if process_command_var == '':
        try:
            f = io.StringIO()
            with redirect_stdout(f):
                eval(command)
            resp = f.getvalue()[:-1]
        except Exception as e:
            resp = 'ERROR: ' + str(e)

    get_console().width = console_width

    # Add command to our history window
    hist_cmd = command.replace('"[', '"\\[').replace("'[","'\\[")
    cmd = "\n" + hist_cmd+"\n" + resp
    if not tabs.has_tab("history"):
        tabs.add_tab("history", "Command History", True)
        tabs.select_tab("history")
    tabs.add_renderable("history", cmd, False)

    return resp

class MyApp(App):
    """Override of Textual App refresh to work with Linux 'screen' program"""

    def refresh(self, repaint: bool = True, layout: bool = False) -> None:
        sync_available = os.environ.get("TERM_PROGRAM", "") != "Apple_Terminal"
        if not self._closed:
            console = self.console
            try:
                if sync_available:
                    console.file.write("\x1bP=1s\x1b\\")
                console.print(Screen(Control.home(), self.view, Control.home()))

                # Disable these two lines for screen
                # if sync_available:
                #     console.file.write("\x1bP=2s\x1b\\")
                console.file.flush()
            except Exception:
                self.panic()

    async def on_load(self) -> None:
        """Sent before going in to application mode."""

        # Bind our basic keys
        await self.bind("b", "view.toggle('controls')", "Toggle controls")
        await self.bind("ctrl+d", "quit", "Quit")

        # Get path to show
        try:
            self.path = sys.argv[1]
        except IndexError:
            self.path = os.path.abspath(
                os.path.join(os.path.basename(__file__), "../../")
            )

    async def on_mount(self) -> None:
        """Call after terminal goes in to application mode"""

        global cmdHistory
        global cmdText
        global tabs
        global ctrl_table
        cli_height = 10

        # Create our tabs
        self.body = Tabs(border_style=Style(color="blue"), border_focus_style=Style(color="green"))
        tabs = self.body
        self.body.add_tab("history", "Command History", True)
        self.body.add_tab("controls", "Controls")
        self.body.add_tab("graph", "Time Plot")
        self.body.add_tab("fft", "FFT Plot")

        # Add content to the command history tab
        cmdText = "[yellow]Command History\n\n[white]This is an example of a Dynamic Widget that displays text which can be changed dynamically."
        cmdHistory = Dynamic(cmdText,name="history")
        self.body.add_renderable("history", cmdHistory, True)

        # Add content to the controls tab
        self.ctrl_table = DynamicTable("controls")
        ctrl_table = self.ctrl_table
        self.ctrl_table.add_column("Control")
        self.ctrl_table.add_column("Value")
        self.ctrl_table.add_column("Sample")
        self.ctrl_table.add_row(*["Radio Type", "large", Radiobutton("Example",radiotype="large",selected=True)])
        self.ctrl_table.add_row(*["Radio Color", "blue", Radiobutton("Example",radiotype="large",radiocolor="blue",selected=True)])
        self.ctrl_table.add_row(*["Check Type", "large", Checkbutton("Example",checktype="large",checked=True)])
        self.body.add_renderable("controls", Dynamic('Below is a "DynamicTable" that updates when the Droplist controls (left) update.\n',name="table"))
        self.body.add_renderable("controls", self.ctrl_table)

        self.body.add_renderable("graph", Dynamic("Time Domain Plot",name="time"))
        self.body.add_renderable("graph", TimePlot(name="graph",style=Style(color="grey63")))
        self.body.add_renderable("fft", FftPlot(name="fft",style=Style(color="grey63")))

        # Create the bottom Command Line Interface (CLI) and the control panel
        self.cmd = CliInput(process_command, name="cli", title="Command Window", height=cli_height)
        self.controls = Controls(name='Control Panel')

        # Dock our widgets
        await self.view.dock(SampleAppHeader(), edge="top")
        await self.view.dock(Footer(), edge="bottom")
        await self.view.dock(self.cmd, edge="bottom", size=cli_height, name="cmd")

        # Note the directory is also in a scroll view
        await self.view.dock(self.controls, edge="left", size=40, name="controls")
        await self.view.dock(self.body, edge="top")

if __name__ == "__main__":
    # Run our app class
    app = MyApp(driver_class=ScreenDriver)
    app.run(title="Sample TUI",driver=ScreenDriver)

