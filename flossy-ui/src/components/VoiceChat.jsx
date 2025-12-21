import { useEffect, useState } from "react";
import { useUser } from "@clerk/clerk-react";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    ControlBar,
    useTracks,
    VideoTrack, // <--- Import VideoTrack
    GridLayout, // <--- Import Layout helpers
} from "@livekit/components-react";
import "@livekit/components-styles";
import { Track } from "livekit-client";

export default function VoiceChat({ onClose, onBookingSuccess }) {
    const { user } = useUser();
    const [token, setToken] = useState(null);
    const [url, setUrl] = useState(null);

    // 1. Fetch Token (Same as before)
    useEffect(() => {
        async function getToken() {
            if (!user) return;
            const identity = `patient_${user.id}`;
            const name = user.firstName || "Patient";
            const email = user.primaryEmailAddress?.emailAddress || "";

            try {
                const resp = await fetch(
                    `http://localhost:8000/api/token?identity=${identity}&name=${name}&email=${email}&room=flossy-room`
                );
                const data = await resp.json();
                setToken(data.token);
                setUrl(data.url);
            } catch (e) {
                console.error("Failed to connect:", e);
            }
        }
        getToken();
    }, [user]);

    // 2. Custom Video Component
    function FlossyVideoStage() {
        // Get all video tracks (The Agent/Avatar)
        const tracks = useTracks([Track.Source.Camera]);

        return (
            <div style={{ flex: 1, position: "relative", background: "#000" }}>
                {tracks.length > 0 ? (
                    <GridLayout tracks={tracks}>
                        {/* Render the Avatar's Video */}
                        <VideoTrack trackRef={tracks[0]} />
                    </GridLayout>
                ) : (
                    /* Fallback if Avatar hasn't joined yet */
                    <div style={{
                        height: "100%", display: "flex", alignItems: "center", justifyContent: "center",
                        flexDirection: "column", color: "#666"
                    }}>
                        <div className="agent-orb pulse"></div>
                        <p style={{ marginTop: "20px" }}>Waiting for Avatar video...</p>
                    </div>
                )}
            </div>
        );
    }

    if (!token || !url) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content voice-modal" style={{
                width: "500px", height: "650px", background: "#111",
                border: "1px solid #333", display: "flex", flexDirection: "column", padding: 0, overflow: "hidden"
            }}>

                {/* Header */}
                <div style={{ padding: "15px", background: "#1a1a1a", borderBottom: "1px solid #333", display: "flex", justifyContent: "space-between" }}>
                    <h3 style={{ color: "#f0b800", margin: 0 }}>📞 FlossyAI Video Call</h3>
                    <button onClick={onClose} style={{ background: "transparent", border: "none", color: "#fff", cursor: "pointer" }}>✖</button>
                </div>

                {/* LiveKit Room */}
                <LiveKitRoom
                    serverUrl={url}
                    token={token}
                    connect={true}
                    video={true} // <--- ENABLE VIDEO RECEPTION
                    audio={true}
                    onDisconnected={onClose}
                    style={{ flex: 1, display: "flex", flexDirection: "column" }}
                >
                    {/* Render Audio from Agent */}
                    <RoomAudioRenderer />

                    {/* Render Video Stage */}
                    <FlossyVideoStage />

                    {/* Controls */}
                    <div style={{ padding: "10px" }}>
                        <ControlBar
                            variation="minimal"
                            controls={{ microphone: true, camera: true, screenShare: false, chat: false }}
                        />
                    </div>
                </LiveKitRoom>
            </div>

            <style>{`
        .agent-orb {
          width: 80px; height: 80px; borderRadius: 50%;
          background: radial-gradient(circle, #f0b800 0%, #ffcb05 60%, transparent 100%);
          box-shadow: 0 0 30px #f0b800;
        }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse {
          0% { transform: scale(0.95); opacity: 0.8; }
          50% { transform: scale(1.05); opacity: 1; }
          100% { transform: scale(0.95); opacity: 0.8; }
        }
      `}</style>
        </div>
    );
}