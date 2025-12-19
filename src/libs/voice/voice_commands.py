from enum import Enum
from dataclasses import dataclass
import re

WORD_TO_NUMBER = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100
}


def words_to_number(text: str) -> int | None:
    words = text.lower().split()
    total = 0
    current = 0
    found_number = False

    for word in words:
        if word in WORD_TO_NUMBER:
            found_number = True
            value = WORD_TO_NUMBER[word]
            if value == 100:
                current = current * 100 if current else 100
            elif value >= 20:
                current += value
            else:
                current += value
        elif word.isdigit():
            found_number = True
            current = int(word)

    total += current
    return total if found_number else None


class VoiceCommand(Enum):
    START = "start"
    NEXT = "next"
    AGAIN = "again"
    PREVIOUS = "previous"
    GO_TO = "go_to"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    START_RECORDING = "start_recording"
    PAUSE_RECORDING = "pause_recording"
    RESUME_RECORDING = "resume_recording"
    STOP_RECORDING = "stop_recording"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    command: VoiceCommand
    shot_number: int | None = None


COMMAND_PATTERNS = {
    VoiceCommand.START: ["start", "play", "begin"],
    VoiceCommand.NEXT: ["next", "forward"],
    VoiceCommand.AGAIN: ["again", "repeat", "replay"],
    VoiceCommand.PREVIOUS: ["previous", "back"],
    VoiceCommand.GO_TO: ["go to", "jump to", "shot"],
    VoiceCommand.PAUSE: ["pause", "wait", "hold"],
    VoiceCommand.RESUME: ["resume", "continue"],
    VoiceCommand.STOP: ["stop", "quit", "exit", "end"],
    VoiceCommand.START_RECORDING: ["start recording", "begin recording", "start record"],
    VoiceCommand.PAUSE_RECORDING: ["pause recording", "post recording", "hold recording", "pause record", "paws recording"],
    VoiceCommand.RESUME_RECORDING: ["resume recording", "continue recording", "resume record", "resume regarding", "resumed recording"],
    VoiceCommand.STOP_RECORDING: ["stop recording", "end recording", "stop record"],
}

RECORDING_COMMANDS = [
    VoiceCommand.START_RECORDING,
    VoiceCommand.PAUSE_RECORDING,
    VoiceCommand.RESUME_RECORDING,
    VoiceCommand.STOP_RECORDING,
]


def parse_command(text: str) -> ParsedCommand:
    text_lower = text.lower().strip()

    for command in RECORDING_COMMANDS:
        if any(p in text_lower for p in COMMAND_PATTERNS[command]):
            return ParsedCommand(command)

    for pattern in COMMAND_PATTERNS[VoiceCommand.GO_TO]:
        if pattern in text_lower:
            number = words_to_number(text_lower)
            if number:
                return ParsedCommand(VoiceCommand.GO_TO, number)

    for command, patterns in COMMAND_PATTERNS.items():
        if command == VoiceCommand.GO_TO or command in RECORDING_COMMANDS:
            continue
        if any(p in text_lower for p in patterns):
            return ParsedCommand(command)

    return ParsedCommand(VoiceCommand.UNKNOWN)
