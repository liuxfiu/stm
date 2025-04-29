# mpiexec -np 3 python -m examples.manual-mode

from time import sleep
from mpi4py import MPI

from stm.builder import STMBuilder
from stm.stm import _STM


comm = MPI.COMM_WORLD
rank = comm.Get_rank()


class PDESEngine:
    def __init__(self, stm: _STM):
        self.msg_request = None
        self.stm = stm
        self.stm.start("manual")

    def process_messages(self):
        if not self.msg_request:
            self.msg_request = self.stm.receive_message()
        ready = self.msg_request.get_status()
        while ready:
            msg = self.msg_request.wait()
            self.stm.process_message(msg)
            self.msg_request = self.stm.receive_message()
            ready = self.msg_request.get_status()


b = STMBuilder()
if rank == 0:
    b.create_channels(["ch1"])
    b.create_writer("ch1", f"ch1_writer_{rank}")
else:
    b.create_reader("ch1", f"ch1_reader_{rank}")
stm = b.build()

pdes = PDESEngine(stm)

if rank > 0:
    sleep(1)

for i in range(2, 10):
    pdes.process_messages()

    if rank == 0:
        writer = stm.get_writer(f"ch1_writer_{rank}")
        writer.put(i, f"data({i})")
        print(f"({rank}) put({i})")
        writer.advance_until(i)
    else:
        reader = stm.get_reader(f"ch1_reader_{rank}")
        print(f"({rank}) time={i} get({i - 1})={reader.get(i - 1)}")
        reader.consume_until(i - 1)


stm.stop()
