from enum import Enum, auto

from dusted.broadcaster import Broadcaster
from dusted.inputs import Inputs
from dusted.nexus_script import ButtonState, DirectionState, KeyStates, NexusScript

# The number of frames after the initial tap that a second tap will register as
# a double tap dash.
MAXIMUM_DOUBLE_TAP_DELAY = 14

# The attack intents that are allowed to come next.
VALID_NEXT_ATTACK_INTENT = {
    "0": {"a", "0"},
    "a": {"a", "b", "9", "0"},
    "b": {"b", "0"},
    "9": {"a", "b", "8", "0"},
    "8": {"a", "b", "7", "0"},
    "7": {"a", "b", "6", "0"},
    "6": {"a", "b", "5", "0"},
    "5": {"a", "b", "4", "0"},
    "4": {"a", "b", "3", "0"},
    "3": {"a", "b", "2", "0"},
    "2": {"a", "b", "1", "0"},
    "1": {"a", "b", "0"},
}


class Direction(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()


class ReplayDiagnostics(Broadcaster):
    def __init__(self, inputs: Inputs) -> None:
        super().__init__()

        self._inputs = inputs

        # Store the row and column of each diagnostic.
        self._warnings: set[tuple[int, int]] = set()
        self._errors: set[tuple[int, int]] = set()

        self._nexus_script = NexusScript(frames=[])

        self._inputs.subscribe(self._recalculate)
        self._recalculate()

    @property
    def warnings(self) -> set[tuple[int, int]]:
        return self._warnings

    @property
    def errors(self) -> set[tuple[int, int]]:
        return self._errors

    @property
    def nexus_script(self) -> NexusScript:
        return self._nexus_script

    def _recalculate(self) -> None:
        """Recalculate the diagnostics."""

        self._warnings.clear()
        self._errors.clear()

        nexus_script_frames: list[KeyStates] = []

        # Frame and direction of the first tap of a potential double tap dash.
        first_tap: tuple[int, Direction] | None = None

        prev_x = "1"
        prev_y = "1"
        prev_jump = "0"
        prev_dash = "0"
        prev_fall = "0"
        prev_light = "0"
        prev_heavy = "0"
        prev_taunt = "0"

        for frame in range(len(self._inputs)):
            x = self._inputs.at(0, frame)
            y = self._inputs.at(1, frame)
            jump = self._inputs.at(2, frame)
            dash = self._inputs.at(3, frame)
            fall = self._inputs.at(4, frame)
            light = self._inputs.at(5, frame)
            heavy = self._inputs.at(6, frame)
            taunt = self._inputs.at(7, frame)

            left_pressed = prev_x != "0" and x == "0"
            right_pressed = prev_x != "2" and x == "2"
            up_pressed = prev_y != "0" and y == "0"
            down_pressed = prev_y != "2" and y == "2"

            double_tap: Direction | None = None

            # Check each direction intent in priority order.
            for direction, pressed in [
                (Direction.LEFT, left_pressed),
                (Direction.UP, up_pressed),
                (Direction.RIGHT, right_pressed),
                (Direction.DOWN, down_pressed),
            ]:
                if not pressed:
                    continue

                if first_tap is None:
                    first_tap = frame, direction
                else:
                    first_tap_frame, first_tap_direction = first_tap
                    if (
                        first_tap_direction == direction
                        and frame <= first_tap_frame + MAXIMUM_DOUBLE_TAP_DELAY
                    ):
                        double_tap = direction
                        first_tap = None
                    else:
                        first_tap = frame, direction

            if double_tap in (Direction.LEFT, Direction.RIGHT):
                if dash != "0":
                    # This dash was caused by a double tap, and (probably) not
                    # by pressing the dash key.
                    dash = "0"
                else:
                    # It looks like there should be a dash intent on this
                    # frame. This is only a warning because it is possible to
                    # reproduce this scenario in a valid replay by holding
                    # both left and right at the same time.
                    self._warnings.add((3, frame))

            if double_tap is Direction.DOWN:
                if fall != "0":
                    # This fall was caused by a double tap, and (probably) not
                    # by pressing the dash key.
                    fall = "0"
                else:
                    # It looks like there should be a fall intent on this
                    # frame. This is only a warning because it is possible to
                    # reproduce this scenario in a valid replay by holding
                    # both up and down at the same time.
                    self._warnings.add((4, frame))

            jump_pressed = prev_jump == "0" and jump != "0"
            dash_pressed = (
                prev_dash == "0" and prev_fall == "0" and (dash != "0" or fall != "0")
            )
            light_pressed = prev_light == "0" and light != "0"
            heavy_pressed = prev_heavy == "0" and heavy != "0"
            taunt_pressed = prev_taunt == "0" and taunt != "0"

            if double_tap is None:
                if dash != "0" and not dash_pressed:
                    # This is a non double tapped dash without a dash press.
                    self._errors.add((3, frame))

                if fall != "0" and (not dash_pressed or y != "2"):
                    # This is a non double tapped fall without a dash press or
                    # down intent.
                    self._errors.add((4, frame))

                if dash != "0" and fall == "0" and y == "2":
                    # This is a non double tapped dash with down held, which
                    # should result in a fall input, but hasn't.
                    self._errors.add((4, frame))

            # Pressing any other key interrupts a double tap.
            if (
                heavy_pressed
                or dash_pressed
                or light_pressed
                or jump_pressed
                or taunt_pressed
            ):
                first_tap = None

            # Check for invalid attack intents.
            if light not in VALID_NEXT_ATTACK_INTENT[prev_light]:
                self._errors.add((5, frame))
            if heavy not in VALID_NEXT_ATTACK_INTENT[prev_heavy]:
                self._errors.add((6, frame))

            nexus_script_frames.append(
                KeyStates(
                    left=(
                        DirectionState.DOUBLE_TAPPED
                        if double_tap is Direction.LEFT
                        else (
                            DirectionState.HELD if x == "0" else DirectionState.RELEASED
                        )
                    ),
                    right=(
                        DirectionState.DOUBLE_TAPPED
                        if double_tap is Direction.RIGHT
                        else (
                            DirectionState.HELD if x == "2" else DirectionState.RELEASED
                        )
                    ),
                    up=(DirectionState.HELD if y == "0" else DirectionState.RELEASED),
                    down=(
                        DirectionState.DOUBLE_TAPPED
                        if double_tap is Direction.DOWN
                        else (
                            DirectionState.HELD if y == "2" else DirectionState.RELEASED
                        )
                    ),
                    jump=ButtonState.HELD if jump != "0" else ButtonState.RELEASED,
                    dash=(
                        ButtonState.HELD
                        if (dash != "0" or fall != "0")
                        else ButtonState.RELEASED
                    ),
                    light=ButtonState.HELD if light in "ab" else ButtonState.RELEASED,
                    heavy=ButtonState.HELD if heavy in "ab" else ButtonState.RELEASED,
                    escape=ButtonState.RELEASED,
                    taunt=ButtonState.HELD if taunt != "0" else ButtonState.RELEASED,
                )
            )

            prev_x = x
            prev_y = y
            prev_jump = jump
            prev_dash = dash
            prev_fall = fall
            prev_light = light
            prev_heavy = heavy
            prev_taunt = taunt

        self._nexus_script = NexusScript(nexus_script_frames)

        self.broadcast()
