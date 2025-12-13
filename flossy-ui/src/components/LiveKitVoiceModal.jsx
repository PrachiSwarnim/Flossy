import React, { useEffect, useState } from "react";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    BarVisualizer,
    useVoiceAssistant,
} from "@livekit/components-react";
import "@livekit/components-styles";
import "../styles/voice_call.css"; // Reuse existing styles or add new ones

const SERVER_URL = "wss://flossy-pmhj3sdw.livekit.cloud"; // From your .env

export default function LiveKitVoiceModal({ isOpen, onClose, userName }) {
    const [token, setToken] = useState("");

    useEffect(() => {
        if (isOpen) {
            // Fetch Token from Backend
            fetch(`http://localhost:8000/api/token?name=${encodeURIComponent(userName)}`)
                .then((res) => res.json())
                .then((data) => setToken(data.accessToken))
                .catch((err) => console.error("Failed to get LiveKit token", err));
        } else {
            setToken(""); // Disconnect on close
        }
    }, [isOpen, userName]);

    if (!isOpen) return null;

    return (
        <div className="voice-call-overlay">
            <div className="voice-call-container" style={{ width: "400px", height: "500px" }}>
                {/* Header */}
                <div className="call-header">
                    <span className="secure-badge"><i className="fas fa-shield-alt"></i> Secure AI</span>
                    <button className="close-x-btn" onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none", color: "white", fontSize: "1.2rem", cursor: "pointer" }}>
                        <i className="fas fa-times"></i>
                    </button>
                </div>

                {/* LiveKit Room */}
                {token ? (
                    <LiveKitRoom
                        video={false}
                        audio={true}
                        token={token}
                        serverUrl={SERVER_URL}
                        data-lk-theme="default"
                        style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}
                        onDisconnected={onClose}
                    >
                        <SimpleVoiceInterface />
                        <RoomAudioRenderer />
                    </LiveKitRoom>
                ) : (
                    <div className="call-status">Loading secure connection...</div>
                )}
            </div>
        </div>
    );
}

function SimpleVoiceInterface() {
    const { state, audioTrack } = useVoiceAssistant();

    return (
        <div className="orb-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
            {/* Visualizer */}
            <div className="orb" style={{ boxShadow: state === "speaking" ? "0 0 30px #00d2ff" : "none" }}>
                <div className="orb-core"></div>
                {/* LiveKit Bar Visualizer can go here if track is available */}
                {audioTrack && (
                    <div style={{ height: "50px", width: "200px", marginTop: "20px" }}>
                        <BarVisualizer state={state} trackRef={audioTrack} barCount={5} options={{ minHeight: 10, maxHeight: 40 }} />
                    </div>
                )}
            </div>

            {/* Status Text */}
            <div className="call-status" style={{ textAlign: "center" }}>
                <h3>FlossyAI</h3>
                <p>{state === "listening" ? "Listening..." : state === "speaking" ? "Speaking..." : "Thinking..."}</p>
            </div>
        </div>
    );
}
