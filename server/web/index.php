<?php include 'prehtml.php' ?>

<html>

    <head>
        
        <link rel="stylesheet" href="styles/style.css">
        <style>
            #lyric-mode-button {
                opacity: 100%
            }
            #standard-mode-button {
                opacity: 50%
            }
            #hud-mode-button {
                opacity: 100%
            }
        </style>

    </head>

    <body>

        <h1>lyric-hud web ui</h1>

        <h2>connection info</h2>

        <p id="server-info">connected to <b><a href="<?= escapeHtml($connectionServer) ?>" target="_blank"><?= escapeHtml($connectionServerTitle) ?></a></b> as <b><?= escapeHtml($connectionUser) ?></b></p>
        <button id="reconnect-button" type="button">Reconnect</button>
        <span id="reconnect-status" aria-live="polite"></span>
        <script src="scripts/connection.js"></script>

        <h2>playing now...</h2>

        <h4 id="now-playing"><?= escapeHtml($state['title'] ?: 'Nothing playing') ?> - <?= escapeHtml($state['artist']) ?></h4>
        <p id="playback-status">Status: <?= escapeHtml($state['status']) ?></p>
        
        <?php include 'modules/lyrics.php' ?>

        <?php include 'modules/settings.php' ?>
        
                   

    </body>
</html>