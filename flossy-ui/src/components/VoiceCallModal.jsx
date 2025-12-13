import React, { useEffect, useState } from "react";
import { useVoiceAgent } from "../hooks/useVoiceAgent";
import "../styles/voice_call.css";

export default function VoiceCallModal({ isOpen, onClose, userName }) {
    const { isListening, isAgentSpeaking, start, stop, connect } = useVoiceAgent();
    const [duration, setDuration] = useState(0);

    // Auto-start call when opened
    useEffect(() => {
        if (isOpen) {
            start();
            const timer = setInterval(() => setDuration((prev) => prev + 1), 1000);
            return () => {
                stop();
                clearInterval(timer);
                setDuration(0);
            };
        }
    }, [isOpen]);

    const formatTime = (sec) => {
        const m = Math.floor(sec / 60).toString().padStart(2, "0");
        const s = (sec % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    };

    if (!isOpen) return null;

    return (
        <div className="voice-call-overlay">
            <div className="voice-call-container">
                {/* HEADER */}
                <div className="call-header">
                    <span className="secure-badge"><i className="fas fa-shield-alt"></i> Secure Line</span>
                    <span className="call-timer">{formatTime(duration)}</span>
                    <button className="close-x-btn" onClick={onClose} style={{
                        background: "transparent", border: "none", color: "rgba(255,255,255,0.5)", fontSize: "1.2rem", cursor: "pointer", marginLeft: "auto"
                    }}>
                        <i className="fas fa-times"></i>
                    </button>
                </div>

                {/* VISUALIZER */}
                <div className="orb-container">
                    <div className={`orb ${isAgentSpeaking ? "speaking" : "listening"}`}>
                        <div className="orb-core"></div>
                        <div className="orb-ring r1"></div>
                        <div className="orb-ring r2"></div>
                        <div className="orb-ring r3"></div>
                    </div>
                </div>

                {/* STATUS */}
                <div className="call-status">
                    <h3>FlossyAI Assistant</h3>
                    <p>
                        {isAgentSpeaking
                            ? "Speaking..."
                            : isListening
                                ? "Listening..."
                                : "Connecting..."}
                    </p>
                </div>

                {/* CONTROLS */}
                <div className="call-controls">
                    <button className="control-btn mute-btn" title="Mute (Coming Soon)">
                        <i className="fas fa-microphone-slash"></i>
                    </button>

                    <button className="control-btn hangup-btn" onClick={onClose}>
                        <i className="fas fa-phone-slash"></i>
                    </button>
                </div>
            </div>
        </div>
    );
}
