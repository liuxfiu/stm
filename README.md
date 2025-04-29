# STM - Space Time Memory

## Table of Contents

- [Basic Usage](#basic-usage)
- [STMBuilder Methods](#stmbuilder-methods)
  - [.create_channels](#create_channels)
  - [.create_reader](#create_reader)
  - [.create_writer](#create_writer)
  - [.build](#build)
- [STM Methods](#stm-methods)
  - [.get_reader](#get_reader)
  - [.get_writer](#get_writer)
  - [.start](#start)
  - [.stop](#stop)
  - [Manual mode](#manual-mode)
    - [.receive_message](#receive_message)
    - [.check_shutdown](#check_shutdown)
    - [.process_message](#process_message)
    - [Example Usage](#manual-mode-example-usage)
- [Reader Methods](#reader-methods)
  - [.get](#get)
  - [.consume_until](#consume_until)
  - [Not Yet Implemented](#not-yet-implemented)
    - [.get_all](#get_all)
    - [.get_first](#get_first)
    - [.get_last](#get_last)
- [Writer Methods](#writer-methods)
  - [.put](#put)
  - [.advance_until](#advance_until)

## Basic Usage

Building a single STM instance with channels and connections

```python
stm = (
    STMBuilder()
    .create_channels(["ch1"])
    .create_reader("ch1", "ch1_reader")
    .create_writer("ch1", "ch1_writer")
    .build()
)
```

Reading/Writing from a channel

```python
stm.start()

reader = stm.get_reader("ch1_reader")
writer = stm.get_writer("ch1_writer")

writer.put(1, "DATA STRING")
print(reader.get(1)) # prints: "DATA STRING"

stm.stop()
```

Or using a context manager

```python
with stm:
    reader = s.get_reader("ch1_reader")
    writer = s.get_writer("ch1_writer")
    writer.put(1, "DATA STRING")
    print(reader.get(1)) # prints: "DATA STRING"
```

## STMBuilder Methods

### `.create_channels`

`create_channels(channels: list[str])`

Instatiates new channels that will live in the `_STM` instance being built.

- **Args**:
  - `channels: list[str]` - A list of names for each new channel. One new `_Channel` object will be instantiated for each name given, and will be stored in the `_STM` instance being built. Each channel's name **must** be unique among **all** channels.
- **Returns**: `STMBuilder`

### `.create_reader`

`create_reader(channel_name: str, reader_name: str)`

Declares a reader, local to this `_STM` instance, that will be attached to `channel_name`.

- **Args**:
  - `channel_name: str` - The name of a channel.
  - `reader_name: str` - The unique identifier that will be assigned to this reader. **Must** be unique.
- **Returns**: `STMBuilder`

### `.create_writer`

`create_writer(channel_name: str, writer_name: str)`

Declares a writer, local to this `_STM` instance, that will be attached to `channel_name`.

- **Args**:
  - `channel_name: str` - The name of a channel.
  - `writer_name: str` - The unique identifier that will be assigned to this writer. **Must** be unique.
- **Returns**: `STMBuilder`

### `.build`

Finalizes the `STMBuilder` and constructs the STM object.

This is a blocking operation. For synchronizing purposes, the builder will block until all other ranks have called `.build` on their `STMBuilder`.

- **Returns**: `_STM` - The constructed STM object.
- **Raises**:
  - `Exception` - If the builder is reused after an STM instance has already been built.

## STM Methods

### `.get_reader`

`get_reader(name: str)`

Retrieves a reader by its name.

- **Args**:
  - `name: str` - The name of the reader.
- **Returns**: `_Reader` - The reader object associated with the given name.

### `.get_writer`

`get_writer(name: str)`

Retrieves a writer by its name.

- **Args**:
  - `name: str` - The name of the writer.
- **Returns**: `_Writer` - The writer object associated with the given name.

### `.start`

`start(listening_mode: Literal["thread", "manual"] = "thread")`

Starts the STM instance in the specified listening mode. This method is called automatically when using a context manager.

- **Args**:
  - `listening_mode (Literal["thread", "manual"])` - The mode of listening for messages:
    - `"thread"`: Starts a background thread for message processing. This is the default behavior.
    - `"manual"`: Noop.
- **Raises**:
  - `ValueError` - If an invalid listening mode is provided.

### `.stop`

Broadcasts a shutdown message to all STM instances (including this one), notifying them that this STM instance is ready to shutdown.

Once all STM instances call `.stop`, then `.check_shutdown` will return `True`. If automatic message processing is being used (the default), then all STM instances will stop listening for messages and the background threads will be destroyed.

### Manual Mode

By default, STM starts in "thread" mode, where it launches a Python thread that listens for messages asynchronously. However, for some applications (like PDES), launching background threads may not be desired. Therefore, STM also supports manual message handling with the following methods.

#### `.receive_message`

`receive_message()`

Receives a message from the STM instance. This method is used in manual mode to retrieve messages for processing.

- **Returns**:
  - `MPI.Request` - An MPI request object from the `mpi4py` library that can be waited on to retrieve the message.

For more information on `MPI.Request`, refer to the [mpi4py documentation](https://mpi4py.readthedocs.io/en/stable/).

#### `.check_shutdown`

`check_shutdown(msg: Any) -> bool`

Uses an incoming message to determine if this STM instance is ready to fully shut down.

- **Args**:
  - `msg: Any` - The most recent message received.
- **Returns**:
  - `bool` - `True` if the message is a shutdown signal and all STM instances have already sent their shutdown signals, indicating that this instance is ready to clean up and shut down completely. Otherwise, `False`.

#### `.process_message`

`process_message(msg: Any)`

Processes an incoming message received by the STM instance. This method is used to handle various types of messages, such as data updates, reader consumption requests, writer advancement notifications, and shutdown signals.

- **Args**:

  - `msg: Any` - The message to process. The type of the message determines the action taken.

For more details, refer to the implementation in the `_STM` class in `stm.py`.

#### Manual Mode Example Usage

```python
while True:
    msg = stm.receive_message().wait()
    if stm.check_shutdown(msg):
        print("shutting down...")
        break
    stm.process_message(msg)
```

## Reader Methods

### `.get`

`get(ts: int)`

Retrieves data for a specific timestamp.

- **Args**:
  - `ts: int` - The timestamp to retrieve data for.
- **Returns**:
  - `tuple[Any, bool]` - A tuple containing the data (or `None`) and a boolean indicating whether the data could potentially be present in a future call. If the boolean is `False`, then a future call of `get` at the same timestamp will never return anything different. Internally, this means the channel's "advance_time" has reached `ts`.

### `.consume_until`

`consume_until(time: int)`

Consumes data up to, and including, a specified timestamp.

- **Args**:
  - `time: int` - The timestamp up to which data should be consumed on this connection.

### Not Yet Implemented

### `.get_all`

`.get_all(until: str)`

Retrieves all data available in the channel that has a timestamp <= `until`

- **Args**:
  - `until: int` - The maximum timestamp for data.
- **Returns**:
  - `list[tuple[Any, bool]]` - A list of results of calling `get` for all possible timestamps that are <= `until`, but >= the reader's "consume_time".

### `.get_first`

`get_first()`

Retrieves the first available data for a timestamp greater than or equal to the reader's consume time.

- **Returns**:
  - `tuple[Any, bool]` - A tuple containing the data (or `None`) and a boolean indicating whether the data could potentially be present in a future call.

### `.get_last`

`get_last()`

Retrieves the latest available data for a timestamp greater than or equal to the reader's consume.

- **Returns**:
  - `tuple[Any, int]` - A tuple containing the data and the timestamp it is from.

## Writer Methods

### `.put`

`put(ts: int, item: Any)`

Puts data into the channel at a specific timestamp.

- **Args**:
  - `ts: int` - The timestamp for the data.
  - `item: Any` - The data to be added to the channel.

### `.advance_until`

`advance_until(ts: int)`

Advances the writer's time to a specified timestamp.
This is used to advance the channel's "advance_time", which is a measure of the minimum possible timestamp any writer could write to, which is important for synchronizing readers and writers.

- **Args**:
  - `ts: int` - The timestamp to advance to.
