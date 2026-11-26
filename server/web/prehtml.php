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

    $defaultsContents = file_get_contents(__DIR__ . '/default_state.json');
    if ($defaultsContents === false) {
        throw new RuntimeException('Could not read default web state.');
    }
    $state = json_decode($defaultsContents, true, 512, JSON_THROW_ON_ERROR);
    if (!is_array($state)) {
        throw new RuntimeException('Default web state must be a JSON object.');
    }
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