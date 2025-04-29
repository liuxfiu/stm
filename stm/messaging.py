from dataclasses import dataclass
from typing import Any


class STM_Tag:
    STM_DATA = 1


@dataclass
class _Message_STM_Channels_Init:
    channels: list[str]
    source_rank: int


@dataclass
class _Message_STM_Shutdown:
    source_rank: int


@dataclass
class _Message_Channel_Put:
    ts: int
    item: Any
    source_rank: int
    channel_name: str


@dataclass
class _Message_Reader_Data:
    ts: int
    item: Any
    channel_name: str


@dataclass
class _Message_Reader_Consume:
    until: int
    reader_name: str
    channel_name: str


@dataclass
class _Message_Writer_Advance:
    until: int
    writer_name: str
    channel_name: str
