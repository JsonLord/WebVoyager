---
title: Web-Agent-Internal
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
python_version: '3.10'
---

# WebVoyager (Web-Agent-Internal)

This is a persistent, session-oriented web automation agent refactored for professional use. It integrates structured scraping and multi-step planning.

## Setup

To use this space, you must set your `BLABLADOR_API_KEY` as a secret.

1.  Go to the "Settings" tab of this space.
2.  Scroll down to the "Secrets" section.
3.  Click on "New secret" and add your `BLABLADOR_API_KEY`.

The agent uses Helmholtz-Blablador (OpenAI-compatible endpoint) with models `alias_large` and `alias_fast`.

## How to use

1.  Enter the URL of the website you want the agent to interact with.
2.  Describe the task you want the agent to perform.
3.  (Optional) Toggle persona usage or describe a TinyTroupe persona.
4.  Click "Submit" and watch the agent work in real-time.

## API Usage

This space exposes a Gradio API and a FastAPI backend.
- API Endpoint: `/api/v1`
- Gradio API: Use the `execute_task` endpoint via Gradio Client.
