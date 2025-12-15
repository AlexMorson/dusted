from enum import Enum, auto

from dusted.broadcaster import Broadcaster
from dusted.inputs import Inputs

# The number of frames after the initial tap that a second tap will register as
# a double tap dash.
MAXIMUM_DOUBLE_TAP_DELAY = 14


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

        self._inputs.subscribe(self._recalculate)
        self._recalculate()

    @property
    def warnings(self) -> set[tuple[int, int]]:
        return self._warnings

    @property
    def errors(self) -> set[tuple[int, int]]:
        return self._errors

    def _recalculate(self) -> None:
        """Recalculate the diagnostics."""

        self._warnings.clear()
        self._errors.clear()

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

            # Pressing any other key interrupts a double tap.
            if (
                heavy_pressed
                or dash_pressed
                or light_pressed
                or jump_pressed
                or taunt_pressed
            ):
                first_tap = None

            prev_x = x
            prev_y = y
            prev_jump = jump
            prev_dash = dash
            prev_fall = fall
            prev_light = light
            prev_heavy = heavy
            prev_taunt = taunt

        self.broadcast()
