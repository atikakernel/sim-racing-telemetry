import express from 'express';
import cors from 'cors';
import { DefaultAzureCredential } from "@azure/identity";
import { AIProjectClient } from "@azure/ai-projects";

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const projectEndpoint = "https://dicastellanosr-1278-resource.services.ai.azure.com/api/projects/dicastellanosr-1278";
const agentName = "papales";
const agentVersion = "2";

// Create AI Project client
const projectClient = new AIProjectClient(projectEndpoint, new DefaultAzureCredential());

app.post('/api/chat', async (req, res) => {
    try {
        const userMessage = req.body.message || "What is the size of France in square miles?";
        const openAIClient = Object.keys(projectClient).includes('getOpenAIClient') ? projectClient.getOpenAIClient() : null; 
        
        // Handling the fact that AIProjectClient structure might need proper instantiation for telemetry or chat
        // Wait, the user's code uses: const openAIClient = projectClient.getOpenAIClient();
        // and openAIClient.conversations.create and openAIClient.responses.create
        
        const client = projectClient.getOpenAIClient();
        
        console.log("\nCreating conversation with initial user message:", userMessage);
        const conversation = await client.conversations.create({
            items: [{ type: "message", role: "user", content: userMessage }]
        });
        
        console.log(`Created conversation (id: ${conversation.id})`);
        
        console.log("\nGenerating response...");
        const response = await client.responses.create(
            {
                conversation: conversation.id,
            },
            {
                body: { agent: { name: agentName, version: agentVersion, type: "agent_reference" } },
            }
        );
        
        console.log("Response output: ", response.output_text);
        res.json({ response: response.output_text, conversationId: conversation.id });
    } catch (error) {
        console.error("Error communicating with AI Project:", error);
        res.status(500).json({ error: error.message || "Internal Server Error" });
    }
});

const PORT = process.env.PORT || 3030;
app.listen(PORT, () => {
    console.log(`\n================================`);
    console.log(`Server listening on port ${PORT}`);
    console.log(`Open http://localhost:${PORT} in your browser.`);
    console.log(`================================\n`);
});
