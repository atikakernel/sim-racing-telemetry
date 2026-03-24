document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const clearChatBtn = document.getElementById('clear-chat');

    const addMessage = (text, sender) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender, 'animate-in');
        
        const bubble = document.createElement('div');
        bubble.classList.add('bubble');
        bubble.textContent = text;
        
        messageDiv.appendChild(bubble);
        chatWindow.appendChild(messageDiv);
        
        // Scroll to bottom
        chatWindow.scrollTop = chatWindow.scrollHeight;
    };

    const handleChat = async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to UI
        addMessage(message, 'user');
        userInput.value = '';

        try {
            // Loading indicator (optional, but good for UX)
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
            });

            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }

            const data = await response.json();
            addMessage(data.reply, 'ai');
        } catch (error) {
            console.error('Error:', error);
            addMessage('Lo siento, hubo un error al procesar tu mensaje.', 'ai');
        }
    };

    chatForm.addEventListener('submit', handleChat);

    clearChatBtn.addEventListener('click', () => {
        chatWindow.innerHTML = '';
        addMessage('¡Hola! Soy tu asistente de Azure AI. ¿En qué puedo ayudarte hoy?', 'ai');
    });
});
