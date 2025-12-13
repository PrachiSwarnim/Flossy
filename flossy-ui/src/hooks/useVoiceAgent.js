import { useState, useRef, useEffect, useCallback } from "react";

export function useVoiceAgent(url = "ws://localhost:8000/agent/ws/agent") {
    const [isListening, setIsListening] = useState(false);
    const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
    const [messages, setMessages] = useState([]);

    // Refs to keep connection state
    const ws = useRef(null);
    const mediaRecorder = useRef(null);
    const audioContext = useRef(null);
    const audioQueue = useRef([]);
    const isPlaying = useRef(false);

    useEffect(() => {
        return () => {
            stop(); // Cleanup on unmount
        };
    }, []);

    const connect = useCallback(() => {
        if (ws.current?.readyState === WebSocket.OPEN) return;

        ws.current = new WebSocket(url);

        ws.current.onopen = () => {
            console.log("Connected to Voice Agent");
        };

        ws.current.onmessage = async (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "transcript") {
                if (data.text.trim()) {
                    setMessages((prev) => [...prev, { from: "user", text: data.text }]);
                }
            } else if (data.type === "bot_text") {
                setMessages((prev) => [...prev, { from: "ai", text: data.text }]);
            } else if (data.type === "audio_chunk") {
                queueAudio(data.data);
            } else if (data.type === "audio_done") {
                // Audio stream finished for this turn
            }
        };

        ws.current.onclose = () => {
            console.log("Voice Agent Disconnected");
            setIsListening(false);
        };
    }, [url]);

    const start = useCallback(async () => {
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            connect();
            // Wait briefly for connection
            await new Promise(r => setTimeout(r, 500));
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Setup MediaRecorder
            mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });

            mediaRecorder.current.ondataavailable = (event) => {
                if (event.data.size > 0 && ws.current?.readyState === WebSocket.OPEN) {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64Audio = reader.result.split(',')[1];
                        ws.current.send(JSON.stringify({ type: "audio_chunk", data: base64Audio }));
                    };
                    reader.readAsDataURL(event.data);
                }
            };

            mediaRecorder.current.start(100); // 100ms chunks
            setIsListening(true);

        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Microphone access is required for voice chat.");
        }
    }, [connect]);

    const stop = useCallback(() => {
        if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
            mediaRecorder.current.stop();
            mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
        }

        // Signal backend that we are done talking
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: "audio_done" }));
        }

        setIsListening(false);
    }, []);

    // --- AUDIO PLAYBACK ---
    function queueAudio(base64Data) {
        const raw = window.atob(base64Data);
        const rawLength = raw.length;
        const array = new Uint8Array(new ArrayBuffer(rawLength));
        for (let i = 0; i < rawLength; i++) {
            array[i] = raw.charCodeAt(i);
        }

        if (!audioContext.current) {
            audioContext.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 }); // Adjust sample rate if needed
        }

        audioContext.current.decodeAudioData(array.buffer, (buffer) => {
            audioQueue.current.push(buffer);
            playNext();
        });
    }

    function playNext() {
        if (isPlaying.current || audioQueue.current.length === 0) return;

        isPlaying.current = true;
        const buffer = audioQueue.current.shift();
        const source = audioContext.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.current.destination);
        source.onended = () => {
            isPlaying.current = false;
            // logic to check if queue is empty to set state false
            if (audioQueue.current.length === 0) {
                setIsAgentSpeaking(false);
            }
            playNext();
        };
        source.start(0);
        setIsAgentSpeaking(true);
    }

    return { isListening, isAgentSpeaking, start, stop, messages, connect };
}
