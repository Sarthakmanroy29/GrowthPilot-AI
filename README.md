# GrowthPilot AI
**Marketing Analytics & Growth Strategy Agent** for Indian D2C e-commerce.

## What is included
- Streamlit web interface with editable campaign data and CSV upload.
- KPI calculations for ROAS, CAC proxy and AOV; conversion rate only when `conversions` is supplied.
- Gemini-powered marketing analysis using the official `google-genai` SDK.
- Optional routing through an existing n8n production webhook.
- Sample CSV data and setup instructions.

## 1. Install prerequisites
Install:
- Python 3.11 or 3.12
- Visual Studio Code
- VS Code Python extension
- Your Gemini API key from Google AI Studio

## 2. Open the project in VS Code
1. Extract the ZIP file.
2. In VS Code choose **File → Open Folder** and select `GrowthPilotAI_Project`.
3. Open **Terminal → New Terminal**.

## 3. Create a virtual environment (Windows PowerShell)
Run one command at a time:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `py -3.12` is not available, use `py -m venv .venv` with an installed supported Python version. If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`, or follow Microsoft's execution-policy guidance for your machine.

## 4. Configure your API key securely
1. In VS Code Explorer, open the `.streamlit` folder.
2. Copy `secrets.toml.example` and rename the copy to `secrets.toml`.
3. Open `secrets.toml` and replace the placeholder with your own Gemini API key.
4. Save the file.
5. Confirm `.streamlit/secrets.toml` is listed in `.gitignore`.

Never upload or commit `secrets.toml`, screenshots containing the key, or the key itself to GitHub. If a key is exposed, revoke it and create a replacement.

## 5. Run the app locally
In the VS Code terminal, from the project folder, run:

```powershell
python -m streamlit run app.py
```

The browser should open at `http://localhost:8501`. If it does not, copy that address into your browser. Keep the terminal running while using the app.

## 6. Use GrowthPilot AI
1. Review the sample campaign table or upload your own CSV.
2. Edit the campaign rows if needed.
3. Confirm business, currency and reporting period in the sidebar.
4. Ask a question in the chat box, for example:
   - "Compare channels and recommend three growth actions."
   - "Design an A/B test to improve conversion."
   - "Suggest a 30-day customer retention strategy."
5. Review calculated metrics and the AI's assumptions/missing-data notes.

### CSV format
Expected columns:
- `channel`
- `spend`
- `attributed_revenue`
- `orders`
- `new_customers`
- `sessions`

Optional:
- `conversions` — needed for conversion rate. The app deliberately does not assume orders equal conversions.
- Additional columns are retained in the uploaded table and may be sent as context to the model.

All values must use consistent time periods, currency and attribution scope.

## 7. Connect your existing n8n workflow (optional)
The app can send chat questions and campaign rows to your n8n webhook instead of calling Gemini directly.

### Local testing
1. Start n8n and ensure your workflow is configured to respond using a **Respond to Webhook** node.
2. Activate/publish the workflow to use its production URL, or use a test listener and test URL for development.
3. In the Streamlit sidebar, turn on **Route questions through my n8n workflow**.
4. Enter your local production webhook URL:
   `http://localhost:5678/webhook/growthpilot-chat`
5. Ask a question in the app.

Important: when Streamlit runs locally on the same computer as n8n, localhost can work. If n8n is in Docker, check port mappings and network access.

### Cloud hosting caveat
A deployed Streamlit app cannot use `http://localhost:5678` to reach n8n on your personal laptop. The URL would refer to the cloud host itself. To use n8n from a hosted app, deploy n8n to a secured reachable host with HTTPS and set `N8N_WEBHOOK_URL` in Streamlit secrets. Do not expose an unauthenticated webhook publicly. Add authentication or another appropriate access-control layer before public deployment.

## 8. Deploy to Streamlit Community Cloud
1. Create a GitHub repository.
2. Upload the project files except `.streamlit/secrets.toml`, `.venv`, and other ignored files.
3. Verify that `.gitignore` excludes `.streamlit/secrets.toml`.
4. Go to https://share.streamlit.io/ and sign in with GitHub.
5. Click **Create app**, select your repository, branch and `app.py` as the main file.
6. In the deployment's **Advanced settings / Secrets**, add the contents of your local secrets file, replacing the placeholder with your real key. Do not put the real key in the repository.
7. Deploy and wait for the build to finish.
8. Open the generated `*.streamlit.app` URL.

For cloud deployment, leave n8n routing off unless you have configured a reachable, secure n8n URL. The app can call Gemini directly using its server-side secret.

## Troubleshooting
- `ModuleNotFoundError: streamlit`: activate `.venv` and run `pip install -r requirements.txt`.
- `No module named google.genai`: run `pip install -r requirements.txt`.
- Missing secrets: check `.streamlit/secrets.toml` spelling and restart Streamlit.
- Gemini 400 / 401: check key, model name and API access.
- Gemini 429: check quota/rate limits and retry later.
- Gemini 503: model service may be temporarily unavailable; retry later or select another available model.
- n8n 404: verify test vs production URL and whether workflow is listening/active.
- n8n timeout: check n8n is running, webhook response mode, network reachability and node execution.
- Cloud app cannot reach local n8n: use a secured public HTTPS n8n endpoint; do not use localhost.

## Design and safety notes
- KPI calculations are performed in Python; Gemini provides interpretation and recommendations.
- CAC is labelled a proxy because spend may not include all acquisition costs.
- ROAS is not profit.
- Conversion rate is calculated only when a `conversions` column is provided.
- The app does not change live ad campaigns, spend money, send external messages, or write to business systems.
- AI output is advisory. Validate inputs and require human approval for consequential actions.
