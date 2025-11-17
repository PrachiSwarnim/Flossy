// =========================
// 🔧 WebSocket (Call Button)
// =========================
const wsProto = window.location.protocol === "https:" ? "wss" : "ws";
const wsUrl = `${wsProto}://${window.location.host}/ws/agent`; // Make sure this matches FastAPI route
let ws;

const callBtn = document.getElementById("call-btn");
const audioPlayer = document.getElementById("audioPlayer");

callBtn.addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
    callBtn.textContent = "📞";
    console.log("Call ended");
    return;
  }

  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    console.log("Connected to voice agent");
    callBtn.textContent = "🔴 End";
  };

  ws.onmessage = (event) => {
    const audioData = event.data;
    if (audioData instanceof Blob) {
      const url = URL.createObjectURL(audioData);
      audioPlayer.src = url;
    } else {
      console.log("Message:", audioData);
    }
  };

  ws.onclose = () => {
    console.log("Disconnected");
    callBtn.textContent = "📞";
  };
});

// ==========================
// 🔔 Firebase Notifications
// ==========================
const firebaseConfig = {
  apiKey: "AIzaSyCusU0d_qu4hr-k1xKXmQtTpVXpShCcOGI",
  authDomain: "flossy-62a22.firebaseapp.com",
  projectId: "flossy-62a22",
  storageBucket: "flossy-62a22.firebasestorage.app",
  messagingSenderId: "620594247395",
  appId: "1:620594247395:web:02f0ec4be8e884359cb7d6",
  measurementId: "G-8NB5F8N12M",
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

document.getElementById("notify-btn").addEventListener("click", async () => {
  try {
    const permission = await Notification.requestPermission();
    if (permission === "granted") {
      const token = await messaging.getToken();
      console.log("Notification token:", token);
      alert("Notifications enabled!");
    } else {
      alert("Permission denied for notifications.");
    }
  } catch (err) {
    console.error("Error enabling notifications:", err);
  }
});

// ==========================
// 💬 Chatbox Implementation
// ==========================
const chatbox = document.getElementById("chatbox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("send-btn");

function appendMessage(sender, text) {
  const div = document.createElement("div");
  div.className = sender === "user" ? "text-right my-1" : "text-left my-1";
  div.innerHTML = `<span class="inline-block px-3 py-2 rounded-xl ${
    sender === "user"
      ? "bg-blue-600 text-white"
      : "bg-gray-300 text-black"
  }">${text}</span>`;
  chatbox.appendChild(div);
  chatbox.scrollTop = chatbox.scrollHeight;
}

sendBtn.addEventListener("click", async () => {
  const text = userInput.value.trim();
  if (!text) return;
  appendMessage("user", text);
  userInput.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    appendMessage("flossy", data.reply || "Hmm... I’m thinking!");
  } catch (err) {
    console.error("Chat error:", err);
    appendMessage("flossy", "⚠️ Error connecting to server");
  }
});
