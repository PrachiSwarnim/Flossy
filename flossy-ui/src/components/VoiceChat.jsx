import { useEffect, useState, useRef } from "react";
import { Mic, MicOff, PhoneOff, ShieldCheck } from "lucide-react";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    useRoomContext,
    useConnectionState,
} from "@livekit/components-react";
import { createPortal } from "react-dom";
import { ConnectionState, RoomEvent } from "livekit-client";

/* -------------------- STYLES -------------------- */
const css = `
.voice-close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.voice-close:hover {
  background: rgba(255,255,255,0.18);
}

.voice-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.65);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 99999;
}
.voice-card {
  width: 320px;
  height: 560px;
  background: #0b0b0b;
  border-radius: 22px;
  padding: 20px;
  color: white;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.voice-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.secure {
  display: flex;
  gap: 6px;
  color: #00e676;
}
.orb {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  margin: 30px auto;
  background: radial-gradient(circle,#f5c84c,#9e7c19);
}
.orb.connecting { opacity:.5; animation:pulse 2s infinite; }
.orb.listening { animation:pulse 2s infinite; }
.orb.speaking { animation:speak .8s infinite; }

@keyframes pulse {
  0%{transform:scale(1)}
  50%{transform:scale(1.07)}
  100%{transform:scale(1)}
}
@keyframes speak {
  0%{transform:scale(1)}
  50%{transform:scale(1.2)}
  100%{transform:scale(1)}
}

.controls {
  display:flex;
  justify-content:center;
  gap:20px;
}
.controls button {
  width:54px;
  height:54px;
  border-radius:50%;
  border:none;
  cursor:pointer;
}
.mute { background:#333;color:white }
.end { background:#e53935;color:white }
`;

/* -------------------- INNER UI -------------------- */
function VoiceUI({ onClose, timer }) {
    const room = useRoomContext();
    const connection = useConnectionState();

    const ringRef = useRef(null);
    const analyserRef = useRef(null);

    const [muted, setMuted] = useState(false);
    const [agentSpeaking, setAgentSpeaking] = useState(false);
    const [agentEverSpoke, setAgentEverSpoke] = useState(false);

    /* 🎧 Detect agent audio energy */
    useEffect(() => {
        if (!room) return;

        const ctx = new AudioContext();
        analyserRef.current = ctx.createAnalyser();
        analyserRef.current.fftSize = 512;

        const data = new Uint8Array(analyserRef.current.frequencyBinCount);

        const handleTrack = (track) => {
            if (track.kind !== "audio") return;
            const src = ctx.createMediaStreamSource(
                new MediaStream([track.mediaStreamTrack])
            );
            src.connect(analyserRef.current);
        };

        room.on(RoomEvent.TrackSubscribed, handleTrack);

        const interval = setInterval(() => {
            if (!analyserRef.current) return;
            analyserRef.current.getByteFrequencyData(data);
            const avg = data.reduce((a, b) => a + b, 0) / data.length;

            const speaking = avg > 8;
            setAgentSpeaking(speaking);

            if (speaking) {
                setAgentEverSpoke(true);
            }
        }, 120);

        return () => {
            clearInterval(interval);
            room.off(RoomEvent.TrackSubscribed, handleTrack);
            ctx.close();
        };
    }, [room]);

    /* 🔔 Ring UNTIL agent actually speaks */
    useEffect(() => {
        if (!ringRef.current) return;

        if (!agentEverSpoke) {
            ringRef.current.loop = true;
            ringRef.current.volume = 0.4;
            ringRef.current.play().catch(() => { });
        } else {
            ringRef.current.pause();
            ringRef.current.currentTime = 0;
        }
    }, [agentEverSpoke]);

    const toggleMute = async () => {
        if (!room?.localParticipant) return;
        const next = !muted;
        setMuted(next);
        await room.localParticipant.setMicrophoneEnabled(!next);
    };

    const format = (s) =>
        `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(
            2,
            "0"
        )}`;

    const orbState = !agentEverSpoke
        ? "connecting"
        : agentSpeaking
            ? "speaking"
            : "listening";

    return (
        <div className="voice-card">
            <button
                className="voice-close"
                aria-label="Close voice chat"
                onClick={onClose}
            >
                ✕
            </button>

            <audio ref={ringRef} src="/sounds/phone-ringing.mp3" />

            <div className="voice-header">
                <div className="secure">
                    <ShieldCheck size={14} /> Secure Line
                </div>
                <div>{format(timer)}</div>
            </div>

            <div className={`orb ${orbState}`} />

            <h2 style={{ color: "#f5c84c" }}>FlossyAI Assistant</h2>
            <p>
                {!agentEverSpoke
                    ? "CONNECTING…"
                    : agentSpeaking
                        ? "SPEAKING…"
                        : "LISTENING…"}
            </p>

            <div className="controls">
                <button className="mute" onClick={toggleMute}>
                    {muted ? <MicOff /> : <Mic />}
                </button>
                <button className="end" onClick={onClose}>
                    <PhoneOff />
                </button>
            </div>

            <RoomAudioRenderer />
        </div>
    );
}

/* -------------------- OUTER -------------------- */
export default function VoiceChat({ onClose }) {
    const [token, setToken] = useState(null);
    const [timer, setTimer] = useState(0);

    useEffect(() => {
        const style = document.createElement("style");
        style.innerHTML = css;
        document.head.appendChild(style);
        return () => style.remove();
    }, []);

    useEffect(() => {
        fetch(`${import.meta.env.VITE_API_BASE_URL}/api/generate-token`, {
            method: "POST",
        })
            .then((r) => r.json())
            .then((d) => setToken(d.token));

        const id = setInterval(() => setTimer((t) => t + 1), 1000);
        return () => clearInterval(id);
    }, []);

    if (!token) return null;

    return createPortal(
        <div className="voice-overlay">
            <LiveKitRoom
                token={token}
                serverUrl={import.meta.env.VITE_LIVEKIT_URL}
                audio
                video={false}
                onDisconnected={onClose}
            >
                <VoiceUI onClose={onClose} timer={timer} />
            </LiveKitRoom>
        </div>,
        document.getElementById("voice-root")
    );
}
