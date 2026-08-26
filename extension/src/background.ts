declare const API_BASE: string;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "LOOKUP_WORD") {
        fetch (`${API_BASE}/lookup?word=${encodeURIComponent(message.word)}`)
            .then((res) => {
                if (!res.ok) throw new Error(`Status ${res.status}`);
                return res.json();
            })
            .then((data) => sendResponse({ ok: true, data }))
            .catch((err) => sendResponse({ ok: false, error: err.message }));

        return true;
    }
})

console.log("WordLit: background service worker loaded");