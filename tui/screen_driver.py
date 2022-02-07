from __future__ import annotations

import asyncio
import os
#from codecs import getincrementaldecoder
import selectors
import sys
from time import time
from typing import Any, TYPE_CHECKING
from threading import Event, Thread

from rich.console import Console

from textual import events
from textual._types import MessageTarget
from textual._xterm_parser import XTermParser
from textual._linux_driver import LinuxDriver


class ScreenDriver(LinuxDriver):
    def __init__(self, console: "Console", target: "MessageTarget") -> None:
        super().__init__(console, target)
        # Mouse event mapping dict
        self.mouse_code = { 0x43:35, 32:0, 33:1, 34:2, 0x60:64, 0x61:65, 0x40:32, 0x41:33, 0x42:34}
        self.last_mouse_press = 0

    def _convert_to_xterm(self, data):
        ret = ''
        while len(data) >= 6:
            # Test for mouse code
            if data[0] == 0x1b and data[1] == 0x5b and data[2] == 0x4d:
                # Convert the x/y coordinates
                x = data[4] - 32
                y = data[5] - 32
                
                # Convert the actual code
                ending = 'M'
                if data[3] == 0x23:
                  mouse_code = self.last_mouse_press
                  ending = 'm'
                else:
                  mouse_code = self.mouse_code[data[3]]
                if mouse_code < 3:
                  self.last_mouse_press = mouse_code
        
                ret += f'\x1b[<{mouse_code};{x};{y}{ending}'
                data = data[6:]
            else:
              ret += f'{chr(data[0])}'
              data = data[1:]
            
        if len(data) > 0:
            ret += data.decode()
        return ret

    def _run_input_thread(self, loop) -> None:

        selector = selectors.DefaultSelector()
        selector.register(self.fileno, selectors.EVENT_READ)

        fileno = self.fileno

        def more_data() -> bool:
            """Check if there is more data to parse."""
            for key, events in selector.select(0.1):
                if events:
                    return True
            return False

        parser = XTermParser(self._target, more_data)
        read = os.read

        try:
            while not self.exit_event.is_set():
                selector_events = selector.select(0.1)
                for _selector_key, mask in selector_events:
                    if mask | selectors.EVENT_READ:
                        data = read(fileno, 1024)
                        # Convert GNU 'screen' mouse events to XTerm mouse events
                        unicode_data = self._convert_to_xterm(data)
                        for event in parser.feed(unicode_data):
                            self.process_event(event)

        except Exception:
            pass
            # TODO: log
        finally:
            selector.close()

if __name__ == "__main__":
    from time import sleep
    from rich.console import Console
    from . import events

    console = Console()

    from .app import App

    class MyApp(App):
        async def on_mount(self, event: events.Mount) -> None:
            self.set_timer(5, callback=self.close_messages)

    MyApp.run()
  
