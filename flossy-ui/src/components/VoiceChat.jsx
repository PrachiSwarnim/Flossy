import { useEffect, useRef, useState } from "react";
import { Phone, Mic, MicOff, PhoneOff, ShieldCheck } from "lucide-react";

export default function VoiceChat({ onClose }) {
    const [status, setStatus] = useState("");
    const [callStatus, setCallStatus] = useState("Connecting...");
    const [isTalking, setIsTalking] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [timer, setTimer] = useState(0);

    // Refs for WebSocket and Audio
    const socketRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioContextRef = useRef(null);
    const audioQueue = useRef([]);
    const isPlaying = useRef(false);
    const timerIntervalRef = useRef(null);
    const ringingRef = useRef(null);

    useEffect(() => {
        // Start ringing sound
        const audio = new Audio("https://www.soundjay.com/phone/phone-calling-1.mp3");
        audio.loop = true;
        audio.play().catch(e => console.log("Audio play blocked:", e));
        ringingRef.current = audio;

        startConnection();
        return () => stopConnection();
    }, []);

    useEffect(() => {
        if (callStatus === "Listening..." || callStatus === "Speaking..." || callStatus === "Thinking...") {
            if (ringingRef.current) {
                ringingRef.current.pause();
                ringingRef.current = null;
            }
            if (!timerIntervalRef.current) {
                timerIntervalRef.current = setInterval(() => {
                    setTimer(prev => prev + 1);
                }, 1000);
            }
        }
    }, [callStatus]);

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const startConnection = async () => {
        try {
            const ws = new WebSocket("ws://localhost:8000/ws/agent");
            ws.binaryType = "arraybuffer";

            ws.onopen = () => {
                startMicrophone(ws);
            };

            ws.onmessage = async (event) => {
                const data = event.data;
                if (data instanceof ArrayBuffer) {
                    queueAudio(data);
                } else {
                    try {
                        const msg = JSON.parse(data);
                        if (msg.type === "text") {
                            setStatus(msg.content);
                        } else if (msg.type === "status") {
                            setCallStatus(msg.content);
                            if (msg.content === "Speaking...") setIsTalking(true);
                            if (msg.content === "Listening...") setIsTalking(false);
                        }
                    } catch (e) { console.log("Text msg:", data); }
                }
            };

            ws.onclose = () => setCallStatus("Disconnected");
            ws.onerror = (e) => setCallStatus("Connection Error");
            socketRef.current = ws;

        } catch (e) {
            console.error(e);
            setCallStatus("Error Connecting");
        }
    };

    const startMicrophone = async (ws) => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

            recorder.ondataavailable = (e) => {
                if (!isMuted && e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    ws.send(e.data);
                }
            };

            recorder.start(250);
            mediaRecorderRef.current = recorder;
        } catch (e) {
            setCallStatus("Microphone blocked");
        }
    };

    const queueAudio = (arrayBuffer) => {
        audioQueue.current.push(arrayBuffer);
        playNext();
    };

    const playNext = async () => {
        if (isPlaying.current || audioQueue.current.length === 0) return;

        isPlaying.current = true;
        if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        }

        try {
            const buffer = await audioContextRef.current.decodeAudioData(audioQueue.current.shift());
            const source = audioContextRef.current.createBufferSource();
            source.buffer = buffer;
            source.connect(audioContextRef.current.destination);
            source.onended = () => {
                isPlaying.current = false;
                playNext();
            };
            source.start(0);
        } catch (e) {
            isPlaying.current = false;
        }
    };

    const stopConnection = () => {
        if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
        if (socketRef.current) socketRef.current.close();
        if (audioContextRef.current) audioContextRef.current.close();
        if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        if (ringingRef.current) ringingRef.current.pause();
    };

    return (
        <div className="voice-modal-overlay">
            <div className="voice-modal-container">

                {/* Header Information */}
                <div className="voice-header">
                    <div className="secure-badge">
                        <ShieldCheck size={14} className="mr-1" />
                        Secure Line
                    </div>
                    <div className="call-timer">{formatTime(timer)}</div>
                </div>

                {/* Animated Orb Section */}
                <div className="orb-wrapper">
                    <div className={`orb-outer ${isTalking ? 'speaking' : 'listening'}`}>
                        <div className={`orb-inner ${isTalking ? 'speaking' : 'listening'}`}></div>
                    </div>
                </div>

                {/* Agent Identity and Status */}
                <div className="agent-info">
                    <h2 className="agent-name">FlossyAI Assistant</h2>
                    <p className="agent-status">{callStatus.toUpperCase()}</p>
                </div>

                {/* Subtitles / Text Output */}
                <div className="subtitle-container">
                    <p className="subtitle-text">{status || "..."}</p>
                </div>

                {/* Control Bar */}
                <div className="control-bar">
                    <button
                        className={`control-btn mute-btn ${isMuted ? 'active' : ''}`}
                        onClick={() => setIsMuted(!isMuted)}
                    >
                        {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                    </button>

                    <button className="control-btn end-btn" onClick={onClose}>
                        <PhoneOff size={24} />
                    </button>
                </div>

            </div>

            <style>{`
                .voice-modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.95);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                    font-family: 'Inter', sans-serif;
                }

                .voice-modal-container {
                    width: 100%;
                    max-width: 400px;
                    height: 600px;
                    background: #0a0a0a;
                    border-radius: 40px;
                    padding: 40px 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    position: relative;
                    box-shadow: 0 0 100px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(255, 255, 255, 0.05);
                    border: 1px solid #1a1a1a;
                }

                .voice-header {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-bottom: 60px;
                }

                .secure-badge {
                    background: rgba(34, 197, 94, 0.1);
                    color: #22c55e;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    display: flex;
                    align-items: center;
                    margin-bottom: 10px;
                }

                .call-timer {
                    color: white;
                    font-size: 1.5rem;
                    font-weight: 300;
                    letter-spacing: 2px;
                }

                .orb-wrapper {
                    position: relative;
                    width: 200px;
                    height: 200px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin-bottom: 40px;
                }

                .orb-outer {
                    position: absolute;
                    width: 180px;
                    height: 180px;
                    border-radius: 50%;
                    transition: all 0.5s ease;
                }

                .orb-outer.listening {
                    border: 1px solid rgba(59, 130, 246, 0.3);
                    animation: pulse-ring-blue 3s infinite;
                }

                .orb-outer.speaking {
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    animation: pulse-ring-yellow 2s infinite;
                    transform: scale(1.1);
                }

                .orb-inner {
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                }

                .orb-inner.listening {
                    background: radial-gradient(circle, #3b82f6 0%, #1d4ed8 70%);
                    box-shadow: 0 0 40px rgba(59, 130, 246, 0.6);
                    animation: orb-breathe 4s infinite ease-in-out;
                }

                .orb-inner.speaking {
                    background: radial-gradient(circle, #fbbf24 0%, #f59e0b 70%);
                    box-shadow: 0 0 60px rgba(245, 158, 11, 0.8);
                    animation: orb-talk 0.5s infinite alternate ease-in-out;
                    transform: scale(1.05);
                }

                @keyframes pulse-ring-blue {
                    0% { transform: scale(0.9); opacity: 0; }
                    50% { opacity: 0.5; }
                    100% { transform: scale(1.4); opacity: 0; }
                }

                @keyframes pulse-ring-yellow {
                    0% { transform: scale(1); opacity: 0; }
                    50% { opacity: 0.8; }
                    100% { transform: scale(1.6); opacity: 0; }
                }

                @keyframes orb-breathe {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.08); }
                }

                @keyframes orb-talk {
                    0% { transform: scale(1); }
                    100% { transform: scale(1.15) translateY(-5px); }
                }

                .agent-info {
                    text-align: center;
                    margin-bottom: 30px;
                }

                .agent-name {
                    color: #fbbf24;
                    font-size: 1.8rem;
                    font-weight: 400;
                    margin: 0;
                    letter-spacing: 0.5px;
                }

                .agent-status {
                    color: #666;
                    font-size: 0.9rem;
                    letter-spacing: 4px;
                    margin-top: 10px;
                }

                .subtitle-container {
                    width: 100%;
                    max-height: 80px;
                    overflow: hidden;
                    text-align: center;
                    padding: 0 20px;
                    margin-bottom: auto;
                }

                .subtitle-text {
                    color: #999;
                    font-size: 0.95rem;
                    line-height: 1.4;
                    font-style: italic;
                }

                .control-bar {
                    display: flex;
                    gap: 30px;
                    margin-top: 20px;
                }

                .control-btn {
                    width: 64px;
                    height: 64px;
                    border-radius: 50%;
                    border: none;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .mute-btn {
                    background: rgba(255, 255, 255, 0.1);
                    color: white;
                }

                .mute-btn:hover {
                    background: rgba(255, 255, 255, 0.2);
                }

                .mute-btn.active {
                    background: #ef4444;
                    color: white;
                }

                .end-btn {
                    background: #ef4444;
                    color: white;
                    box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
                }

                .end-btn:hover {
                    background: #dc2626;
                    transform: scale(1.05);
                }
            `}</style>
        </div>
    );
}
