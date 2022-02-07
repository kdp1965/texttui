from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from operator import itemgetter
from logging import getLogger
from itertools import cycle, product
import sys
from typing import Iterable, NamedTuple

from rich.console import Console

from textual._layout_resolve import layout_resolve
from textual.geometry import Size, Offset, Region
from textual.layout import Layout, WidgetPlacement
from textual.layout_map import LayoutMap
from textual.widget import Widget
from textual.layouts.grid import GridLayout, GridOptions, GridArea, GridAlign

from tui import RowHeightUpdate

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

class ControlPanelLayout(GridLayout):
    def __init__(
        self,
        gap: tuple[int, int] | int | None = None,
        gutter: tuple[int, int] | int | None = None,
        align: tuple[GridAlign, GridAlign] | None = None,
    ) -> None:
        super().__init__(gap, gutter, align)
        self.spacer_count = 0
        self.col_spans = {}

    def row_update_max_size(self, row: str, max_size):
        for r in self.rows:
            if r.name == row:
                r.max_size = max_size
                break
        else:
            raise ValueError(f'{row} not found in {self.rows}')
            sys.exit() 
        self.require_update()

    def row_update_size(self, row: str, size):
        for r in self.rows:
            if r.name == row:
                r.size = size
                r.max_size = size
                break
        else:
            raise ValueError(f'{row} not found in {self.rows}')
            sys.exit() 
        self.require_update()

    def _add_col_span(
        self, name: str, columns: str | tuple[str, str], rows: str | tuple[str, str]
    ) -> None:
        if isinstance(columns, str):
            column_start = f"{columns}-start"
            column_end = f"{columns}-end"
        else:
            column_start, column_end = columns

        if isinstance(rows, str):
            row_start = f"{rows}-start"
            row_end = f"{rows}-end"
        else:
            row_start, row_end = rows

        self.col_spans[name] = GridArea(column_start, column_end, row_start, row_end)

    def add_col_spans(self, **spans: str) -> None:
        for name, span in spans.items():
            span = span.replace(" ", "")
            column, _, row = span.partition(",")

            column_start, column_sep, column_end = column.partition("|")
            row_start, row_sep, row_end = row.partition("|")

            self._add_col_span(
                name,
                (column_start, column_end) if column_sep else column,
                (row_start, row_end) if row_sep else row,
            )
        self.require_update()

    def add_row(
        self,
        name: str,
        *,
        size: int | None = None,
        fraction: int = 1,
        min_size: int = 1,
        max_size: int | None = None,
        repeat: int = 1,
        spacer: int = 0,
        span: str | None = None,
    ) -> None:
        super().add_row(name, size=size, fraction=fraction, min_size=min_size, max_size=max_size, repeat=repeat)

        # Test for spacer row after the widget row
        if spacer:
            super().add_row(f'spacer{self.spacer_count}',size=spacer)
            self.spacer_count += 1
        if span is not None:
            columns = span.split('|')
            if len(columns) == 2:
                self.add_col_spans(
                    **{name:f"{columns[0]}-start|{columns[1]}-end,{name}"},
                )

    def arrange(self, size: Size, scroll: Offset) -> Iterable[WidgetPlacement]:
        """Generate a map that associates widgets with their location on screen.

        Args:
            width (int): [description]
            height (int): [description]
            offset (Point, optional): [description]. Defaults to Point(0, 0).

        Returns:
            dict[Widget, OrderedRegion]: [description]
        """
        width, height = size

        def resolve(
            size: int, edges: list[GridOptions], gap: int, repeat: bool
        ) -> Iterable[tuple[int, int]]:
            total_gap = gap * (len(edges) - 1)
            tracks: Iterable[int]
            tracks = [
                track if edge.max_size is None else min(edge.max_size, track)
                for track, edge in zip(layout_resolve(size - total_gap, edges), edges)
            ]
            if repeat:
                tracks = cycle(tracks)
            total = 0
            edge_count = len(edges)
            for index, track in enumerate(tracks):
                if total + track >= size and index >= edge_count:
                    break
                yield total, total + track
                total += track + gap

        def resolve_tracks(
            grid: list[GridOptions], size: int, gap: int, repeat: bool
        ) -> tuple[list[str], dict[str, tuple[int, int]], int, int]:
            spans = [
                (options.name, span)
                for options, span in zip(cycle(grid), resolve(size, grid, gap, repeat))
            ]

            max_size = 0
            tracks: dict[str, tuple[int, int]] = {}
            counts: dict[str, int] = defaultdict(int)
            if repeat:
                names = []
                for index, (name, (start, end)) in enumerate(spans):
                    max_size = max(max_size, end)
                    counts[name] += 1
                    count = counts[name]
                    names.append(f"{name}-{count}")
                    tracks[f"{name}-{count}-start"] = (index, start)
                    tracks[f"{name}-{count}-end"] = (index, end)
            else:
                names = [name for name, _span in spans]
                for index, (name, (start, end)) in enumerate(spans):
                    max_size = max(max_size, end)
                    tracks[f"{name}-start"] = (index, start)
                    tracks[f"{name}-end"] = (index, end)

            return names, tracks, len(spans), max_size

        container = Size(width - self.column_gutter * 2, height - self.row_gutter * 2)
        column_names, column_tracks, column_count, column_size = resolve_tracks(
            [
                options
                for options in self.columns
                if options.name not in self.hidden_columns
            ],
            container.width,
            self.column_gap,
            self.column_repeat,
        )
        row_names, row_tracks, row_count, row_size = resolve_tracks(
            [options for options in self.rows if options.name not in self.hidden_rows],
            container.height,
            self.row_gap,
            self.row_repeat,
        )
        grid_size = Size(column_size, row_size)

        widget_areas = (
            (widget, area)
            for widget, area in self.widgets.items()
            if area and widget.visible
        )

        free_slots = {
            (col, row) for col, row in product(range(column_count), range(row_count))
        }
        order = 1
        from_corners = Region.from_corners
        gutter = Offset(self.column_gutter, self.row_gutter)
        for widget, area in widget_areas:
            column_start, column_end, row_start, row_end = self.areas[area]
            try:
                col1, x1 = column_tracks[column_start]
                col2, x2 = column_tracks[column_end]
                row1, y1 = row_tracks[row_start]
                row2, y2 = row_tracks[row_end]
            except (KeyError, IndexError):
                continue

            free_slots.difference_update(
                product(range(col1, col2 + 1), range(row1, row2 + 1))
            )

            region = self._align(
                from_corners(x1, y1, x2, y2),
                grid_size,
                container,
                self.column_align,
                self.row_align,
            )
            yield WidgetPlacement(region + gutter, widget, (0, order))
            order += 1

        # Widgets with no area assigned.
        auto_widgets = (widget for widget, area in self.widgets.items() if area is None)

        # Create array of active rows based on any addes spacer rows
        active_rows = []
        for r in range(row_count):
            if not "spacer" in self.rows[r].name:
                active_rows.append(r)

        # Remove column/rows that are part of a span
        span_slots = {}
        for span in self.col_spans:
            column_start, column_end, row_start, row_end = self.col_spans[span]
            try:
                col1, x1 = column_tracks[column_start]
                col2, x2 = column_tracks[column_end]
                row1, y1 = row_tracks[row_start]
                row2, y2 = row_tracks[row_end]
            except (KeyError, IndexError):
                continue

            span_slots[(col1,row1)] = (column_end, row_end)
            free_slots.difference_update(
                product(range(col1+1, col2 + 1), range(row1, row2 + 1))
            )

        grid_slots = sorted(
            (
                slot
                for slot in product(range(column_count), active_rows)
                if slot in free_slots
            ),
            key=itemgetter(1, 0),  # TODO: other orders
        )

        for widget, (col, row) in zip(auto_widgets, grid_slots):

            col_name = column_names[col]
            row_name = row_names[row]
            _col1, x1 = column_tracks[f"{col_name}-start"]
            _col2, x2 = column_tracks[f"{col_name}-end"]

            _row1, y1 = row_tracks[f"{row_name}-start"]
            _row2, y2 = row_tracks[f"{row_name}-end"]

            if (x1, y1) in span_slots:
                end_col, end_row = span_slots[(x1, y1)]
                _, x2 = column_tracks[f"{end_col}"]

            widget.ctrl_panel_row = self.rows[row].name
            region = self._align(
                from_corners(x1, y1, x2, y2),
                grid_size,
                container,
                self.column_align,
                self.row_align,
            )
            yield WidgetPlacement(region + gutter, widget, (0, order))
            order += 1

        return map

