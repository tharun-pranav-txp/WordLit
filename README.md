# WordLit

WordLit is a Chrome extension for looking up words, summarizing selected text or web pages, and saving summaries to Notion.

It combines a TypeScript browser extension with a FastAPI backend and external APIs for word lookup, AI summarization, and Notion integration.

## Features

* **Word Lookup** — Select a word on a webpage to view its meaning and synonyms.
* **Text Summarization** — Select text and generate an AI summary without leaving the webpage.
* **Page Summarization** — Summarize the readable content of the current page from the extension popup.
* **Notion Integration** — Save generated summaries to Notion.
* **Notion OAuth** — Connect Notion through OAuth without manually entering an integration token or page ID.
* **Persistent Notion Connection** — Reconnect to an existing WordLit Notion page without creating a new page.
* **WordLit ON/OFF** — Disable WordLit's webpage interactions when it is not needed.
* **Non-intrusive Popup** — Word lookup and text actions appear based on the selected content.

## How It Works

### Word Lookup

```text
Webpage
   │
   │ Select a word
   ↓
WordLit Content Script
   │
   ↓
FastAPI Backend
   │
   ↓
Datamuse API
   │
   ↓
Meaning + Synonyms
```

### Text and Page Summarization

```text
Webpage
   │
   ├── Select text
   │
   └── Summarize Page
          │
          ↓
   WordLit Extension
          │
          ↓
    FastAPI Backend
          │
          ↓
       Groq LLM
          │
          ↓
       AI Summary
          │
          └──────→ Save to Notion
                         │
                         ↓
                    Notion OAuth
```

## Tech Stack

### Extension

* TypeScript
* Chrome Extension APIs
* HTML
* CSS
* Content Scripts
* Background Service Worker

### Backend

* Python
* FastAPI
* HTTPX
* Groq API
* Datamuse API
* Notion API

### Infrastructure

* Docker
* Docker Compose

### Integrations

* Datamuse
* Groq
* Notion

## Architecture

WordLit is split into two main parts:

### Browser Extension

The extension handles:

* Text selection
* Word selection
* Popup and tooltip UI
* Page text extraction
* Communication with the browser
* Communication with the backend

### FastAPI Backend

The backend handles:

* Word lookup requests
* AI summarization
* Notion OAuth
* Notion connection management
* Saving summaries to Notion
* Communication with external APIs

API credentials and OAuth secrets remain on the backend instead of being included in the extension.

Notion is optional. Word lookup and summarization can be used without connecting a Notion account.

## Notion OAuth

WordLit uses Notion OAuth instead of asking users to manually enter an integration token or page ID.

```text
User
 │
 │ Connect Notion
 ↓
Notion OAuth
 │
 │ Authorize WordLit
 ↓
WordLit Backend
 │
 │ Store user connection
 ↓
WordLit
 │
 └── Save summaries to user's WordLit Notion page
```

Each user's Notion connection is stored separately.

When a user disconnects Notion, WordLit stops using the connection for saving summaries. Reconnecting can reuse the existing WordLit Notion page when the stored connection is still available.

## Project Structure

```text
WordLit/
├── backend/
│   ├── app/
│   │   ├── cache/
│   │   ├── clients/
│   │   │   ├── datamuse.py
│   │   │   ├── groq.py
│   │   │   └── notion.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── extension/
│   ├── src/
│   │   ├── background.ts
│   │   ├── content.ts
│   │   ├── content.css
│   │   ├── popup.html
│   │   ├── popup.ts
│   │   └── manifest.json
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Running Locally

### Requirements

* Docker
* Docker Compose
* Chrome or another Chromium-based browser

### 1. Clone the repository

```bash
git clone https://github.com/txp-atelier/WordLit.git
cd WordLit
```

### 2. Configure environment variables

Create the required environment files locally.

Do not commit `.env` files or API credentials to the repository.

The backend requires configuration for the external services used by WordLit, including:

* Datamuse
* Groq
* Notion OAuth

### 3. Start the project

```bash
docker compose up --build
```

The extension build service generates the extension files in:

```text
extension/dist/
```

### 4. Load the extension

Open Chrome:

```text
chrome://extensions/
```

Enable **Developer mode**, select **Load unpacked**, and choose:

```text
extension/dist/
```

## Usage

### Word Lookup

1. Open a webpage.
2. Select a single word.
3. WordLit displays the word's meaning and synonyms.

### Text Summarization

1. Select a section of text on a webpage.
2. Choose **Summarize**.
3. WordLit sends the selected text to the backend.
4. The generated summary is displayed in the popup.

### Page Summarization

1. Open the WordLit extension popup.
2. Select **Summarize Page**.
3. WordLit extracts readable content from the current page.
4. The backend sends the content to the Groq model.
5. The generated summary is displayed in the popup.

### Save to Notion

1. Open the WordLit extension popup.
2. Connect your Notion account.
3. Summarize selected text or a webpage.
4. Select **Save to Notion**.
5. WordLit saves the summary to the user's WordLit Notion page.

Notion is optional. Word lookup and summarization work without a Notion connection.

## Security

* API keys and OAuth credentials are stored in environment variables.
* `.env` files are excluded from Git.
* Notion connections are stored separately for each user.
* The Notion OAuth client secret is kept on the backend.
* The extension does not contain the Notion OAuth client secret.

## Why I Built It

WordLit was built as a practical project around browser extensions, AI APIs, backend development, and OAuth integrations.

The project brings these parts together in a single workflow:

* Browser extension development
* TypeScript
* FastAPI
* AI-powered summarization
* External API integration
* Notion OAuth
* User-specific integration state
* Docker-based development

## Future Improvements

* Additional dictionary and language features
* More summarization options
* Additional knowledge-management integrations
* Production deployment
* Usage analytics

## License

This project is a personal portfolio project.
