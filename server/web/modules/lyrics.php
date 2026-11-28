<div id="navigation">
    <a href="/"><button id="standard-mode-button" type="button">standard view</button></a>
    <a href="/hudmode.php"><button id="hud-mode-button" type="button">phone HUD view</button></a>
    <a href="/lyriconlymode.php"><button id="lyric-mode-button" type="button">lyrics only view</button></a>
</div>

<div id="lyrics">
            
    <p id="previous-line">
        <span class="line-1"><?= escapeHtml($state['previous_line1']) ?></span>
        <span class="line-2"><?= escapeHtml($state['previous_line2'] ?: '') ?></span>
    </p>

    <p id="current-line">
        <span class="line-1"><?= escapeHtml($state['current_line1']) ?></span>
        <span class="line-2"><?= escapeHtml($state['current_line2'] ?: '') ?></span>
    </p>

    <p id="next-line">
        <span class="line-1"><?= escapeHtml($state['next_line1']) ?></span>
        <span class="line-2"><?= escapeHtml($state['next_line2'] ?: '') ?></span>
    </p>

</div>

<script src="scripts/lyrics.js"></script>