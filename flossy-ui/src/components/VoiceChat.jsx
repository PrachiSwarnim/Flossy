import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';

const VoiceChat = ({ onClose, onBookingSuccess }) => {
    const { getToken } = useAuth();
    const [isConnected, setIsConnected] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState([]);
    const [error, setError] = useState(null);

    const wsRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioContextRef = useRef(null);
    const audioQueueRef = useRef([]);
    const isPlayingRef = useRef(false);

    // Connect to WebSocket
    useEffect(() => {
        const connectWebSocket = async () => {
            try {
                const token = await getToken();
                const wsUrl = `ws://localhost:8000/ws/voice-chat?token=${token}`;

                const ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    console.log('WebSocket connected');
                    setIsConnected(true);
                };

                ws.onmessage = async (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'ready') {
                        setTranscript(prev => [...prev, { role: 'assistant', text: data.message }]);
                    }

                    else if (data.type === 'transcript') {
                        setTranscript(prev => [...prev, { role: data.role, text: data.text }]);
                    }

                    else if (data.type === 'audio') {
                        const audioData = base64ToArrayBuffer(data.data);
                        audioQueueRef.current.push(audioData);
                        if (!isPlayingRef.current) {
                            playNextAudio();
                        }
                    }

                    else if (data.type === 'audio_complete') {
                        console.log('Audio stream complete');
                    }

                    else if (data.type === 'booking_success') {
                        console.log('Appointment booked:', data.appointment);
                        if (onBookingSuccess) {
                            onBookingSuccess();
                        }
                    }

                    else if (data.type === 'error') {
                        setError(data.message);
                    }
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    setError('Connection error');
                };

                ws.onclose = () => {
                    console.log('WebSocket closed');
                    setIsConnected(false);
                };

                wsRef.current = ws;
            } catch (err) {
                setError('Failed to connect');
                console.error(err);
            }
        };

        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop();
            }
        };
    }, [getToken]);

    const startListening = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();

            recognition.continuous = true;
            recognition.interimResults = false;

            recognition.onresult = (event) => {
                const transcript = event.results[event.results.length - 1][0].transcript;
                console.log('Transcript:', transcript);

                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({
                        type: 'transcript',
                        text: transcript
                    }));
                }
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                setError('Speech recognition error');
            };

            recognition.start();
            mediaRecorderRef.current = recognition;
            setIsListening(true);

        } catch (err) {
            setError('Microphone access denied');
            console.error(err);
        }
    };

    const stopListening = () => {
        if (mediaRecorderRef.current) {
            mediaRecorderRef.current.stop();
            setIsListening(false);
        }
    };

    const playNextAudio = async () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            return;
        }

        isPlayingRef.current = true;
        const audioData = audioQueueRef.current.shift();

        try {
            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            }

            const audioBuffer = await audioContextRef.current.decodeAudioData(audioData);
            const source = audioContextRef.current.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContextRef.current.destination);

            source.onended = () => {
                playNextAudio();
            };

            source.start(0);
        } catch (err) {
            console.error('Audio playback error:', err);
            playNextAudio();
        }
    };

    const base64ToArrayBuffer = (base64) => {
        const binaryString = window.atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    };

    const overlayStyle = {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000
    };

    const modalStyle = {
        backgroundColor: 'white',
        borderRadius: '12px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        width: '90%',
        maxWidth: '600px',
        maxHeight: '80vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
    };

    const headerStyle = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '20px',
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: '#f9fafb'
    };

    const transcriptStyle = {
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        backgroundColor: '#f3f4f6'
    };

    const controlsStyle = {
        padding: '20px',
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        backgroundColor: 'white'
    };

    const micButtonStyle = {
        padding: '16px',
        borderRadius: '50%',
        border: 'none',
        fontSize: '32px',
        cursor: isConnected ? 'pointer' : 'not-allowed',
        backgroundColor: isListening ? '#ef4444' : '#3b82f6',
        color: 'white',
        transition: 'all 0.3s',
        animation: isListening ? 'pulse 1.5s infinite' : 'none'
    };

    return (
        <div style={overlayStyle}>
            <div style={modalStyle}>
                <div style={headerStyle}>
                    <h2 style={{ fontSize: '24px', fontWeight: '600', margin: 0 }}>🎤 Talk to Flossy</h2>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            fontSize: '28px',
                            cursor: 'pointer',
                            color: '#6b7280'
                        }}
                    >
                        ✕
                    </button>
                </div>

                <div style={transcriptStyle}>
                    {transcript.map((msg, idx) => (
                        <div
                            key={idx}
                            style={{
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                marginBottom: '12px'
                            }}
                        >
                            <div
                                style={{
                                    maxWidth: '70%',
                                    padding: '12px 16px',
                                    borderRadius: '12px',
                                    backgroundColor: msg.role === 'user' ? '#3b82f6' : '#e5e7eb',
                                    color: msg.role === 'user' ? 'white' : '#1f2937'
                                }}
                            >
                                {msg.text}
                            </div>
                        </div>
                    ))}
                </div>

                {error && (
                    <div style={{
                        padding: '12px 20px',
                        backgroundColor: '#fee2e2',
                        color: '#dc2626',
                        fontSize: '14px'
                    }}>
                        {error}
                    </div>
                )}

                <div style={controlsStyle}>
                    <button
                        onClick={isListening ? stopListening : startListening}
                        disabled={!isConnected}
                        style={micButtonStyle}
                    >
                        {isListening ? '🔴' : '🎤'}
                    </button>
                    <div style={{ fontSize: '14px', color: '#6b7280' }}>
                        {!isConnected ? 'Connecting...' : isListening ? 'Listening...' : 'Click to speak'}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VoiceChat;
