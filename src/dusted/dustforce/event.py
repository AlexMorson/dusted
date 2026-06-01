import struct
from dataclasses import dataclass
from typing import TypeAlias

from dustmaker.replay import Character

from dusted.models.inputs import Intents

StateId: TypeAlias = str


@dataclass(frozen=True)
class State:
    x: float
    y: float


@dataclass(frozen=True)
class LevelStartEvent:
    id: StateId
    level: str
    character: Character
    state: State


@dataclass(frozen=True)
class StepEvent:
    id: StateId
    prev_id: StateId
    intents: Intents
    state: State


Event: TypeAlias = LevelStartEvent | StepEvent


def parse_event(line: str) -> LevelStartEvent | StepEvent | None:
    match _parse_next_field(line):
        case ["[dusted]", line]:
            pass
        case _:
            return None

    match _parse_next_field(line):
        case ["level_start", line]:
            return _parse_level_start_event(line)
        case ["step", line]:
            return _parse_step_event(line)
        case _:
            return None


def _parse_level_start_event(line: str) -> LevelStartEvent | None:
    if not (id_result := _parse_id(line)):
        return None
    id, line = id_result

    if not (level_result := _parse_string(line)):
        return None
    level, line = level_result

    if not (character_result := _parse_character(line)):
        return None
    character, line = character_result

    if not (state_result := _parse_state(line)):
        return None
    state, line = state_result

    return LevelStartEvent(
        id=id,
        level=level,
        character=character,
        state=state,
    )


def _parse_step_event(line: str) -> StepEvent | None:
    if not (id_result := _parse_id(line)):
        return None
    id, line = id_result

    if not (prev_id_result := _parse_id(line)):
        return None
    prev_id, line = prev_id_result

    if not (intents_result := _parse_intents(line)):
        return None
    intents, line = intents_result

    if not (state_result := _parse_state(line)):
        return None
    state, line = state_result

    return StepEvent(
        id=id,
        prev_id=prev_id,
        intents=intents,
        state=state,
    )


def _parse_id(line: str) -> tuple[StateId, str] | None:
    return _parse_next_field(line)


def _parse_character(line: str) -> tuple[Character, str] | None:
    if not (level_result := _parse_int(line)):
        return None
    character_index, line = level_result

    try:
        character = Character(character_index)
    except ValueError:
        return None

    return character, line


def _parse_intents(line: str) -> tuple[Intents, str] | None:
    if not (result := _parse_int(line)):
        return None
    x, line = result

    if not (result := _parse_int(line)):
        return None
    y, line = result

    if not (result := _parse_int(line)):
        return None
    jump, line = result

    if not (result := _parse_int(line)):
        return None
    dash, line = result

    if not (result := _parse_int(line)):
        return None
    fall, line = result

    if not (result := _parse_int(line)):
        return None
    light, line = result

    if not (result := _parse_int(line)):
        return None
    heavy, line = result

    if not (result := _parse_int(line)):
        return None
    taunt, line = result

    try:
        intents = Intents(
            x=x,
            y=y,
            jump=jump,
            dash=dash,
            fall=fall,
            light=light,
            heavy=heavy,
            taunt=taunt,
        )
    except ValueError:
        return None

    return intents, line


def _parse_state(line: str) -> tuple[State, str] | None:
    if not (result := _parse_float(line)):
        return None
    x, line = result

    if not (result := _parse_float(line)):
        return None
    y, line = result

    return State(x=x, y=y), line


def _parse_string(line: str) -> tuple[str, str] | None:
    """
    Parse a string field.

    Strings are wrapped in double quotes to allow them to contain spaces.
    """

    # Split on the next two quote characters. At some point this might need to
    # handle escaped quotes, but for now all the strings that are being parsed
    # simply cannot contain a quote, so there is no need.
    match line.split('"', maxsplit=2):
        case ["", value, line]:
            pass
        case _:
            return None

    if not line.startswith(" "):
        return None

    return value, line[1:]


def _parse_int(line: str) -> tuple[int, str] | None:
    """
    Parse an int field.

    Negative integers are allowed.
    """

    if not (result := _parse_next_field(line)):
        return None
    value_str, line = result

    try:
        value = int(value_str)
    except ValueError:
        return None

    return value, line


def _parse_float(line: str) -> tuple[float, str] | None:
    """
    Parse a float field.

    These are serialised as big-endian hex strings to avoid loss of precision.
    """

    if not (result := _parse_next_field(line)):
        return None
    value_hex, line = result

    try:
        value_bytes = bytes.fromhex(value_hex)
    except ValueError:
        return None

    try:
        values = struct.unpack("!f", value_bytes)
    except struct.error:
        return None

    if len(values) != 1:
        return None

    return values[0], line


def _parse_next_field(line: str) -> tuple[str, str] | None:
    """Split a line into its next field and the remainder."""

    match line.split(" ", maxsplit=1):
        case [field, line]:
            return field, line
        case [field] if field:
            return field, ""
        case _:
            return None
