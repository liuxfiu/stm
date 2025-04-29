# mpiexec -np 3 python -m examples.advance-spmd

from time import sleep
from stm.builder import STMBuilder
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

b = STMBuilder()
if rank == 0:
    b.create_channels(["ch1"])
    b.create_writer("ch1", f"ch1_writer_{rank}")
else:
    b.create_reader("ch1", f"ch1_reader_{rank}")

with b.build() as stm:
    if rank == 0:
        writer = stm.get_writer(f"ch1_writer_{rank}")
        writer.put(1, f"data({1})")
        writer.put(3, f"data({3})")
        writer.put(5, f"data({5})")
        writer.advance_until(3)
        print(f"({rank}) advance_until(3)")
        sleep(1)
        writer.put(7, f"data({7})")
    elif rank == 1:
        sleep(0.1)
        reader = stm.get_reader(f"ch1_reader_{rank}")
        print(f"({rank}) {reader.data._data}")
        print(f"({rank}) get(2)={reader.get(2)}")  # null and not possible
        print(f"({rank}) get(4)={reader.get(4)}")  # null and still possible
        print(f"({rank}) consume_until(4)")
        reader.consume_until(4)
        print(f"({rank}) {reader.data._data}")
        print(f"({rank}) get(4)={reader.get(4)}")  # null and not possible
        print(f"({rank}) get(7)={reader.get(7)}")  # null and still possible
    elif rank == 2:
        sleep(0.5)
        reader = stm.get_reader(f"ch1_reader_{rank}")
        print(f"({rank}) {reader.data._data}")
        print(f"({rank}) consume_until(3)")
        reader.consume_until(3)
        print(f"({rank}) {reader.data._data}")
        print(f"({rank}) get(7)={reader.get(7)}")  # null and still possible
        print(f"({rank}) sleeping...")
        sleep(0.6)
        print(f"({rank}) get(7)={reader.get(7)}")  # not null
