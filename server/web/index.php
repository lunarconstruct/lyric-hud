<?php
    // list of lyric format options for Japanese and Korean
    $japaneseFormatLabels = [
        'orig' => 'Original',
        'kana' => 'Kana',
        'hira' => 'Hiragana',
        'hepburn' => 'Romaji (Hepburn)',
        'kunrei' => 'Romaji (Kunrei)',
        'passport' => 'Romaji (Passport)',
        'none' => 'Hide this line',
    ];
    $koreanFormatLabels = [
        'orig' => 'Original',
        'romanized' => 'Romanized',
        'none' => 'Hide this line',
    ];

    // path to the settings file
    $settingsPath = __DIR__ . '/web_settings.json';
    $settingsSaved = false;

    // default settings
    $settings = [
        'ja_line1_format' => 'orig',
        'ja_line2_format' => 'hepburn',
        'ko_line1_format' => 'orig',
        'ko_line2_format' => 'romanized',
    ];

    // allowed formats for each setting
    $allowedFormats = [
        'ja_line1_format' => array_keys($japaneseFormatLabels),
        'ja_line2_format' => array_keys($japaneseFormatLabels),
        'ko_line1_format' => array_keys($koreanFormatLabels),
        'ko_line2_format' => array_keys($koreanFormatLabels),
    ];
    
    // load the saved settings if they exist
    if (is_file($settingsPath)) {
        $savedSettings = json_decode(file_get_contents($settingsPath), true);
        if (is_array($savedSettings)) {
            foreach (array_keys($settings) as $key) {
                $value = $savedSettings[$key] ?? null;
                if (is_string($value) && in_array($value, $allowedFormats[$key], true)) {
                    $settings[$key] = $value;
                }
            }
        }
    }

    // handle form submission to save settings
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $newSettings = [];
        foreach (array_keys($settings) as $key) {
            $value = $_POST[$key] ?? null;
            if (!is_string($value) || !in_array($value, $allowedFormats[$key], true)) {
                http_response_code(400);
                exit('Invalid lyric format.');
            }
            $newSettings[$key] = $value;
        }

        $temporarySettingsPath = $settingsPath . '.tmp';
        $encodedSettings = json_encode($newSettings, JSON_THROW_ON_ERROR);
        if (file_put_contents($temporarySettingsPath, $encodedSettings, LOCK_EX) === false
            || !rename($temporarySettingsPath, $settingsPath)) {
            http_response_code(500);
            exit('Could not save settings.');
        }

        $settings = $newSettings;
        $settingsSaved = true;
    }

    // default state of web ui
    $state = [
        'status' => 'waiting',
        'title' => '',
        'artist' => '',
        'current_line' => '',
        'lyrics' => '',
    ];
    // path to the state file
    $statePath = __DIR__ . '/web_state.json';

    // load the saved state if it exists
    if (is_file($statePath)) {
        $savedState = json_decode(file_get_contents($statePath), true);
        if (is_array($savedState)) {
            $state = array_merge($state, $savedState);
        }
    }

    // connection/credentials info
    $connection = [
        'status' => 'connecting...',
        'server' => '',
        'user' => '',
    ];
    // path to the credentials file
    $credentialsPath = __DIR__ . '/../credentials.json';

    // load the connection info if it exists
    if (is_file($credentialsPath)) {
        $savedConnection = json_decode(file_get_contents($credentialsPath), true);
        if (is_array($savedConnection)) {
            $connection = array_merge($connection, $savedConnection);
        }
    }

    function get_title(string $url){
        $str = file_get_contents($url);
        if(strlen($str)>0){
            $str = trim(preg_replace('/\s+/', ' ', $str)); // supports line breaks inside <title>
            preg_match("/\<title\>(.*)\<\/title\>/i",$str,$title); // ignore case
            return $title[1];
        }
    }

    $connectionServer = trim($connection['url'], '/rest') ?? '';
    $connectionServerTitle = get_title($connectionServer) ?? '';
    $connectionUser = $connection['params']['u'] ?? '';

    // function to escape HTML special characters
    function escapeHtml(string $value) {
        return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }
?>

<html>

    <head>
        
        <link rel="stylesheet" href="style.css">

    </head>

    <body>

        <h1>lyric-hud web ui</h1>

        <h2>connection info</h2>

        <p id="server-info">connected to <b><a href="<?= escapeHtml($connectionServer) ?>" target="_blank"><?= escapeHtml($connectionServerTitle) ?></a></b> as <b><?= escapeHtml($connectionUser) ?></b></p>

        <h2>playing now...</h2>

        <h4 id="now-playing"><?= escapeHtml($state['title'] ?: 'Nothing playing') ?> - <?= escapeHtml($state['artist']) ?></h4>
        <p id="playback-status">Status: <?= escapeHtml($state['status']) ?></p>

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

        <h2>settings</h2>
        <h3>Japanese lyric formatting</h3>
        <form method="post">
            <label for="ja_line1_format">Top line</label>
            <select id="ja_line1_format" name="ja_line1_format">
                <?php foreach ($japaneseFormatLabels as $value => $label): ?>
                    <option value="<?= escapeHtml($value) ?>" <?= $settings['ja_line1_format'] === $value ? 'selected' : '' ?>>
                        <?= escapeHtml($label) ?>
                    </option>
                <?php endforeach; ?>
            </select>
            <br>
            <label for="ja_line2_format">Bottom line</label>
            <select id="ja_line2_format" name="ja_line2_format">
                <?php foreach ($japaneseFormatLabels as $value => $label): ?>
                    <option value="<?= escapeHtml($value) ?>" <?= $settings['ja_line2_format'] === $value ? 'selected' : '' ?>>
                        <?= escapeHtml($label) ?>
                    </option>
                <?php endforeach; ?>
            </select>
            <br>
            <h3>Korean lyric formatting</h3>
            <label for="ko_line1_format">Top line</label>
            <select id="ko_line1_format" name="ko_line1_format">
                <?php foreach ($koreanFormatLabels as $value => $label): ?>
                    <option value="<?= escapeHtml($value) ?>" <?= $settings['ko_line1_format'] === $value ? 'selected' : '' ?>>
                        <?= escapeHtml($label) ?>
                    </option>
                <?php endforeach; ?>
            </select>
            <br>
            <label for="ko_line2_format">Bottom line</label>
            <select id="ko_line2_format" name="ko_line2_format">
                <?php foreach ($koreanFormatLabels as $value => $label): ?>
                    <option value="<?= escapeHtml($value) ?>" <?= $settings['ko_line2_format'] === $value ? 'selected' : '' ?>>
                        <?= escapeHtml($label) ?>
                    </option>
                <?php endforeach; ?>
            </select>
            <br>
            <input type="submit" value="save">
        </form>
        <?php if ($settingsSaved): ?>
            <p>Settings saved. They will apply from the next lyric line.</p>
        <?php endif; ?>
        <script>
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
                    document.getElementById('now-playing').textContent =
                        `${state.title || 'Nothing playing'} - ${state.artist || ''}`;
                    document.getElementById('playback-status').textContent =
                        `Status: ${state.status || 'waiting'}`;

                    updateLyricBlock('previous-line', state.previous_line1, state.previous_line2);
                    updateLyricBlock('current-line', state.current_line1, state.current_line2);
                    updateLyricBlock('next-line', state.next_line1, state.next_line2);
                } catch (error) {
                    console.error('Could not update now-playing info:', error);
                }
            }

            updateNowPlaying();
            setInterval(updateNowPlaying, 500);
        </script>
    </body>
</html>