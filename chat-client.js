const ws = new WebSocket("ws://localhost:8000/ws/chat");

function sendMessage(content, guestId) {
    ws.send(JSON.stringify({
        content,
        guest_id: guestId,
        timestamp: new Date().toISOString(),
    }));
}

ws.onmessage = ({ data }) => {
    const res = JSON.parse(data);

    console.log(`Topic: ${res.classified_topic} (${res.confidence})`);
    console.log(`Queue depth: ${res.queue_depth}`);

    if (res.saturated) {
        showSuggestionBanner(res.suggestion);   // your UI component
    }
};

function showSuggestionBanner({ message, alternatives }) {
    // render banner with clickable topic chips
    const chips = alternatives.map(t => `<button onclick="prefillTopic('${t}')">${t}</button>`).join("");
    document.getElementById("suggestion-banner").innerHTML = `${message} ${chips}`;
}
