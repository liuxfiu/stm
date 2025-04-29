# mpiexec -np 1 python -m examples.basics

from stm import STMBuilder

builder = (
    STMBuilder()
    .create_channels(["ch1"])
    .create_reader("ch1", "ch1_reader")
    .create_writer("ch1", "ch1_writer")
)
stm = builder.build()
stm.start("thread")

reader = stm.get_reader("ch1_reader")
writer = stm.get_writer("ch1_writer")

writer.put(1, "HELLO, THIS IS DATA")
print(reader.get(1))

stm.stop()
