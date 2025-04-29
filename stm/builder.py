from mpi4py import MPI

from .channel import _Channel
from .stm import _STM, _Reader, _Writer

from .log import logger
from .messaging import (
    _Message_STM_Channels_Init,
)

COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


class STMBuilder:
    def __init__(self):
        self._obj = _STM()
        self._channel_reader_names: dict[str, list[str]] = {}
        self._channel_writer_names: dict[str, list[str]] = {}

    def create_channels(self, channels: list[str]):
        # todo: check duplicates
        for channel in channels:
            self._obj._local_channels[channel] = _Channel(channel)
            self._obj._channel_rank[channel] = RANK
        return self

    def create_reader(self, channel_name: str, reader_name: str):
        channel_is_local = (
            channel_name in self._obj._local_channels
            and channel_name in self._obj._channel_rank
        )
        if channel_is_local:
            reader = _Reader(reader_name, channel_name, RANK)
            channel = self._obj._local_channels[channel_name]
            channel.local_readers.add(reader)
            channel.set_reader_keeptime(reader_name, 0)
            self._obj._readers_by_id[reader_name] = reader
        else:
            # we don't know the rank at this point, so save for later
            self._channel_reader_names.setdefault(channel_name, [])
            self._channel_reader_names[channel_name].append(reader_name)
        return self

    def create_writer(self, channel_name: str, writer_name: str):
        channel_is_local = (
            channel_name in self._obj._local_channels
            and channel_name in self._obj._channel_rank
        )
        if channel_is_local:
            channel = self._obj._local_channels[channel_name]
            channel.set_writer_advancetime(writer_name, 0)
            writer = _Writer(writer_name, channel_name, RANK)
            self._obj._writers_by_id[writer_name] = writer
        else:
            # we don't know the rank at this point, so save for later
            self._channel_writer_names.setdefault(channel_name, [])
            self._channel_writer_names[channel_name].append(writer_name)
        return self

    def _distribute_channel_ranks(self):
        # share all channel locations (source ranks)
        channel_msgs = _Message_STM_Channels_Init(
            channels=list(self._obj._local_channels.keys()), source_rank=RANK
        )
        rank_ready_messages = COMM.allgather(channel_msgs)
        logger.debug(f"({RANK}) ready msgs = {rank_ready_messages}")
        for msg in rank_ready_messages:
            for channel_name in msg.channels:
                self._obj._channel_rank[channel_name] = msg.source_rank

    def _distribute_readers_metadata(self):
        # initialize readers that are attached to remote channels
        # (this is a bit more involved since channels push data to readers)
        # each rank has a list of attached readers, which are each represented as a tuple
        # we will be distributing attachment data with alltoall,
        #   each rank is assigned a list of reader tuples.
        #   we declare a reader by putting its metadata in the list for the rank we want to send it to
        #   after alltoall, each channels will know the rank where each reader is located
        reader_rank_attachments: list[list[tuple[str, str]]] = [[] for _ in range(SIZE)]
        for channel_name, reader_names in self._channel_reader_names.items():
            channel_rank = self._obj._channel_rank[channel_name]
            # create reader objects
            for reader_name in reader_names:
                reader = _Reader(reader_name, channel_name, channel_rank)
                self._obj._readers_by_id[reader_name] = reader
                self._obj._readers_by_channel.setdefault(channel_name, [])
                self._obj._readers_by_channel[channel_name].append(reader)
                # note the ranks that this reader has attachments to
                reader_rank_attachments[channel_rank].append(
                    (channel_name, reader_name)
                )
        # distribute reader attachment information
        reader_connection_msgs = COMM.alltoall(reader_rank_attachments)
        logger.debug(f"({RANK}) reader connection msgs = {reader_connection_msgs}")
        for source_rank, connections in enumerate(reader_connection_msgs):
            for channel_name, reader_name in connections:
                channel = self._obj._local_channels[channel_name]
                channel.reader_ranks.add(source_rank)
                channel._readers_keeptime[reader_name] = 0

    def _distribute_writers_metadata(self):
        # a similar setup for writers, but for a different reason
        # each channel needs to know the advance time for each of its writers
        writer_rank_attachments: list[list[tuple[str, str]]] = [[] for _ in range(SIZE)]
        for channel_name, writer_names in self._channel_writer_names.items():
            channel_rank = self._obj._channel_rank[channel_name]
            for writer_name in writer_names:
                writer = _Writer(writer_name, channel_name, channel_rank)
                self._obj._writers_by_id[writer_name] = writer
                writer_rank_attachments[channel_rank].append(
                    (channel_name, writer_name)
                )
        # distribute writer attachment information
        writer_connection_msgs = COMM.alltoall(writer_rank_attachments)
        logger.debug(f"({RANK}) writer connection msgs = {writer_connection_msgs}")
        for source_rank, connections in enumerate(writer_connection_msgs):
            for channel_name, writer_name in connections:
                channel = self._obj._local_channels[channel_name]
                channel._writers_advancetime[writer_name] = 0

    def build(self):
        if not self._obj:
            raise Exception("Builder cannot be reused")

        self._distribute_channel_ranks()

        # todo: check for bad channel names in connections
        self._distribute_readers_metadata()
        self._distribute_writers_metadata()

        logger.info(
            f"({RANK}) finished build with channel keeptimes = {
                [(key, channel._readers_keeptime[key]) 
                 for channel in self._obj._local_channels.values() 
                 for key in channel._readers_keeptime]
            }"
        )

        obj = self._obj
        self._obj = None
        return obj
