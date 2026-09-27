declare const API_BASE: string;

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


chrome.runtime.onMessage.addListener(
    (message, _sender, sendResponse) => {

        if (
            message.type ===
            "LOOKUP_WORD"
        ) {
            fetch(
                `${API_BASE}/lookup?word=${encodeURIComponent(
                    message.word
                )}`
            )
                .then((res) => {
                    if (!res.ok) {
                        throw new Error(
                            `Status ${res.status}`
                        );
                    }

                    return res.json();
                })
                .then((data) => {
                    sendResponse({
                        ok: true,
                        data,
                    });
                })
                .catch((err) => {
                    sendResponse({
                        ok: false,
                        error:
                            err.message,
                    });
                });

            return true;
        }


        if (
            message.type ===
            "SUMMARIZE_TEXT"
        ) {
            fetch(
                `${API_BASE}/summarize`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        text: message.text,
                        max_words:
                            message.maxWords ??
                            80,
                    }),
                }
            )
                .then((res) => {
                    if (!res.ok) {
                        throw new Error(
                            `Status ${res.status}`
                        );
                    }

                    return res.json();
                })
                .then((data) => {
                    sendResponse({
                        ok: true,
                        data,
                    });
                })
                .catch((err) => {
                    sendResponse({
                        ok: false,
                        error:
                            err.message,
                    });
                });

            return true;
        }


        if (
            message.type ===
            "CONNECT_NOTION"
        ) {
            getUserId()
                .then(async (userId) => {
                    const currentTab =
                        await chrome.tabs.query({
                            active: true,
                            currentWindow: true,
                        });

                    const originalTabId =
                        currentTab[0]?.id;

                    const url =
                        `${API_BASE}/notion/oauth/authorize?user_id=${encodeURIComponent(
                            userId
                        )}`;

                    const tab =
                        await chrome.tabs.create({
                            url,
                        });

                    if (!tab.id) {
                        throw new Error(
                            "Unable to open Notion authorization tab."
                        );
                    }

                    const tabId = tab.id;

                    const checkConnection =
                        async () => {
                            try {
                                const response =
                                    await fetch(
                                        `${API_BASE}/notion/status?user_id=${encodeURIComponent(
                                            userId
                                        )}`
                                    );

                                if (!response.ok) {
                                    return;
                                }

                                const data =
                                    await response.json();

                                if (
                                    data.connected === true
                                ) {
                                    clearInterval(
                                        intervalId
                                    );

                                    try {
                                        await chrome.tabs.remove(
                                            tabId
                                        );
                                    } catch {
                                        // OAuth tab may already be closed.
                                    }

                                    if (
                                        originalTabId !==
                                        undefined
                                    ) {
                                        try {
                                            await chrome.tabs.update(
                                                originalTabId,
                                                {
                                                    active: true,
                                                }
                                            );
                                        } catch {
                                            // Original tab may have been closed.
                                        }
                                    }
                                }
                            } catch {
                                // Backend may temporarily be unavailable.
                            }
                        };

                    const intervalId =
                        setInterval(
                            checkConnection,
                            1000
                        );

                    setTimeout(() => {
                        clearInterval(
                            intervalId
                        );
                    }, 5 * 60 * 1000);
                })
                .then(() => {
                    sendResponse({
                        ok: true,
                    });
                })
                .catch((err) => {
                    sendResponse({
                        ok: false,
                        error:
                            err instanceof Error
                                ? err.message
                                : "Unable to connect to Notion.",
                    });
                });

            return true;
        }


        if (
            message.type ===
            "GET_NOTION_STATUS"
        ) {
            getUserId()
                .then((userId) => {
                    return fetch(
                        `${API_BASE}/notion/status?user_id=${encodeURIComponent(
                            userId
                        )}`
                    );
                })
                .then((res) => {
                    if (!res.ok) {
                        throw new Error(
                            `Status ${res.status}`
                        );
                    }

                    return res.json();
                })
                .then((data) => {
                    sendResponse({
                        ok: true,
                        data,
                    });
                })
                .catch((err) => {
                    sendResponse({
                        ok: false,
                        error:
                            err.message,
                    });
                });

            return true;
        }


        if (
            message.type ===
            "GET_PAGE_TEXT"
        ) {
            chrome.tabs.sendMessage(
                message.tabId,
                {
                    type:
                        "EXTRACT_PAGE_TEXT",
                },
                (response) => {
                    if (
                        chrome.runtime.lastError
                    ) {
                        sendResponse({
                            ok: false,
                            error:
                                chrome.runtime
                                    .lastError
                                    .message,
                        });

                        return;
                    }

                    sendResponse(
                        response
                    );
                }
            );

            return true;
        }

        if (
            message.type ===
            "SAVE_TO_NOTION"
        ) {
            getUserId()
                .then((userId) => {
                    return fetch(
                        `${API_BASE}/notion/save`,
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json",
                            },
                            body: JSON.stringify({
                                user_id: userId,
                                title:
                                    message.title,
                                content:
                                    message.content,
                            }),
                        }
                    );
                })
                .then((res) => {
                    if (!res.ok) {
                        throw new Error(
                            `Status ${res.status}`
                        );
                    }

                    return res.json();
                })
                .then((data) => {
                    sendResponse({
                        ok: true,
                        data,
                    });
                })
                .catch((err) => {
                    sendResponse({
                        ok: false,
                        error:
                            err.message,
                    });
                });

            return true;
        }
    }
);


console.log(
    "WordLit: background service worker loaded"
);