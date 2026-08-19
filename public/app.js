document.addEventListener('DOMContentLoaded', () => {
    const statusDot = document.getElementById('status-dot');
    const apiMessage = document.getElementById('api-message');
    const generateBtn = document.getElementById('generate-btn');

    // API Health Check
    async function checkApiStatus() {
        try {
            const response = await fetch('/api');
            if (response.ok) {
                const data = await response.json();
                statusDot.className = 'status-indicator online';
                apiMessage.textContent = 'API Bağlantısı Başarılı: ' + data.message;
                apiMessage.style.color = 'var(--success)';
                generateBtn.disabled = false;
            } else {
                throw new Error('API Hatası');
            }
        } catch (error) {
            statusDot.className = 'status-indicator offline';
            apiMessage.textContent = 'API Sunucusuna Ulaşılamıyor (Yerel Geliştirme mi?)';
            apiMessage.style.color = 'var(--error)';
            
            // Allow testing UI anyway if local
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                generateBtn.disabled = false;
                apiMessage.textContent += ' (Lokal Test Modu)';
            }
        }
    }

    // Button Click Handler
    generateBtn.addEventListener('click', () => {
        generateBtn.disabled = true;
        const originalText = generateBtn.textContent;
        generateBtn.textContent = 'Planlanıyor...';
        
        // Mock a 2 second wait for UI demonstration
        setTimeout(() => {
            alert('Bu aşamada Python Algoritması devreye girecek!');
            generateBtn.textContent = originalText;
            generateBtn.disabled = false;
        }, 2000);
    });

    // Run check on load
    checkApiStatus();
});
