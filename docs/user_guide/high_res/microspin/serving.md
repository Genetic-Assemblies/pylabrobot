# Serving a MicroSpin

A MicroSpin can be served where it is plugged in and driven from anywhere else, with the same
`MicroSpin` class and methods. Its body, rotor and buckets live on a resource server, which other
device servers in the same workcell can share, so a plate a robot puts in a bucket is a plate in
one tree that every device and client sees.

## The processes

Each runs where it suits: the resource server anywhere on the network, the MicroSpin server on a
machine that reaches the device.

One shared resource server, holding the workcell's tree in memory:

```sh
python -m pylabrobot.resources.server --host 0.0.0.0 --port 8080
```

The MicroSpin server, keeping the device's resources on it:

```sh
python -m pylabrobot.high_res.microspin.server \
  --device 192.168.127.60 --name microspin \
  --resource-server http://lab-resources:8080 \
  --host 0.0.0.0 --port 8082 --settings-json microspin_settings.json
```

`--simulation` in place of `--device` serves a simulated MicroSpin. `microspin_settings.json` is
optional: it holds the defaults the device uses where a call names none, and anything left out
keeps the code's.

```json
{"default_acceleration": 0.8, "default_spindle_stop_timeout": 900}
```

Another device server started with `--resource-server http://lab-resources:8080` keeps its
resources in the same tree.

## A client

```python
from pylabrobot.high_res.microspin import MicroSpin

cf = MicroSpin(
  microspin_server="http://lab-cf:8082", resource_server="http://lab-resources:8080"
)
await cf.setup()               # takes up the body, rotor and buckets the server keeps
print(cf.settings.default_acceleration)  # 0.8: the server's, and not assignable here

await cf.home()
await cf.present_bucket(1)
bucket = await cf.get_bucket_at_door()   # read off the shared tree
```

Put a plate in each bucket, by robot or by hand. On the resource server, that is a plate assigned
to the bucket:

```python
await cf.resource_server.create("cor_96_wellplate_360uL_Fb", name="lysate_1", parent=cf.buckets[1])
await cf.resource_server.create("cor_96_wellplate_360uL_Fb", name="lysate_2", parent=cf.buckets[2])
```

`spin` returns when the rotor has stopped, as it does in-process:

```python
await cf.spin(g=3000, duration=20 * 60)
```

`stream_spin` yields what the spin is doing as the server reads the spindle, ending with the spin
finished:

```python
from pylabrobot.high_res.microspin.server.v1 import microspin_pb2 as mpb

request_id = (42).to_bytes(8, "big")
async for update in cf.stream_spin(g=3000, duration=20 * 60, request_id=request_id):
  print(f"{update.elapsed:6.0f} s  {update.rpm:6.0f} rpm")
  if update.phase == mpb.SPIN_PHASE_FINISHED and update.HasField("error"):
    print("failed:", update.error.message)
```

The server owns the spin. If the network drops, the stream is asked for again by its request id:
the server does not start the spin twice, and it carries on whether or not anyone is listening.
Any other client can follow it by its id:

```python
other = MicroSpin(
  microspin_server="http://lab-cf:8082", resource_server="http://lab-resources:8080"
)
async for update in other.watch_spin(request_id):
  print(update.phase, update.rpm)
```

What the device raises, the client raises, as the same class: `DoorLockPinError`, `NotHomedError`,
a `ValueError` for an unbalanced rotor.

## Credentials

If the servers sit behind something that asks for credentials, connect with headers, which go with
every call:

```python
from pylabrobot.high_res.microspin.server import MicroSpinServer
from pylabrobot.resources.server import ResourceServer

auth = {"authorization": "Bearer <token>"}
cf = MicroSpin(
  microspin_server=MicroSpinServer.connect("https://lab.example/microspin", headers=auth),
  resource_server=ResourceServer.connect("https://lab.example/resources", headers=auth),
)
```

## Other languages

The service is `MicroSpinService` in
[`v1/microspin.proto`](https://github.com/PyLabRobot/pylabrobot/blob/main/pylabrobot/high_res/microspin/server/v1/microspin.proto),
one call per public method of `MicroSpin`. A client in any language with Connect or gRPC-Web
bindings uses the same service; a spin's `request_id` is 1 to 16 bytes, an integer's big-endian
bytes or a UUID's 16.
