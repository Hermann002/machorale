from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import asyncio

layer = get_channel_layer()

async def test_round_trip():
    # Envoi puis lecture immédiate, le tout async.
    await layer.send("test-channel", {"type": "hello", "data": 1})
    # wait_for : si rien en 2s, lève TimeoutError au lieu de bloquer.
    msg = await asyncio.wait_for(layer.receive("test-channel"), timeout=2.0)
    return msg

result = async_to_sync(test_round_trip)()
print(result)