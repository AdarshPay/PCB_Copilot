"""Geometric connectivity extraction for KiCad schematic sheets."""

from __future__ import annotations

from dataclasses import dataclass, field

Point = tuple[float, float]


def quantize(value: float, *, grid: float = 1e-6) -> float:
    return round(value / grid) * grid


def qpoint(x: float, y: float, *, grid: float = 1e-6) -> Point:
    return (quantize(x, grid=grid), quantize(y, grid=grid))


class UnionFind:
    def __init__(self) -> None:
        self._parent: dict[Point, Point] = {}

    def add(self, p: Point) -> None:
        if p not in self._parent:
            self._parent[p] = p

    def has(self, p: Point) -> bool:
        return p in self._parent

    def find(self, p: Point) -> Point:
        self.add(p)
        while self._parent[p] != p:
            self._parent[p] = self._parent[self._parent[p]]
            p = self._parent[p]
        return p

    def union(self, a: Point, b: Point) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra

    def components(self) -> dict[Point, set[Point]]:
        groups: dict[Point, set[Point]] = {}
        for p in self._parent:
            root = self.find(p)
            groups.setdefault(root, set()).add(p)
        return groups


@dataclass
class PinAttachment:
    component_ref: str
    pin_number: str
    pin_name: str | None
    point: Point
    uuid: str | None = None


@dataclass
class LabelAttachment:
    name: str
    point: Point
    scope: str  # local | global | hierarchical
    uuid: str | None = None


@dataclass
class ConnectivityGraph:
    uf: UnionFind = field(default_factory=UnionFind)
    pins: list[PinAttachment] = field(default_factory=list)
    labels: list[LabelAttachment] = field(default_factory=list)
    wire_uuids: dict[Point, str] = field(default_factory=dict)
    segments: list[tuple[Point, Point]] = field(default_factory=list)

    def add_wire(self, a: Point, b: Point, *, uuid: str | None = None) -> None:
        self.uf.union(a, b)
        if a != b:
            self.segments.append((a, b))
        if uuid:
            self.wire_uuids[a] = uuid
            self.wire_uuids[b] = uuid

    def add_junction(self, p: Point) -> None:
        self.uf.add(p)
        self._snap_to_segments(p)

    def add_pin(self, pin: PinAttachment) -> None:
        self.uf.add(pin.point)
        self._snap_to_segments(pin.point)
        self.pins.append(pin)

    def add_label(self, label: LabelAttachment) -> None:
        self.uf.add(label.point)
        self._snap_to_segments(label.point)
        self.labels.append(label)

    def _snap_to_segments(self, p: Point) -> None:
        """Union `p` with segment endpoints when it lies on a stored segment."""
        for a, b in self.segments:
            if _point_on_segment(p, a, b):
                self.uf.union(p, a)
                self.uf.union(p, b)

    def net_groups(self) -> list[dict]:
        """Return connected components with attached pins and labels."""
        groups = self.uf.components()
        # Index attachments by root
        pin_by_root: dict[Point, list[PinAttachment]] = {}
        for pin in self.pins:
            pin_by_root.setdefault(self.uf.find(pin.point), []).append(pin)
        label_by_root: dict[Point, list[LabelAttachment]] = {}
        for label in self.labels:
            label_by_root.setdefault(self.uf.find(label.point), []).append(label)

        results: list[dict] = []
        seen_roots: set[Point] = set()
        # Prefer roots that have pins or labels (ignore dangling geometry-only).
        candidate_roots = set(pin_by_root) | set(label_by_root)
        for root in candidate_roots:
            if root in seen_roots:
                continue
            seen_roots.add(root)
            results.append(
                {
                    "root": root,
                    "points": groups.get(root, {root}),
                    "pins": pin_by_root.get(root, []),
                    "labels": label_by_root.get(root, []),
                }
            )
        return results


def _point_on_segment(p: Point, a: Point, b: Point, *, eps: float = 1e-4) -> bool:
    """True when `p` lies on segment ab (inclusive), within `eps`."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    len_sq = (bx - ax) * (bx - ax) + (by - ay) * (by - ay)
    if len_sq <= eps * eps:
        # Degenerate segment: only the endpoint itself counts.
        return abs(px - ax) <= eps and abs(py - ay) <= eps
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > eps * (len_sq ** 0.5):
        return False
    dot = (px - ax) * (bx - ax) + (py - ay) * (by - ay)
    if dot < -eps:
        return False
    if dot - len_sq > eps:
        return False
    return True
