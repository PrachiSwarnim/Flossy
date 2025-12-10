import asyncio
import websockets
import base64
import json
import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
import playsound

WS_URL = "ws://localhost:8765/ws/agent"
SAMPLE_RATE = 16000
CHANNELS = 1


def float_to_pcm16(arr):
    return (np.clip(arr, -1, 1) * 32767).astype(np.int16)


async def mic_sender(ws):
    q = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def callback(indata, frames, time, status):
        pcm = float_to_pcm16(indata[:, 0])
        raw = pcm.tobytes()
        loop.call_soon_threadsafe(q.put_nowait, raw)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=1600,
        callback=callback,
    )

    with stream:
        while True:
            raw = await q.get()
            b64 = base64.b64encode(raw).decode("ascii")
            await ws.send(json.dumps({"type": "audio_chunk", "data": b64}))


async def speaker_player(ws):
    buffer = []

    while True:
        msg = await ws.recv()
        data = json.loads(msg)
        typ = data.get("type")

        if typ == "bot_text":
            print("Bot:", data["text"])

        elif typ == "audio_chunk":
            buffer.append(base64.b64decode(data["data"]))

        elif typ == "audio_done":
            wav = b"".join(buffer)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp.write(wav)
            tmp.close()
            playsound.playsound(tmp.name)
            buffer = []


async def main():
    async with websockets.connect(WS_URL, max_size=None) as ws:
        sender = asyncio.create_task(mic_sender(ws))
        player = asyncio.create_task(speaker_player(ws))
        await asyncio.gather(sender, player)


if __name__ == "__main__":
    asyncio.run(main())
