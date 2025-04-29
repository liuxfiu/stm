from collections.abc import Callable
import threading
from mpi4py import MPI
from typing import Any, Literal

from .connection import _Reader, _Writer
from .channel import _Channel

from .log import logger
from .messaging import (
    _Message_Channel_Put,
    _Message_Reader_Consume,
    _Message_Reader_Data,
    _Message_STM_Shutdown,
    _Message_Writer_Advance,
    STM_Tag,
)


COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


class _STM:
    def __init__(self):
        self._channel_rank: dict[str, int] = {}
        self._local_channels: dict[str, _Channel] = {}
        self._readers_by_channel: dict[str, list[_Reader]] = {}
        self._readers_by_id: dict[str, _Reader] = {}
        self._writers_by_id: dict[str, _Writer] = {}
        self._rank_shutdown = [False] * SIZE

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def get_reader(self, name: str):
        return self._readers_by_id[name]

    def get_writer(self, name: str):
        return self._writers_by_id[name]

    def start(self, listening_mode: Literal["thread", "manual"] = "thread"):
        if listening_mode == "thread":
            self._listening_thread = threading.Thread(
                target=self._receive_message_loop,
                args=(self.process_message,),
            )
            self._listening_thread.start()
        elif listening_mode == "manual":
            pass
        else:
            raise ValueError("Invalid listening_mode")

    def stop(self):
        shutdown_msg = _Message_STM_Shutdown(source_rank=RANK)
        for target in range(SIZE):
            COMM.send(obj=shutdown_msg, dest=target, tag=STM_Tag.STM_DATA)

    def _receive_message_loop(self, handler: Callable[[Any], None]):
        while True:
            msg = self.receive_message().wait()
            if self.check_shutdown(msg):
                break
            handler(msg)

    def receive_message(self) -> MPI.Request:
        return COMM.irecv(tag=STM_Tag.STM_DATA)

    def check_shutdown(self, msg: Any):
        if isinstance(msg, _Message_STM_Shutdown):
            self._rank_shutdown[msg.source_rank] = True
            logger.debug(
                f"({RANK}) received shutdown from {msg.source_rank}, {self._rank_shutdown}"
            )
        if self._rank_shutdown[RANK] and all(self._rank_shutdown):
            logger.info(f"({RANK}) shutting down")
            return True
        return False

    def process_message(self, msg):
        logger.info(f"({RANK}) received {msg}")
        if isinstance(msg, _Message_Channel_Put):
            self._put(msg.ts, msg.item, msg.channel_name)
        elif isinstance(msg, _Message_Reader_Data):
            for reader in self._readers_by_channel.get(msg.channel_name, []):
                reader.data[msg.ts] = msg.item
        elif isinstance(msg, _Message_Reader_Consume):
            channel = self._local_channels[msg.channel_name]
            channel.handle_consume_until(msg.reader_name, msg.until)
        elif isinstance(msg, _Message_Writer_Advance):
            if msg.channel_name in self._local_channels:
                channel = self._local_channels[msg.channel_name]
                channel.handle_advance_until(msg.writer_name, msg.until)
                return
            for reader in self._readers_by_channel[msg.channel_name]:
                reader.channel_advancetime = max(reader.channel_advancetime, msg.until)

    def _put(self, ts: int, item: Any, channel_name: str):
        if channel_name in self._local_channels:
            channel = self._local_channels[channel_name]
            channel.publish_data(ts, item)
        else:
            # todo: this can be removed once we have proper checks in the .build phase
            if channel_name not in self._channel_rank:
                raise ValueError(f"Unknown channel {channel_name}")
            msg = _Message_Channel_Put(ts, item, RANK, channel_name)
            channel_rank = self._channel_rank[channel_name]
            COMM.send(obj=msg, dest=channel_rank, tag=STM_Tag.STM_DATA)
