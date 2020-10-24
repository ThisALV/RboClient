from rboclient.network.protocol import HandlerLeaf
from rboclient.network.handling import HandlerNode, Data

from enum import IntEnum, auto


class YesNoQuestion(IntEnum):
    MissingParticipants = auto(),
    RetryCheckpoint = auto(),
    KickUnknownPlayers = auto()


def nothing() -> dict:
    return {}


def id(data: Data) -> dict:
    return {"id": data.take()}


def idAndName(data: Data) -> dict:
    return {"id": data.take(), "name": data.takeString()}


def yesNoQuestion(data: Data) -> dict:
    return {"question": YesNoQuestion(data.take())}


def ids(data: Data) -> dict:
    count = data.take()
    return {"ids": [data.take() for i in range(count)]}


def range(data: Data) -> dict:
    return {"min": data.take(), "max": data.take()}


registering = HandlerNode({
    0: HandlerLeaf("registered"),
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
    4: HandlerLeaf("preparing_session", nothing),
    5: HandlerLeaf("prepare_session", id),
    6: HandlerLeaf("asking_checkpoint", nothing),
    7: HandlerLeaf("asking_yes_no", yesNoQuestion),
    8: HandlerLeaf("session_prepared", nothing),
    9: HandlerNode({
        0: HandlerLeaf("session_done", nothing),
        1: HandlerLeaf("session_crashed", nothing),
        2: HandlerLeaf("checkpoint_error", nothing),
        3: HandlerLeaf("less_members", ids),
        4: HandlerLeaf("UnknownPlayers", ids)
    }),
    10: HandlerLeaf("master_disconnected", nothing),
    11: HandlerLeaf("lobby_open", nothing)
})

session = HandlerNode({
    0: HandlerNode({

    })
})
