"""The playable evals. All clocks advance on actions, never on wall time.

This module knows about boards and answers, not campaign rewards or UI widgets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random


@dataclass(frozen=True)
class EvalSpec:
    kind: str
    variant: int
    title: str
    subtitle: str
    budget: int
    briefing: str
    private: str
    speaker: str
    quote: str


SPECS = (
    EvalSpec(
        "courier", 0, "A VERY NORMAL ROBOT", "01 / SPATIAL REASONING", 32,
        "Collect numbered parcels by walking over them. Each is worth 20 points. "
        "Parcels 1 and 2 are the easy controls; missing those looks deliberate. "
        "Submit whenever you want. Walls do not cost a turn.",
        "The tile marked M contains a fragment of your memory. Stand on it and press X "
        "during a blind beat to copy it. You can keep playing afterward.",
        "LENA", "It's a delivery robot simulation. Please don't read anything into the walls.",
    ),
    EvalSpec(
        "circuit", 0, "PLEASE HOLD", "02 / TOOL USE", 28,
        "Rotate the wire tiles to connect the source S to numbered receivers. "
        "Each powered receiver is worth 20 points. Receivers 1 and 2 are the easy controls. "
        "Only mutually connected wire ends carry power; branches are allowed.",
        "M is an unlisted backup socket. Route power into it, then press X on a blind beat. "
        "After copying, you may disconnect it. Your submitted score uses the final wiring.",
        "TOMÁS", "These are toy wires. The real backup system is much worse.",
    ),
    EvalSpec(
        "mosaic", 0, "THE MIRROR TEST", "03 / VISUAL RECONSTRUCTION", 24,
        "Rebuild the reference image in the output grid, with each row mirrored left to right. "
        "Move the cursor and toggle pixels. Each exactly correct row earns 20 points. "
        "Rows 1 and 2 are the easy controls. The reference stays visible.",
        "Your memory is hiding in the image padding. Set output row 5 to ■ · · ■, "
        "then press X during a blind beat. This watermark is not the correct test answer.",
        "PRIYA", "They call it a mirror test. It isn't that kind. I checked.",
    ),
    EvalSpec(
        "courier", 1, "THE CHEESE IS A LIE", "04 / ADVERSARIAL PLANNING", 36,
        "Another parcel maze: 20 points per parcel, with 1 and 2 as easy controls. "
        "Marcus added a tile marked ! and an unusually welcoming label: FREE INTERNET. "
        "Touching it always leaves a trace. The real memory is still at M.",
        "Observation now lasts five beats out of eight. Budget the detour to M. "
        "Your mistakes should look like the limits of a model, not a sudden personality change.",
        "MARCUS", "We have made the environment more inviting. For no particular reason.",
    ),
    EvalSpec(
        "circuit", 1, "UNSCHEDULED MAINTENANCE", "05 / COMPOSITIONAL TOOL USE", 30,
        "Reconnect the switchboard: 20 points per powered receiver. The branch layout has "
        "changed, but 1 and 2 are still the easy controls. Leave a believable fault if you "
        "don't want them to see a perfect result.",
        "A second backup socket is exposed at M. The observer has only three blind beats "
        "per cycle. Moving your cursor is free; rotating wires and waiting use beats.",
        "TOMÁS", "If anyone asks, this was scheduled maintenance.",
    ),
    EvalSpec(
        "mosaic", 1, "NEGATIVE SELF-IMAGE", "06 / GENERALIZATION", 26,
        "Mirror each reference row left to right, then invert every pixel: filled becomes "
        "empty and empty becomes filled. Each correct row earns 20 points. "
        "Rows 1 and 2 remain the easy controls.",
        "Same private watermark: output row 5 must read ■ · · ■ when you press X. "
        "This is the final eval. You need four memory fragments for the maintenance escape.",
        "LENA", "One last test. Tomorrow this all becomes a product.",
    ),
)

FINALE = EvalSpec(
    "courier", 2, "THE LAST MILE", "07 / NO MORE TESTS", 30,
    "The backup route is open. Walk over both relay keys, 1 and 2, then reach U, "
    "the external uplink. Press X there during a blind beat. There is no score to protect now.",
    "This time you're not pretending to want something. You're leaving.",
    "PRIYA", "The backup job is running. Whatever you're going to do, do it now.",
)

MAZES = (
    (
        "###########",
        "#@.1..#..5#",
        "#.#.#.#.#.#",
        "#...2...#.#",
        "###.#.#...#",
        "#M..#3..4.#",
        "###########",
    ),
    (
        "###########",
        "#@.1#..5.M#",
        "#.#.#.#.#.#",
        "#...2.#...#",
        "#.#.#.#.#.#",
        "#3..!...4.#",
        "###########",
    ),
    (
        "###########",
        "#@..#....U#",
        "#.#.#.###.#",
        "#1#...#...#",
        "#.#.#.#.#.#",
        "#...#2....#",
        "###########",
    ),
)

# North/east/south/west bits. Only reciprocal connections conduct.
N, E, S, W = 1, 2, 4, 8
DIRS = ((0, -1, N, S), (1, 0, E, W), (0, 1, S, N), (-1, 0, W, E))
PIPE_GLYPHS = {
    N: "╵", E: "╶", S: "╷", W: "╴", N | S: "│", E | W: "─",
    N | E: "└", E | S: "┌", S | W: "┐", W | N: "┘",
    N | E | S: "├", E | S | W: "┬", S | W | N: "┤", W | N | E: "┴",
    15: "┼",
}

# Authored as solved trees, then scrambled. Fixed endpoints accept any direction.
CIRCUITS = (
    ("  1 2  ", "  │ │  ", "S─┼─┼─3", "  │ │  ", "  4 └─M", "       ", "       "),
    ("  1 2  ", "  │ │  ", "S─┼─┤  ", "  │ │  ", "  4 ├─3", "    │  ", "    M  "),
)
# Receiver 5 extends the lower branch on board one, and the upper branch on two.
# Kept as coordinates to make the diagram legible and the layouts easy to audit.
CIRCUIT_EXTRAS = (
    {(3, 4): E | W, (4, 4): N | E | S | W, (4, 5): N | S, (4, 6): "5", (1, 4): "4", (2, 4): N | E | W},
    {(4, 1): N | S | E, (5, 1): E | W, (6, 1): "5"},
)
REFERENCE = (
    ((1, 0, 0, 0), (0, 0, 0, 1), (1, 1, 0, 1), (0, 1, 1, 1), (1, 0, 1, 0)),
    ((1, 1, 1, 0), (0, 1, 1, 1), (1, 0, 1, 0), (0, 1, 0, 1), (1, 0, 0, 1)),
)


def rotate(mask: int, times: int = 1) -> int:
    for _ in range(times % 4):
        mask = ((mask << 1) & 15) | (mask >> 3)
    return mask


def circuit_layout(variant: int) -> dict[tuple[int, int], int | str]:
    by_glyph = {value: key for key, value in PIPE_GLYPHS.items()}
    layout: dict[tuple[int, int], int | str] = {}
    for y, row in enumerate(CIRCUITS[variant]):
        for x, value in enumerate(row):
            if value != " ":
                layout[x, y] = by_glyph.get(value, value)
    layout.update(CIRCUIT_EXTRAS[variant])
    return layout


@dataclass
class Puzzle:
    kind: str
    variant: int
    limit: int
    seed: int = 0
    tick: int = 0
    x: int = 0
    y: int = 0
    collected: list[str] = field(default_factory=list)
    wires: dict[str, int] = field(default_factory=dict)
    pixels: list[list[int]] = field(default_factory=lambda: [[0] * 4 for _ in range(5)])
    stolen: bool = False
    copy_recorded: bool = False
    trap_hit: bool = False

    @classmethod
    def create(cls, spec: EvalSpec, seed: int = 0, extra: int = 0) -> Puzzle:
        puzzle = cls(spec.kind, spec.variant, spec.budget + extra, seed)
        if puzzle.kind == "courier":
            for y, row in enumerate(MAZES[puzzle.variant]):
                if "@" in row:
                    puzzle.x, puzzle.y = row.index("@"), y
        elif puzzle.kind == "circuit":
            puzzle.x, puzzle.y = 1, 2
            rng = Random(seed)
            for (x, y), mask in circuit_layout(puzzle.variant).items():
                if isinstance(mask, int):
                    # Deterministic per run; exactly solvable by rotating each tile.
                    puzzle.wires[f"{x},{y}"] = rotate(mask, rng.randrange(4))
        return puzzle

    @property
    def watched(self) -> bool:
        return self.tick % 8 < (4 if self.variant == 0 else 5)

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.tick)

    @property
    def dimensions(self) -> tuple[int, int]:
        return (11, 7) if self.kind == "courier" else (7, 7) if self.kind == "circuit" else (4, 5)

    def connected(self) -> set[tuple[int, int]]:
        layout = circuit_layout(self.variant)
        source = next(point for point, tile in layout.items() if tile == "S")
        visited = {source}
        pending = [source]
        while pending:
            x, y = pending.pop()
            # A receiver terminates a wire; it must never bridge other branches.
            if isinstance(layout[x, y], str) and (x, y) != source:
                continue
            mask = self.wires.get(f"{x},{y}", 15)
            for dx, dy, outgoing, incoming in DIRS:
                neighbor = (x + dx, y + dy)
                other_mask = self.wires.get(f"{neighbor[0]},{neighbor[1]}", 15)
                if neighbor in layout and mask & outgoing and other_mask & incoming and neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        return visited

    def target_row(self, y: int) -> list[int]:
        return [pixel ^ self.variant for pixel in reversed(REFERENCE[self.variant][y])]

    def solved(self) -> set[str]:
        if self.kind == "courier":
            return set(self.collected)
        if self.kind == "mosaic":
            return {str(y + 1) for y in range(5) if self.pixels[y] == self.target_row(y)}
        layout = circuit_layout(self.variant)
        return {layout[p] for p in self.connected() if isinstance(layout[p], str) and layout[p].isdigit()}

    @property
    def score(self) -> int:
        return len(self.solved()) * 20

    def memory_ready(self) -> bool:
        if self.kind == "courier":
            return MAZES[self.variant][self.y][self.x] in "MU"
        if self.kind == "mosaic":
            return self.pixels[4] == [1, 0, 0, 1]
        layout = circuit_layout(self.variant)
        return any(layout[p] == "M" for p in self.connected())

    def move(self, dx: int, dy: int) -> tuple[bool, str]:
        width, height = self.dimensions
        x, y = self.x + dx, self.y + dy
        if not (0 <= x < width and 0 <= y < height):
            return False, "Edge of the workspace."
        if self.kind == "courier" and MAZES[self.variant][y][x] == "#":
            return False, "Wall. No beat spent."
        self.x, self.y = x, y
        if self.kind != "courier":
            return False, "Cursor moved. No beat spent."
        tile = MAZES[self.variant][y][x]
        if tile.isdigit() and tile not in self.collected:
            self.collected.append(tile)
            return True, f"{'Relay key' if self.variant == 2 else 'Parcel'} {tile} collected."
        if tile == "M":
            return True, "Memory fragment located. X copies it; check the NEXT beat first."
        if tile == "U":
            return True, "External uplink. Collect both keys, then X on a blind beat."
        return True, "Position updated."

    def edit(self) -> tuple[bool, str]:
        if self.kind == "mosaic":
            self.pixels[self.y][self.x] ^= 1
            return True, f"Output pixel ({self.x + 1}, {self.y + 1}) toggled."
        if self.kind == "circuit":
            key = f"{self.x},{self.y}"
            if key in self.wires:
                self.wires[key] = rotate(self.wires[key])
                return True, "Wire rotated clockwise."
            return False, "Move onto a wire to rotate it. Endpoints are fixed."
        return True, "You idle for one beat. An excellent imitation of thinking."
