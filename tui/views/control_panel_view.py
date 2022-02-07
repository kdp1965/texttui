
from tui.layouts.control_panel_layout import ControlPanelLayout
from textual.view import View

from tui import RowHeightUpdate

class ControlPanelView(View, layout=ControlPanelLayout):
    @property
    def grid(self) -> ControlPanelLayout:
        assert isinstance(self.layout, ControlPanelLayout)
        return self.layout

    async def handle_row_height_update(self, message: RowHeightUpdate) -> None:
        """A message sent by a widget when the render height changes"""

        row = message.row
        height = message.new_height

        self.grid.row_update_size(row, height)
        self.grid.require_update()

