"""Deterministic grid placer + 2-layer maze router (Phase B MVP)."""

from __future__ import annotations

import heapq
from collections import defaultdict

from pcb_ai_circuit_ir.models import Design, EvidenceRef, Finding, Operation, RiskTier, Severity
from pcb_ai_pcb_ir.models import Board, FootprintInstance, Layer, Point, Track, Via


GRID_MM = 0.5
TRACK_WIDTH = 0.25
CLEARANCE = 0.2
MARGIN = 2.0


class GridLayoutBackend:
    """Place footprints in a grid, then A* route nets on F.Cu / B.Cu."""

    def __init__(
        self,
        *,
        grid_mm: float = GRID_MM,
        max_route_expansions: int = 50_000,
        repair_passes: int = 2,
    ) -> None:
        self.grid_mm = grid_mm
        self.max_route_expansions = max_route_expansions
        self.repair_passes = repair_passes

    def layout(self, design: Design, board: Board) -> Board:
        result = board.model_copy(deep=True)
        result.operations = list(result.operations)
        result.findings = list(result.findings)
        result.tracks = []
        result.vias = []
        result.unrouted_nets = []

        self._place(result)
        for _ in range(self.repair_passes + 1):
            result.tracks = []
            result.vias = []
            result.unrouted_nets = []
            self._route(result)
            clearance = self._clearance_findings(result)
            if not clearance:
                break
            result.findings.extend(clearance)
            self._nudge_for_repair(result)

        result.attributes["layout_backend"] = "grid_mvp"
        result.attributes["design_id"] = design.id
        return result

    def _place(self, board: Board) -> None:
        fps = sorted(board.footprints, key=lambda f: f.reference)
        # Power-ish refs near left edge; others row-major.
        powerish = [f for f in fps if f.reference[0] in {"U", "J"} or "REG" in (f.value or "").upper()]
        others = [f for f in fps if f not in powerish]
        ordered = powerish + others
        if not ordered:
            return

        ox = board.outline.origin.x + MARGIN
        oy = board.outline.origin.y + MARGIN
        max_x = board.outline.origin.x + board.outline.width - MARGIN
        x, y = ox, oy
        row_h = 0.0
        for fp in ordered:
            w = fp.courtyard_width
            h = fp.courtyard_height
            if x + w > max_x:
                x = ox
                y += row_h + MARGIN
                row_h = 0.0
            fp.placement.x = round(x + w / 2, 3)
            fp.placement.y = round(y + h / 2, 3)
            fp.placement.placed = True
            board.operations.append(
                Operation(
                    type="place_footprint",
                    target=fp.reference,
                    payload={"x": fp.placement.x, "y": fp.placement.y, "rotation_deg": 0.0},
                    risk_tier=RiskTier.LOW,
                    confidence=1.0,
                )
            )
            x += w + MARGIN
            row_h = max(row_h, h)

    def _pad_abs(self, fp: FootprintInstance, pad_number: str) -> Point | None:
        for pad in fp.pads:
            if pad.number == pad_number:
                return Point(x=fp.placement.x + pad.x, y=fp.placement.y + pad.y)
        if fp.pads:
            pad = fp.pads[0]
            return Point(x=fp.placement.x + pad.x, y=fp.placement.y + pad.y)
        return Point(x=fp.placement.x, y=fp.placement.y)

    def _net_terminals(self, board: Board) -> dict[str, list[Point]]:
        by_net: dict[str, list[Point]] = defaultdict(list)
        for fp in board.footprints:
            for pad in fp.pads:
                if pad.net_name:
                    pt = self._pad_abs(fp, pad.number)
                    if pt is not None:
                        by_net[pad.net_name].append(pt)
        return by_net

    def _route(self, board: Board) -> None:
        terminals = self._net_terminals(board)
        occupied: set[tuple[int, int, int]] = set()  # gx, gy, layer_idx

        # Block footprint courtyards lightly on F.Cu.
        for fp in board.footprints:
            self._mark_courtyard(fp, occupied, layer_idx=0)

        for net_name, points in sorted(terminals.items()):
            if len(points) < 2:
                continue
            # Connect as a chain: p0-p1, p1-p2, ...
            ok = True
            for a, b in zip(points, points[1:]):
                path = self._astar(a, b, occupied)
                if path is None:
                    ok = False
                    break
                self._commit_path(board, net_name, path, occupied)
            if not ok:
                board.unrouted_nets.append(net_name)
                board.findings.append(
                    Finding(
                        rule_id="layout.unrouted_net",
                        severity=Severity.WARNING,
                        objects=[net_name],
                        explanation=f"MVP router could not fully route net {net_name!r}.",
                        evidence_refs=[
                            EvidenceRef(
                                id="rule:layout.unrouted_net",
                                kind="rule",
                                title="Unrouted net",
                            )
                        ],
                        source="layout",
                    )
                )

    def _mark_courtyard(
        self, fp: FootprintInstance, occupied: set[tuple[int, int, int]], *, layer_idx: int
    ) -> None:
        g = self.grid_mm
        half_w = fp.courtyard_width / 2
        half_h = fp.courtyard_height / 2
        x0 = int((fp.placement.x - half_w) / g)
        x1 = int((fp.placement.x + half_w) / g)
        y0 = int((fp.placement.y - half_h) / g)
        y1 = int((fp.placement.y + half_h) / g)
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                # Leave center open so pads remain routable.
                if abs(gx - int(fp.placement.x / g)) <= 1 and abs(gy - int(fp.placement.y / g)) <= 1:
                    continue
                occupied.add((gx, gy, layer_idx))

    def _to_grid(self, p: Point) -> tuple[int, int]:
        return int(round(p.x / self.grid_mm)), int(round(p.y / self.grid_mm))

    def _from_grid(self, gx: int, gy: int) -> Point:
        return Point(x=gx * self.grid_mm, y=gy * self.grid_mm)

    def _astar(
        self,
        start: Point,
        goal: Point,
        occupied: set[tuple[int, int, int]],
    ) -> list[tuple[int, int, int]] | None:
        """Return path as list of (gx, gy, layer) including start and goal."""
        s = (*self._to_grid(start), 0)
        g = (*self._to_grid(goal), 0)
        if s[0:2] == g[0:2]:
            return [s]

        def h(n: tuple[int, int, int]) -> float:
            return abs(n[0] - g[0]) + abs(n[1] - g[1]) + abs(n[2] - g[2]) * 2

        open_heap: list[tuple[float, int, tuple[int, int, int]]] = []
        counter = 0
        heapq.heappush(open_heap, (h(s), counter, s))
        came: dict[tuple[int, int, int], tuple[int, int, int] | None] = {s: None}
        gscore: dict[tuple[int, int, int], float] = {s: 0.0}
        expansions = 0

        while open_heap and expansions < self.max_route_expansions:
            _, _, current = heapq.heappop(open_heap)
            expansions += 1
            if current[0] == g[0] and current[1] == g[1]:
                # Prefer ending on same layer as goal (0).
                path = [current]
                while came[path[-1]] is not None:
                    path.append(came[path[-1]])  # type: ignore[arg-type]
                path.reverse()
                return path

            cx, cy, cl = current
            neighbors: list[tuple[int, int, int]] = [
                (cx + 1, cy, cl),
                (cx - 1, cy, cl),
                (cx, cy + 1, cl),
                (cx, cy - 1, cl),
            ]
            # Via to other layer.
            neighbors.append((cx, cy, 1 - cl))

            for nb in neighbors:
                if nb in occupied and not (nb[0] == g[0] and nb[1] == g[1]):
                    continue
                step = 1.0 if nb[2] == cl else 3.0  # via cost
                tentative = gscore[current] + step
                if tentative < gscore.get(nb, 1e18):
                    came[nb] = current
                    gscore[nb] = tentative
                    counter += 1
                    heapq.heappush(open_heap, (tentative + h(nb), counter, nb))
        return None

    def _commit_path(
        self,
        board: Board,
        net_name: str,
        path: list[tuple[int, int, int]],
        occupied: set[tuple[int, int, int]],
    ) -> None:
        for node in path:
            occupied.add(node)
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            if a[2] != b[2]:
                # Via
                pt = self._from_grid(a[0], a[1])
                board.vias.append(Via(net_name=net_name, at=pt))
                board.operations.append(
                    Operation(
                        type="add_via",
                        target=net_name,
                        payload={"x": pt.x, "y": pt.y},
                        risk_tier=RiskTier.MEDIUM,
                        confidence=1.0,
                    )
                )
                continue
            layer = Layer.F_CU if a[2] == 0 else Layer.B_CU
            start = self._from_grid(a[0], a[1])
            end = self._from_grid(b[0], b[1])
            board.tracks.append(
                Track(net_name=net_name, layer=layer, start=start, end=end, width=TRACK_WIDTH)
            )
            board.operations.append(
                Operation(
                    type="add_track",
                    target=net_name,
                    payload={
                        "layer": layer.value,
                        "x1": start.x,
                        "y1": start.y,
                        "x2": end.x,
                        "y2": end.y,
                        "width": TRACK_WIDTH,
                    },
                    risk_tier=RiskTier.MEDIUM,
                    confidence=1.0,
                )
            )

    def _clearance_findings(self, board: Board) -> list[Finding]:
        """Cheap MVP clearance check between footprint centers."""
        findings: list[Finding] = []
        fps = [f for f in board.footprints if f.placement.placed]
        for i, a in enumerate(fps):
            for b in fps[i + 1 :]:
                dx = a.placement.x - b.placement.x
                dy = a.placement.y - b.placement.y
                dist = (dx * dx + dy * dy) ** 0.5
                min_dist = (a.courtyard_width + b.courtyard_width) / 2 + CLEARANCE
                if dist < min_dist:
                    findings.append(
                        Finding(
                            rule_id="drc.courtyard_overlap",
                            severity=Severity.ERROR,
                            objects=[a.reference, b.reference],
                            explanation=(
                                f"Courtyards of {a.reference} and {b.reference} "
                                f"appear closer than {min_dist:.2f} mm."
                            ),
                            source="layout_drc",
                        )
                    )
        return findings

    def _nudge_for_repair(self, board: Board) -> None:
        """Spread footprints slightly when clearance fails."""
        for i, fp in enumerate(sorted(board.footprints, key=lambda f: f.reference)):
            if not fp.placement.placed:
                continue
            fp.placement.x += (i % 3) * 0.5
            fp.placement.y += (i % 2) * 0.5
            board.operations.append(
                Operation(
                    type="move_footprint",
                    target=fp.reference,
                    payload={"x": fp.placement.x, "y": fp.placement.y},
                    risk_tier=RiskTier.LOW,
                    confidence=0.8,
                )
            )
