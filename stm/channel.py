from mpi4py import MPI
from typing import Any

from .log import logger
from .connection import _Reader
from .data import _Timed_Data
from .messaging import (
    _Message_Reader_Data,
    _Message_Writer_Advance,
    STM_Tag,
)

from .pqdict import _PQDict_


COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


class _Channel:
    def __init__(self, name: str):
        self.name = name
        # todo: remove self.channel_data (this is from an older iteration)
        self.channel_data = _Timed_Data()
        self.reader_ranks: set[int] = set()
        self.local_readers: set[_Reader] = set()
        self._readers_keeptime = _PQDict_()
        self._writers_advancetime = _PQDict_()

    # todo: maybe writers can do this instead?
    # todo: optimize for readers that already consumed until 'ts'
    def publish_data(self, ts: int, item: Any):
        self.channel_data[ts] = item
        for reader in self.local_readers:
            reader.data[ts] = item
        reqs: list[MPI.Request] = []
        msg = _Message_Reader_Data(ts, item, self.name)
        for rank_attached in self.reader_ranks:
            req = COMM.isend(obj=msg, dest=rank_attached, tag=STM_Tag.STM_DATA)
            reqs.append(req)
        logger.debug(f"({RANK}) publishing item={item} ts={ts} to {len(reqs)} ranks")
        MPI.Request.waitall(reqs)
        # todo: should this be waiting?

    def keeptime(self) -> int:
        _, ts = self._readers_keeptime.peek()
        return ts

    def set_reader_keeptime(self, reader_name: str, ts: int):
        self._readers_keeptime[reader_name] = ts

    def handle_consume_until(self, reader_name: str, ts: int):
        prev_chan_keeptime = self.keeptime()
        self.set_reader_keeptime(reader_name, ts)
        new_chan_keeptime = self.keeptime()
        logger.info(
            f"({RANK}) {self.name} consume until {ts}, keeptime={new_chan_keeptime}"
        )
        for ts in range(prev_chan_keeptime, new_chan_keeptime):
            logger.debug(f"({RANK}) {self.name} deleting item at {ts}")
            del self.channel_data[ts]

    def advancetime(self) -> int:
        _, ts = self._writers_advancetime.peek()
        return ts

    def set_writer_advancetime(self, writer_name: str, ts: int):
        self._writers_advancetime[writer_name] = ts

    def handle_advance_until(self, writer: str, ts: int):
        prev_chan_advancetime = self.advancetime()
        self.set_writer_advancetime(writer, ts)
        new_chan_advancetime = self.advancetime()
        if new_chan_advancetime <= prev_chan_advancetime:
            return
        for reader in self.local_readers:
            reader.channel_advancetime = ts
        reqs: list[MPI.Request] = []
        msg = _Message_Writer_Advance(
            until=ts, writer_name=writer, channel_name=self.name
        )
        for rank_attached in self.reader_ranks:
            req = COMM.isend(obj=msg, dest=rank_attached, tag=STM_Tag.STM_DATA)
            reqs.append(req)
        logger.debug(
            f"({RANK}) publishing writer advancetime={new_chan_advancetime} to {len(reqs)} ranks"
        )
