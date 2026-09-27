let tooltipEl: HTMLDivElement | null = null;
let tooltipX = 0;
let tooltipY = 0;

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

function renderTooltip(html: string, x?: number, y?: number) {
    if (x !== undefined && y !== undefined) {
        tooltipX = x;
        tooltipY = y;
    }

    removeTooltip();

    tooltipEl = document.createElement("div");
    tooltipEl.className = "WordLit-tooltip";
    tooltipEl.innerHTML = html;

    document.body.appendChild(tooltipEl);

    const rect = tooltipEl.getBoundingClientRect();

    tooltipEl.style.left = `${Math.max(
        8,
        tooltipX - rect.width / 2
    )}px`;

    tooltipEl.style.top = `${tooltipY + window.scrollY + 10
        }px`;
}

function lookupWord(word: string, x: number, y: number) {
    renderTooltip(`Looking up "${escapeHtml(word)}"...`, x, y);

    chrome.runtime.sendMessage(
        {
            type: "LOOKUP_WORD",
            word,
        },
        (response) => {
            if (!tooltipEl) return;

            if (!response?.ok) {
                renderTooltip(`No results for "${escapeHtml(word)}"`, x, y);

                return;
            }

            const { meaning, synonyms } = response.data;

            const meaningHtml = `<div>${escapeHtml(meaning)}</div>`;

            const synHtml = synonyms.length
                ? `
                        <div class="wl-synonyms">
                            <strong>Synonyms:</strong>
                            ${synonyms.map(escapeHtml).join(", ")}
                        </div>
                    `
                : "";

            const summarizeHtml = `
                <button
                    class="wl-summarize-button"
                    type="button"
                >
                    Summarize
                </button>
            `;

            renderTooltip(meaningHtml + synHtml + summarizeHtml, x, y);

            const button = tooltipEl?.querySelector(".wl-summarize-button");

            button?.addEventListener("click", (event) => {
                event.stopPropagation();

                summarizeText(word, x, y);
            });
        },
    );
}

function summarizeText(
    text: string,
    x: number,
    y: number
) {
    renderTooltip(
        "Summarizing...",
        x,
        y
    );

    chrome.runtime.sendMessage(
        {
            type: "SUMMARIZE_TEXT",
            text,
            maxWords: 80,
        },
        async (response) => {
            if (!tooltipEl) return;

            if (!response?.ok) {
                renderTooltip(
                    "Unable to summarize this text.",
                    x,
                    y
                );

                return;
            }

            const title =
                response.data.title;

            const summary =
                response.data.summary;

            renderTooltip(
                `
                    <div>
                        <strong>${escapeHtml(
                    title
                )}</strong>
                    </div>

                    <div class="wl-summary">
                        ${escapeHtml(summary)}
                    </div>

                    <button
                        class="wl-save-button"
                        type="button"
                    >
                        Save to Notion
                    </button>
                `,
                x,
                y
            );

            const saveButton =
                tooltipEl?.querySelector(
                    ".wl-save-button"
                ) as HTMLButtonElement | null;

            if (!saveButton) return;

            const statusResponse =
                await chrome.runtime.sendMessage(
                    {
                        type:
                            "GET_NOTION_STATUS",
                    }
                );

            if (
                !statusResponse?.ok ||
                !statusResponse.data?.connected
            ) {
                saveButton.remove();
                return;
            }

            saveButton.addEventListener(
                "click",
                async (event) => {
                    event.stopPropagation();

                    saveButton.disabled = true;
                    saveButton.textContent =
                        "Saving...";

                    const savedAt =
                        new Date().toLocaleString(
                            undefined,
                            {
                                dateStyle:
                                    "long",
                                timeStyle:
                                    "short",
                            }
                        );

                    const notionContent =
                        `Source: Highlighted Text\n` +
                        `Saved: ${savedAt}\n\n` +
                        `Summary\n` +
                        summary;

                    const saveResponse =
                        await chrome.runtime.sendMessage(
                            {
                                type:
                                    "SAVE_TO_NOTION",
                                title,
                                content:
                                    notionContent,
                            }
                        );

                    if (
                        saveResponse?.ok
                    ) {
                        saveButton.textContent =
                            "Saved to Notion";
                    } else {
                        saveButton.disabled =
                            false;

                        saveButton.textContent =
                            "Save to Notion";
                    }
                }
            );
        }
    );
}

function showSelectionActions(
    text: string,
    x: number,
    y: number
) {
    const escapedText = escapeHtml(text);

    renderTooltip(
        `
            <div class="wl-selection-text">
                ${escapedText}
            </div>

            <button
                class="wl-summarize-button"
                type="button"
            >
                Summarize
            </button>
        `,
        x,
        y,
    );

    const button =
        tooltipEl?.querySelector(
            ".wl-summarize-button"
        );

    button?.addEventListener(
        "click",
        (event) => {
            event.stopPropagation();

            summarizeText(
                text,
                x,
                y
            );
        }
    );
}

document.addEventListener("mouseup", (event) => {
    // Do not let the page selection handler
    // remove the tooltip before button click fires.
    if (tooltipEl && tooltipEl.contains(event.target as Node)) {
        return;
    }

    const selection = window.getSelection();

    const text = selection?.toString().trim();

    if (!text) {
        removeTooltip();
        return;
    }

    const range = selection!.getRangeAt(0);

    const rect = range.getBoundingClientRect();

    const x = rect.left + rect.width / 2;

    const y = rect.bottom;

    if (!text.includes(" ") && text.length <= 100) {
        lookupWord(text, x, y);

        return;
    }

    showSelectionActions(text, x, y);
});

let selectionTimeout: number | null = null;
let lastSelectionText = "";

document.addEventListener("selectionchange", () => {
    if (selectionTimeout !== null) {
        window.clearTimeout(selectionTimeout);
    }

    selectionTimeout = window.setTimeout(() => {
        const selection = window.getSelection();

        if (!selection || selection.rangeCount === 0) {
            return;
        }

        const anchorNode = selection.anchorNode;
        const focusNode = selection.focusNode;

        // Never process selections inside WordLit.
        if (
            tooltipEl &&
            (
                tooltipEl.contains(anchorNode) ||
                tooltipEl.contains(focusNode)
            )
        ) {
            return;
        }

        const text = selection.toString().trim();

        if (!text) {
            lastSelectionText = "";
            removeTooltip();
            return;
        }

        if (text === lastSelectionText) {
            return;
        }

        lastSelectionText = text;

        if (!text.includes(" ")) {
            return;
        }

        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        showSelectionActions(
            text,
            rect.left + rect.width / 2,
            rect.bottom
        );
    }, 150);
});

document.addEventListener("mousedown", (event) => {
    if (
        tooltipEl &&
        !tooltipEl.contains(event.target as Node)
    ) {
        removeTooltip();

        const selection = window.getSelection();

        if (selection) {
            selection.removeAllRanges();
        }

        lastSelectionText = "";
    }
});

chrome.runtime.onMessage.addListener(
    (message, _sender, sendResponse) => {
        if (
            message.type ===
            "EXTRACT_PAGE_TEXT"
        ) {
            const pageText =
                document.body?.innerText
                    ?.trim() || "";

            const limitedPageText =
                pageText.slice(0, 18000);

            sendResponse({
                ok: true,
                text: limitedPageText,
            });
        }
    }
);

console.log("WordLit: content script loaded");
