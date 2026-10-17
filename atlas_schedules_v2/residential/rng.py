"""Random streams for the residential generator, in two interchangeable modes.

Every residential draw goes through a `Stream` with two operations:
`random()` (a float in [0, 1)) and `randbelow(n)` (an integer in [0, n)).

- R1 "ruby_mt": Ruby 3.2.2 `Random` (MT19937 with Ruby's seeding and
  bounded-integer rules). Replays the upstream OpenStudio-HPXML streams draw
  for draw, so results can be checked against native captures. Port of Ruby
  random.c and missing/mt19937.c (BSD notice: data/notices/notice-ruby-random.json).
- R2 "pcg64": numpy PCG64 streams spawned from the unit seed. Statistically
  equivalent use of randomness, not the same numbers.

Upstream gives each unit seven streams: `main` (occupant activities) plus one
per end use, the end-use seeds being drawn from an allocator seeded like main.
The EV stream is allocated but never used; it is kept so R1 matches upstream.
"""
import numpy as np

STREAM_NAMES = ("main", "hygiene", "dishwasher", "clothes_washer", "clothes_dryer", "ev", "cooking")
END_USES = STREAM_NAMES[1:]
MODES = ("ruby_mt", "pcg64")

_MASK = 0xFFFFFFFF
_N = 624


class RubyStream:
    """Ruby 3.2.2 `Random.new(seed)`: MT19937 with Ruby's integer seeding."""

    def __init__(self, seed: int):
        words = []
        remaining = seed
        while remaining:
            words.append(remaining & _MASK)
            remaining >>= 32
        if len(words) <= 1:
            self._state = self._linear_init(seed & _MASK)
        else:
            if words[-1] == 1:
                # Ruby drops a leading word of 1 (its sign guard) before seeding.
                words.pop()
            self._state = self._array_init(words)
        self._index = _N

    @staticmethod
    def _linear_init(seed: int) -> list[int]:
        state = [seed]
        for i in range(1, _N):
            previous = state[-1]
            state.append((1812433253 * (previous ^ (previous >> 30)) + i) & _MASK)
        return state

    @classmethod
    def _array_init(cls, words: list[int]) -> list[int]:
        state = cls._linear_init(19650218)
        i, j = 1, 0
        for _ in range(max(_N, len(words))):
            previous = state[i - 1]
            state[i] = ((state[i] ^ ((previous ^ (previous >> 30)) * 1664525)) + words[j] + j) & _MASK
            i += 1
            j += 1
            if i == _N:
                state[0] = state[_N - 1]
                i = 1
            if j == len(words):
                j = 0
        for _ in range(_N - 1):
            previous = state[i - 1]
            state[i] = ((state[i] ^ ((previous ^ (previous >> 30)) * 1566083941)) - i) & _MASK
            i += 1
            if i == _N:
                state[0] = state[_N - 1]
                i = 1
        state[0] = 0x80000000
        return state

    def _word(self) -> int:
        if self._index == _N:
            state = self._state
            for i in range(_N):
                mixed = (state[i] & 0x80000000) | (state[(i + 1) % _N] & 0x7FFFFFFF)
                state[i] = state[(i + 397) % _N] ^ (mixed >> 1) ^ (0x9908B0DF if mixed & 1 else 0)
            self._index = 0
        value = self._state[self._index]
        self._index += 1
        value ^= value >> 11
        value ^= (value << 7) & 0x9D2C5680
        value ^= (value << 15) & 0xEFC60000
        value ^= value >> 18
        return value

    def random(self) -> float:
        a = self._word() >> 5
        b = self._word() >> 6
        return (a * 67108864.0 + b) / 9007199254740992.0

    def randbelow(self, limit: int) -> int:
        """Ruby `rand(limit)`: draw words from the top and retry as soon as
        the partial value exceeds the bound."""
        maximum = limit - 1
        if maximum == 0:
            return 0
        count = (maximum.bit_length() + 31) // 32
        top_mask = (1 << (((maximum.bit_length() - 1) % 32) + 1)) - 1
        while True:
            value = 0
            on_boundary = True
            rejected = False
            for position in range(count - 1, -1, -1):
                word = self._word() & (top_mask if position == count - 1 else _MASK)
                bound = (maximum >> (32 * position)) & _MASK
                if on_boundary:
                    if word > bound:
                        rejected = True
                        break
                    if word < bound:
                        on_boundary = False
                value = (value << 32) | word
            if not rejected:
                return value


class Pcg64Stream:
    """numpy PCG64 stream; floats are drawn in blocks for speed."""

    BLOCK = 4096

    def __init__(self, seed_sequence: np.random.SeedSequence):
        self._generator = np.random.Generator(np.random.PCG64(seed_sequence))
        self._block = np.empty(0)
        self._next = 0

    def random(self) -> float:
        if self._next == len(self._block):
            self._block = self._generator.random(self.BLOCK)
            self._next = 0
        value = float(self._block[self._next])
        self._next += 1
        return value

    def randbelow(self, limit: int) -> int:
        return int(self._generator.integers(0, limit))


def unit_streams(mode: str, unit_seed: int) -> dict:
    """The seven named streams for one dwelling unit."""
    if mode == "ruby_mt":
        allocator = RubyStream(unit_seed)
        streams = {"main": RubyStream(unit_seed)}
        for name in END_USES:
            streams[name] = RubyStream(allocator.randbelow(2**32))
        return streams
    if mode == "pcg64":
        children = np.random.SeedSequence(unit_seed).spawn(len(STREAM_NAMES))
        return {name: Pcg64Stream(child) for name, child in zip(STREAM_NAMES, children)}
    raise ValueError(f"Unknown residential RNG mode {mode!r}; expected one of {MODES}")


def weighted_choice(stream, probabilities) -> int:
    """Index of the first cumulative probability >= one draw (upstream `weighted_random`).

    If rounding leaves the total below the draw, the last index is returned.
    """
    draw = stream.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= draw:
            return index
    return len(probabilities) - 1
