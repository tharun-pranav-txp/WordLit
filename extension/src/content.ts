let tooltipEl: HTMLDivElement | null = null;

function escapeHtml(str: string): string {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function removeTooltip() {
    if (tooltipEl) {
        tooltipEl.remove();
        tooltipEl = null;
    }
}

function renderTooltip(word: string, x: number, y: number) {
    removeTooltip();

    tooltipEl = document.createElement("div");
    tooltipEl.className = "WordLit-tooltip";
    tooltipEl.innerHTML = word;

    document.body.appendChild(tooltipEl);

    const rect = tooltipEl.getBoundingClientRect();
    tooltipEl.style.left = `${x - rect.width / 2}px`;
    tooltipEl.style.top = `${y + window.scrollY + 10}px`;
}

function lookupWord(word: string, x: number, y: number) {
    renderTooltip(`Looking up "${escapeHtml(word)}"...`, x, y);

    try {
        chrome.runtime.sendMessage({ type: "LOOKUP_WORD", word}, (response) => {
            if (!tooltipEl) return;

            if (!response?.ok) {
                renderTooltip(`No results for "${escapeHtml(word)}"`, x, y);
                return;
            }

            const { meaning, synonyms } = response.data;
            const meaningHtml = `<div>${escapeHtml(meaning)}</div>`;
            const synHtml = synonyms.length
                ? `<div class="wl-synonyms"><strong>Synonyms:</strong> ${synonyms.map(escapeHtml).join(", ")}</div>`
                : "";

            renderTooltip(meaningHtml + synHtml, x, y);
        });
    } catch (err) {
        if (tooltipEl) {
            renderTooltip("Extension was updated — please refresh the page.", x, y);
        }
    }
}

document.addEventListener("mouseup", () => {
    const selection = window.getSelection();
    const word = selection?.toString().trim();

    if (!word || word.includes(" ")) {
        removeTooltip();
        return;
    }

    const range = selection!.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    lookupWord(word, rect.left + rect.width / 2, rect.bottom);
})

document.addEventListener("mousedown", (e) => {
    if (tooltipEl && !tooltipEl.contains(e.target as Node)) {
        removeTooltip();
    }
})

console.log("WordLit: content script loaded");