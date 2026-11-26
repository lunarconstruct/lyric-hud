function updateLyricBlock(elementId, line1, line2) {
    const container = document.getElementById(elementId);
    if (!container) return;

    let span1 = container.querySelector('.line-1');
    let span2 = container.querySelector('.line-2');

    if (!span1 || !span2) {
        container.innerHTML = '<span class="line-1"></span><span class="line-2"></span>';
        span1 = container.querySelector('.line-1');
        span2 = container.querySelector('.line-2');
    }

    span1.textContent = line1 || '';
    span2.textContent = line2 || '';
}

async function updateNowPlaying() {
    try {
        const response = await fetch('state.php', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const state = await response.json();

        const nowPlayingEl = document.getElementById('now-playing');
        if (nowPlayingEl) {
            nowPlayingEl.textContent = `${state.title || 'Nothing playing'} - ${state.artist || ''}`;
        }

        const statusEl = document.getElementById('playback-status');
        if (statusEl) {
            statusEl.textContent = `Status: ${state.status || 'waiting'}`;
        }

        updateLyricBlock('previous-line', state.previous_line1, state.previous_line2);
        updateLyricBlock('current-line', state.current_line1, state.current_line2);
        updateLyricBlock('next-line', state.next_line1, state.next_line2);
    } catch (error) {
        console.error('Could not update now-playing info:', error);
    }
}


updateNowPlaying();
setInterval(updateNowPlaying, 500);