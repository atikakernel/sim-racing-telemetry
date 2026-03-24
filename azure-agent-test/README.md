# Papales Agent - Azure AI Foundry

This project provides a simple web interface to interact with the **Papales** intelligent agent, configured in Azure AI Foundry.

## 🚀 Prerequisites

1.  **Node.js**: Ensure you have Node.js installed (v18 or higher).
2.  **Azure CLI**: Required for identity-based authentication.
    *   [Download Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
3.  **Azure Permissions**: Your Azure account must have access permissions to the AI Foundry project specified in the `.env` file.

## 🛠️ Installation and Usage

1.  **Install dependencies**:
    Open a terminal in the project folder and run:
    ```bash
    npm install
    ```

2.  **Log in to Azure**:
    To allow the server to connect securely to Azure services:
    ```bash
    az login
    ```

3.  **Start the server**:
    ```bash
    node server.js
    ```

4.  **Open the Chat**:
    Go to your browser and open the following address:
    `http://localhost:8080`

## ⚙️ Configuration (.env file)

If you need to change the agent or the Azure project, edit the `.env` file:

*   `AZURE_PROJECT_ENDPOINT`: Your Azure project URL.
*   `AZURE_AGENT_NAME`: The agent's name (e.g., `papales`).
*   `AZURE_AGENT_VERSION`: The agent's version (e.g., `2`).
*   `AZURE_HOST` and `AZURE_IP`: Configuration to bypass network/DNS blocks.

## ☁️ Deployment to Azure App Service

This project is ready for automated deployment to Azure using GitHub Actions.

1.  **Create an Azure Web App**:
    - Build: Node 18 LTS
    - OS: Linux
2.  **Configure GitHub Secrets**:
    - Go to your repository **Settings > Secrets and variables > Actions**.
    - Add a new secret named `AZURE_WEBAPP_PUBLISH_PROFILE`.
    - Paste the content of your Azure [Publish Profile](https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions?tabs=applevel#configure-the-github-secret).
3.  **Environment Variables**:
    - In the Azure Portal, go to **Configuration > Application settings** for your Web App.
    - Add the following keys (from your `.env`):
      - `AZURE_PROJECT_ENDPOINT`
      - `AZURE_AGENT_NAME`
      - `AZURE_AGENT_VERSION`
      - `AZURE_HOST` (optional)
      - `AZURE_IP` (optional)
4.  **Push to Main**:
    - Any push to the `main` branch will now trigger an automatic deployment.

---
Enjoy chatting with Papales online!
