document.getElementById('reconnect-button').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    const status = document.getElementById('reconnect-status');
    button.disabled = true;
    status.textContent = 'Requesting check...';
    try {
        const response = await fetch('../reconnect.php', { method: 'POST' });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        status.textContent = 'Check requested.';
    } catch (error) {
        status.textContent = 'Could not request a check.';
        console.error('Could not request a reconnect:', error);
    } finally {
        button.disabled = false;
    }
});