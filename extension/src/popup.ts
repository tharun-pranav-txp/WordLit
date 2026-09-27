declare const API_BASE: string;

const wordInput =
    document.getElementById(
        "word-input"
    ) as HTMLInputElement;

const lookupButton =
    document.getElementById(
        "lookup-button"
    ) as HTMLButtonElement;

const summarizePageButton =
    document.getElementById(
        "summarize-page"
    ) as HTMLButtonElement;

const result =
    document.getElementById(
        "result"
    ) as HTMLDivElement;

const notionStatus =
    document.getElementById(
        "notion-status"
    ) as HTMLDivElement;

const notionConnectForm =
    document.getElementById(
        "notion-connect-form"
    ) as HTMLDivElement;

const connectNotionButton =
    document.getElementById(
        "connect-notion"
    ) as HTMLButtonElement;

const notionConnectedActions =
    document.getElementById(
        "notion-connected-actions"
    ) as HTMLDivElement;

const disconnectNotionButton =
    document.getElementById(
        "disconnect-notion"
    ) as HTMLButtonElement;

const wordlitToggle =
    document.getElementById(
        "wordlit-toggle"
    ) as HTMLInputElement;

const toggleDescription =
    document.getElementById(
        "toggle-description"
    ) as HTMLDivElement;

async function getWordLitEnabled(): Promise<boolean> {
    const stored =
        await chrome.storage.local.get(
            "wordlitEnabled"
        );

    return stored.wordlitEnabled !== false;
}


async function updateWordLitToggle() {
    const enabled =
        await getWordLitEnabled();

    wordlitToggle.checked = enabled;

    toggleDescription.textContent =
        enabled
            ? "Active on web pages"
            : "Paused on web pages";
}


async function toggleWordLit() {
    const enabled =
        wordlitToggle.checked;

    await chrome.storage.local.set({
        wordlitEnabled: enabled,
    });

    toggleDescription.textContent =
        enabled
            ? "Active on web pages"
            : "Paused on web pages";

    if (!enabled) {
        await chrome.runtime.sendMessage({
            type: "WORDLIT_DISABLED",
        });
    }
}

function showResult(
    html: string
) {
    result.innerHTML = html;
}


async function getUserId(): Promise<string> {
    const result =
        await chrome.storage.local.get(
            "wordlitUserId"
        );

    if (result.wordlitUserId) {
        return result.wordlitUserId;
    }

    const userId =
        crypto.randomUUID();

    await chrome.storage.local.set({
        wordlitUserId: userId,
    });

    return userId;
}


async function getNotionStatus(): Promise<boolean> {
    const response =
        await chrome.runtime.sendMessage(
            {
                type:
                    "GET_NOTION_STATUS",
            }
        );

    if (!response?.ok) {
        return false;
    }

    return response.data?.connected === true;
}


async function updateNotionStatus() {
    const response =
        await chrome.runtime.sendMessage(
            {
                type:
                    "GET_NOTION_STATUS",
            }
        );

    if (
        response?.ok &&
        response.data?.connected
    ) {
        notionStatus.textContent =
            "Notion connected";

        notionStatus.className =
            "status success";

        notionConnectForm.style.display =
            "none";

        notionConnectedActions.style.display =
            "flex";

        return true;
    }

    notionStatus.textContent =
        "Notion not connected";

    notionStatus.className =
        "status";

    notionConnectForm.style.display =
        "flex";

    notionConnectedActions.style.display =
        "none";

    return false;
}


async function connectNotion() {
    connectNotionButton.disabled =
        true;

    connectNotionButton.textContent =
        "Opening Notion...";

    try {
        const response =
            await chrome.runtime.sendMessage(
                {
                    type:
                        "CONNECT_NOTION",
                }
            );

        if (!response?.ok) {
            throw new Error(
                response?.error ||
                "Unable to connect to Notion."
            );
        }
    } catch (error) {
        notionStatus.textContent =
            error instanceof Error
                ? error.message
                : "Unable to connect to Notion.";

        notionStatus.className =
            "status error";

        connectNotionButton.disabled =
            false;

        connectNotionButton.textContent =
            "Connect Notion";
    }
}


async function disconnectNotion() {
    disconnectNotionButton.disabled =
        true;

    try {
        const userId =
            await getUserId();

        const response =
            await fetch(
                `${API_BASE}/notion/disconnect?user_id=${encodeURIComponent(
                    userId
                )}`,
                {
                    method: "DELETE",
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                `Status ${response.status}`
            );
        }

        await updateNotionStatus();
    } catch (error) {
        notionStatus.textContent =
            error instanceof Error
                ? error.message
                : "Unable to disconnect Notion.";

        notionStatus.className =
            "status error";
    } finally {
        disconnectNotionButton.disabled =
            false;
    }
}


async function saveToNotion(
    title: string,
    content: string
) {
    const connected =
        await getNotionStatus();

    if (!connected) {
        throw new Error(
            "Notion is not connected"
        );
    }

    const response =
        await chrome.runtime.sendMessage(
            {
                type:
                    "SAVE_TO_NOTION",
                title,
                content,
            }
        );

    if (!response?.ok) {
        throw new Error(
            response?.error ||
            "Unable to save to Notion"
        );
    }

    return response.data;
}


async function lookupWord() {
    const word =
        wordInput.value.trim();

    if (!word) {
        showResult(
            `<div class="error">
                Please enter a word.
            </div>`
        );

        return;
    }

    if (
        word.includes(" ") ||
        !/^[a-zA-Z'-]+$/.test(word)
    ) {
        showResult(
            `<div class="error">
                Enter one word only.
            </div>`
        );

        return;
    }

    lookupButton.disabled = true;

    showResult("Looking up...");

    try {
        const response =
            await fetch(
                `${API_BASE}/lookup?word=${encodeURIComponent(
                    word
                )}`
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                `Status ${response.status}`
            );
        }

        const synonyms =
            data.synonyms?.length
                ? `
                    <div class="synonyms">
                        <strong>Synonyms:</strong>
                        ${data.synonyms.join(", ")}
                    </div>
                `
                : "";

        showResult(
            `
                <div class="meaning">
                    <strong>${data.word}</strong>
                    <br>
                    ${data.meaning}
                </div>

                ${synonyms}
            `
        );

    } catch {
        showResult(
            `
                <div class="error">
                    Unable to look up this word.
                </div>
            `
        );
    } finally {
        lookupButton.disabled = false;
    }
}


async function summarizePage() {
    summarizePageButton.disabled = true;

    showResult(
        "Reading current page..."
    );

    try {
        const tabs =
            await chrome.tabs.query({
                active: true,
                currentWindow: true,
            });

        const tab = tabs[0];

        if (!tab?.id) {
            throw new Error(
                "No active tab found"
            );
        }

        const response =
            await chrome.runtime.sendMessage(
                {
                    type:
                        "GET_PAGE_TEXT",
                    tabId: tab.id,
                }
            );

        if (!response?.ok) {
            throw new Error(
                response?.error ||
                "Unable to read page"
            );
        }

        const text =
            response.text?.trim();

        if (!text) {
            throw new Error(
                "No readable text found on this page"
            );
        }

        showResult(
            "Summarizing page..."
        );

        const summaryResponse =
            await chrome.runtime.sendMessage(
                {
                    type:
                        "SUMMARIZE_TEXT",
                    text,
                    maxWords: 120,
                }
            );

        if (
            !summaryResponse?.ok
        ) {
            throw new Error(
                summaryResponse?.error ||
                "Unable to summarize page"
            );
        }

        const title =
            summaryResponse.data.title;

        const summary =
            summaryResponse.data.summary;

        const notionConnected =
            await getNotionStatus();

        showResult(
            `
                <div class="meaning">
                    <strong>${title}</strong>
                </div>

                <div>
                    ${summary}
                </div>

                ${notionConnected
                ? `
                            <button
                                id="save-summary"
                                style="margin-top: 12px;"
                            >
                                Save to Notion
                            </button>
                        `
                : ""
            }
            `
        );

        const saveButton =
            document.getElementById(
                "save-summary"
            ) as HTMLButtonElement | null;

        if (saveButton) {
            saveButton.addEventListener(
                "click",
                async () => {
                    saveButton.disabled = true;
                    saveButton.textContent =
                        "Saving...";

                    try {
                        const savedAt =
                            new Date().toLocaleString(
                                undefined,
                                {
                                    dateStyle: "long",
                                    timeStyle: "short",
                                }
                            );

                        const cleanSummary =
                            summary
                                .replace(/\s+/g, " ")
                                .trim();

                        const notionContent =
                            `Source: Page Summary\n` +
                            `Saved: ${savedAt}\n\n` +
                            `Summary\n` +
                            cleanSummary;

                        await saveToNotion(
                            title,
                            notionContent
                        );

                        saveButton.textContent =
                            "Saved to Notion";
                    } catch {
                        saveButton.disabled =
                            false;

                        saveButton.textContent =
                            "Save to Notion";

                        showResult(
                            `
                        <div class="error">
                            Unable to save to Notion.
                        </div>
                    `
                        );
                    }
                }
            );
        }

    } catch (error) {
        showResult(
            `
                <div class="error">
                    ${error instanceof Error
                ? error.message
                : "Unable to summarize page."
            }
                </div>
            `
        );
    } finally {
        summarizePageButton.disabled =
            false;
    }
}


lookupButton.addEventListener(
    "click",
    lookupWord
);


wordInput.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key ===
            "Enter"
        ) {
            lookupWord();
        }
    }
);


summarizePageButton.addEventListener(
    "click",
    summarizePage
);


connectNotionButton.addEventListener(
    "click",
    connectNotion
);

disconnectNotionButton.addEventListener(
    "click",
    disconnectNotion
);

wordlitToggle.addEventListener(
    "change",
    toggleWordLit
);

updateWordLitToggle();

updateNotionStatus();