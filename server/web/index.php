<?php include 'prehtml.php' ?>

<html>

    <head>
        
        <link rel="stylesheet" href="style.css">

    </head>

    <body>

        <h1>lyric-hud web ui</h1>

        <h2>connection info</h2>

        <p id="server-info">connected to <b><a href="<?= escapeHtml($connectionServer) ?>" target="_blank"><?= escapeHtml($connectionServerTitle) ?></a></b> as <b><?= escapeHtml($connectionUser) ?></b></p>
        <button id="reconnect-button" type="button">Reconnect</button>
        <span id="reconnect-status" aria-live="polite"></span>

        <h2>playing now...</h2>

        <h4 id="now-playing"><?= escapeHtml($state['title'] ?: 'Nothing playing') ?> - <?= escapeHtml($state['artist']) ?></h4>
        <p id="playback-status">Status: <?= escapeHtml($state['status']) ?></p>
        
        <a href="hudmode.php"><button id="hud-mode-button" type="button">enable phone HUD mode</button></a>
        <?php include 'modules/lyrics.php' ?>

        <?php include 'modules/settings.php' ?>
        
        <script src="scripts/connection.js"></script>           

    </body>
</html>