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
        
        if (sender === 'ai' && typeof marked !== 'undefined') {
            // Check for JSON chart data
            const chartMatch = text.match(/\{[\s\S]*"action"\s*:\s*"chart"[\s\S]*\}/);
            let cleanText = text;
            let chartData = null;

            if (chartMatch) {
                try {
                    chartData = JSON.parse(chartMatch[0]);
                    cleanText = text.replace(chartMatch[0], '').trim();
                } catch (e) {
                    console.error("Error parsing chat-chart:", e);
                }
            }

            bubble.innerHTML = marked.parse(cleanText);

            if (chartData) {
                const canvas = document.createElement('canvas');
                canvas.style.marginTop = '15px';
                canvas.style.maxWidth = '100%';
                bubble.appendChild(canvas);
                
                setTimeout(() => {
                    new Chart(canvas, {
                        type: chartData.chartType || 'bar',
                        data: {
                            labels: chartData.labels,
                            datasets: [{
                                label: chartData.title || 'Estadísticas F1',
                                data: chartData.data,
                                backgroundColor: 'rgba(138, 43, 226, 0.6)',
                                borderColor: 'rgba(138, 43, 226, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' } } }
                        }
                    });
                }, 100);
            }
        } else {
            bubble.textContent = text;
        }
        
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
            addMessage(data.reply || data.response || "No hubo respuesta.", 'ai');
        } catch (error) {
            console.error('Error:', error);
            addMessage('Lo siento, hubo un error al procesar tu mensaje.', 'ai');
        }
    };

    chatForm.addEventListener('submit', handleChat);

    clearChatBtn.addEventListener('click', () => {
        chatWindow.innerHTML = '';
        addMessage('¡Hola! Soy tu experto de Azure AI en Fórmula 1. ¿Qué datos o estadísticas de la máxima categoría quieres analizar hoy?', 'ai');
    });
});
