import React, { useEffect, useState, useRef } from "react";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    BarVisualizer,
    useVoiceAssistant,
    useConnectionState,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import "@livekit/components-styles";
import "../styles/voice_call.css";

const SERVER_URL = "wss://flossy-pmhj3sdw.livekit.cloud";

export default function LiveKitVoiceModal({ isOpen, onClose, userName, userEmail }) {
    const [token, setToken] = useState("");

    useEffect(() => {
        if (isOpen) {
            fetch(`http://localhost:8000/api/token?name=${encodeURIComponent(userName)}&email=${encodeURIComponent(userEmail)}`)
                .then((res) => res.json())
                .then((data) => setToken(data.accessToken))
                .catch((err) => console.error("Failed to get LiveKit token", err));
        } else {
            setToken("");
        }
    }, [isOpen, userName]);

    if (!isOpen) return null;

    return (
        <div className="voice-call-overlay">
            <div className="voice-call-container" style={{ width: "400px", height: "500px" }}>
                <div className="call-header">
                    <span className="secure-badge"><i className="fas fa-shield-alt"></i> Secure AI</span>
                    <button className="close-x-btn" onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none", color: "white", fontSize: "1.2rem", cursor: "pointer" }}>
                        <i className="fas fa-times"></i>
                    </button>
                </div>

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
    const roomState = useConnectionState();
    const audioCtxRef = useRef(null);
    const oscRef = useRef(null);

    // Ringing sound removed for performance stability
    // The "Calling..." visual status is sufficient and avoids WebAudio conflicts.
    useEffect(() => {
        // Optional: We could play a simple HTML5 audio file here if needed in future
    }, [roomState]);

    return (
        <div className="orb-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
            <div className="orb" style={{ boxShadow: state === "speaking" ? "0 0 30px #00d2ff" : "none" }}>
                <div className="orb-core"></div>
                {audioTrack && (
                    <div style={{ height: "50px", width: "200px", marginTop: "20px" }}>
                        <BarVisualizer state={state} trackRef={audioTrack} barCount={5} options={{ minHeight: 10, maxHeight: 40 }} />
                    </div>
                )}
            </div>

            <div className="call-status" style={{ textAlign: "center" }}>
                <h3>FlossyAI</h3>
                <p>
                    {roomState === ConnectionState.Connecting ? "Calling..." :
                        state === "listening" ? "Listening..." :
                            state === "speaking" ? "Speaking..." :
                                "Connected"}
                </p>
            </div>
        </div>
    );
}
