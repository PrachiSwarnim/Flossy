import React, { useEffect, useState, useRef } from "react";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    BarVisualizer,
    useVoiceAssistant,
    useConnectionState,
    useRoomContext,
} from "@livekit/components-react";
import { ConnectionState, RoomEvent } from "livekit-client";
import "@livekit/components-styles";
import "../styles/voice_call.css";

const SERVER_URL = "wss://flossy-pmhj3sdw.livekit.cloud";

export default function LiveKitVoiceInline({ isActive, onLeave, userName, userEmail, onAppointmentBooked }) {
    const [token, setToken] = useState("");
    // Actually hooks like useVoiceAssistant must be inside LiveKitRoom, so we can't use them here yet.
    // Let's stick to the structure: Parent handles Token, Child handles Room logic.

    useEffect(() => {
        if (isActive) {
            fetch(`http://localhost:8000/api/token?name=${encodeURIComponent(userName)}&email=${encodeURIComponent(userEmail)}`)
                .then((res) => res.json())
                .then((data) => setToken(data.accessToken))
                .catch((err) => console.error("Failed to get LiveKit token", err));
        } else {
            setToken("");
        }
    }, [isActive, userName, userEmail]);

    if (!isActive) return null;

    return (
        <div className="voice-inline-container" style={{
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            background: "linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)",
            borderRadius: "0",
            overflow: "hidden",
            position: "relative"
        }}>
            {/* Header Removed for Sidebar Integration */}

            {token ? (
                <LiveKitRoom
                    video={false}
                    audio={true}
                    token={token}
                    serverUrl={SERVER_URL}
                    data-lk-theme="default"
                    style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}
                    onDisconnected={onLeave}
                >
                    <SimpleVoiceInterfaceInline onAppointmentBooked={onAppointmentBooked} />
                    <RoomAudioRenderer />
                </LiveKitRoom>
            ) : (
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#888" }}>
                    Connecting to secure line...
                </div>
            )}
        </div>
    );
}

function SimpleVoiceInterfaceInline({ onAppointmentBooked }) {
    const { state, audioTrack } = useVoiceAssistant();
    const roomState = useConnectionState();
    const room = useRoomContext();

    // Listen for Real-time Data Messages (e.g. "APPOINTMENT_BOOKED")
    useEffect(() => {
        if (!room) return;

        const handleData = (payload, participant, kind) => {
            const str = new TextDecoder().decode(payload);
            console.log("📨 Voice Data Message:", str);
            if (str === "APPOINTMENT_BOOKED") {
                if (onAppointmentBooked) {
                    console.log("🔄 Triggering Dashboard Refresh...");
                    onAppointmentBooked();
                }
            }
        };

        room.on(RoomEvent.DataReceived, handleData);
        return () => {
            room.off(RoomEvent.DataReceived, handleData);
        };
    }, [room, onAppointmentBooked]);

    // Ringing Sound Logic - Placed INSIDE the Voice Interface where roomState is available
    useEffect(() => {
        if (roomState === ConnectionState.Connecting) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;

            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.frequency.value = 440; // A4
            osc.type = "sine";

            // Modulation for Warble effect
            const lfo = ctx.createOscillator();
            lfo.frequency.value = 15;
            const lfoGain = ctx.createGain();
            lfoGain.gain.value = 50;

            lfo.connect(lfoGain);
            lfoGain.connect(osc.frequency);

            osc.connect(gain);
            gain.connect(ctx.destination);

            // Pulse: Rings for 2s then fades
            const now = ctx.currentTime;
            gain.gain.setValueAtTime(0.05, now);
            gain.gain.setValueAtTime(0.05, now + 1.8);
            gain.gain.linearRampToValueAtTime(0, now + 2.0);

            osc.start();
            lfo.start();

            return () => {
                try {
                    osc.stop();
                    lfo.stop();
                    ctx.close();
                } catch (e) { }
            };
        }
    }, [roomState]);

    return (
        <div className="orb-container-inline" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "15px" }}>
            <div className="orb small" style={{
                width: "80px",
                height: "80px",
                borderRadius: "50%",
                background: state === "speaking" ? "radial-gradient(circle, #00d2ff 0%, #005f73 100%)" : "radial-gradient(circle, #f0b800 0%, #b8860b 100%)",
                boxShadow: state === "speaking" ? "0 0 20px #00d2ff" : "0 0 15px rgba(240, 184, 0, 0.3)",
                margin: "0 auto",
                transition: "all 0.3s ease",
                animation: state === "listening" ? "pulse 2s infinite" : "none"
            }}>
            </div>

            {audioTrack && (
                <div style={{ height: "30px", width: "120px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <BarVisualizer state={state} trackRef={audioTrack} barCount={4} options={{ minHeight: 5, maxHeight: 25, color: "#f0b800" }} />
                </div>
            )}

            <div className="status-text" style={{ textAlign: "center", color: "#ccc", fontSize: "0.9rem" }}>
                {roomState === ConnectionState.Connecting ? "Calling..." :
                    state === "listening" ? "Listening..." :
                        state === "speaking" ? "Speaking..." :
                            "Connected"}
            </div>
        </div>
    );
}
