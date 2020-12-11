import json
from enum import Enum, IntEnum, auto

from rboclient.network.handling import Data, HandlerNode
from rboclient.network.protocol import HandlerLeaf


class YesNoQuestion(IntEnum):
    MissingParticipants = 0,
    RetryCheckpoint = 1,
    KickUnknownPlayers = 2


class Attacker(Enum):
    Player = auto(),
    Enemy = auto()


def nothing() -> dict:
    return {}


def name(data: Data) -> dict:
    return {"name": data.takeString()}


def id(data: Data) -> dict:
    return {"id": data.take()}


def idAndName(data: Data) -> dict:
    return {"id": data.take(), "name": data.takeString()}


def yesNoQuestion(data: Data) -> dict:
    return {"question": YesNoQuestion(data.take())}


def ids(data: Data) -> dict:
    count = data.take()
    return {"ids": [data.take() for i in range(count)]}


def confirmRequest(data: Data) -> dict:
    return {"target": data.take()}


def rangeRequest(data: Data) -> dict:
    return {"target": data.take(), "message": data.takeString(), "min": data.take(), "max": data.take()}


def possibilities(data: Data) -> dict:
    args = {"target": data.take(), "message": data.takeString(), "options": {}}
    count = data.take()

    for i in range(count):
        id = data.take()
        args["options"][id] = data.takeString()

    return args


def yesNoRequest(data: Data) -> dict:
    return {"target": data.take(), "message": data.takeString()}


def text(data: Data) -> dict:
    return {"text": data.takeString()}


def playerUpdate(data: Data) -> dict:
    return {"id": data.take(), "update": json.loads(data.takeString())}


def globalStat(data: Data) -> dict:
    args = {"name": data.takeString(), "hidden": data.takeBool(), "main": data.takeBool()}

    if not args["hidden"]:
        for arg in ["min", "max", "value"]:
            args[arg] = data.takeNumeric(4, signed=True)

    return args


def reply(data: Data) -> dict:
    return {"id": data.take(), "reply": data.take()}


def enemiesGroup(data: Data) -> dict:
    return {"group": json.loads(data.takeString())}


def atk(data: Data) -> dict:
    args = {"playersId": data.take(), "enemiesName": data.takeString()}
    dmg = data.takeNumeric(4, signed=True)

    args["attacker"] = Attacker.Player if dmg >= 0 else Attacker.Enemy
    args["dmg"] = abs(dmg)

    return args


def scene(data: Data) -> dict:
    return {"scene": data.takeNumeric(2)}


def members(data: Data) -> dict:
    count = data.take()

    args = {"members": {}}
    for i in range(count):
        id = data.take()
        args["members"][id] = (data.takeString(), data.takeBool())

    return args


def delay(data: Data) -> dict:
    return {"delay": data.takeNumeric(8)}


registering = HandlerNode({
    0: HandlerLeaf("registered", members),
    1: HandlerLeaf("invalid_request"),
    2: HandlerLeaf("unavailable_id"),
    3: HandlerLeaf("unavailable_name"),
    4: HandlerLeaf("unavailable_session")
})

lobby = HandlerNode({
    0: HandlerLeaf("member_registered", idAndName),
    1: HandlerLeaf("member_ready", id),
    2: HandlerLeaf("member_disconnected", id),
    3: HandlerLeaf("member_crashed", id),
    4: HandlerLeaf("preparing_session", delay),
    12: HandlerLeaf("cancel_preparing"),
    5: HandlerLeaf("prepare_session", id),
    6: HandlerLeaf("ask_checkpoint"),
    7: HandlerLeaf("ask_yes_no", yesNoQuestion),
    13: HandlerLeaf("selecting_checkpoint"),
    14: HandlerLeaf("checking_players"),
    8: HandlerLeaf("session_prepared"),
    9: HandlerNode({
        0: HandlerLeaf("done"),
        1: HandlerLeaf("crash"),
        2: HandlerLeaf("checkpoint_error"),
        3: HandlerLeaf("less_members", ids),
        4: HandlerLeaf("unknown_players", ids)
    }, "result"),
    10: HandlerLeaf("master_disconnected"),
    11: HandlerLeaf("lobby_open")
})

session = HandlerNode({
    0: HandlerNode({
        0: HandlerLeaf("range", rangeRequest),
        1: HandlerLeaf("possibilities", possibilities),
        2: HandlerLeaf("confirm", confirmRequest),
        3: HandlerLeaf("yes_no", yesNoRequest)
    }, "request"),
    13: HandlerLeaf("finish_request"),
    1: HandlerLeaf("text", text),
    2: HandlerLeaf("player_update", playerUpdate),
    3: HandlerLeaf("global_stat_update", globalStat),
    4: HandlerLeaf("player_die", id),
    5: HandlerLeaf("scene_switch", scene),
    6: HandlerLeaf("player_reply", reply),
    7: HandlerNode({
        0: HandlerLeaf("validated"),
        1: HandlerLeaf("late"),
        2: HandlerLeaf("out_of_range"),
        3: HandlerLeaf("invalid_length"),
        4: HandlerLeaf("confirm_expected")
    }, "reply"),
    8: HandlerNode({
        0: HandlerLeaf("init", enemiesGroup),
        1: HandlerLeaf("atk", atk),
        2: HandlerLeaf("end", nothing)
    }, "battle"),
    9: HandlerLeaf("player_crash", id),
    10: HandlerLeaf("leader_switch", id),
    11: HandlerLeaf("session_start", name),
    12: HandlerLeaf("session_stop")
})
