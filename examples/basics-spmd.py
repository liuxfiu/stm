# mpiexec -np 3 python -m examples.basics-spmd

from time import sleep
from stm.builder import STMBuilder
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

b = STMBuilder()
if rank == 0:
    b.create_channels(["ch1"])
    b.create_writer("ch1", "ch1_writer")
else:
    b.create_reader("ch1", f"ch1_reader_{rank}")

with b.build() as stm:
    if rank == 0:
        writer = stm.get_writer("ch1_writer")
        writer.put(1, "HELLO, THIS IS DATA")
    else:
        reader = stm.get_reader(f"ch1_reader_{rank}")
        sleep(0.1)
        print(f"({rank}) {reader.get(1)}")
        print(f"({rank}) {reader.get(2)}")
