<?php
header('Content-Type: application/json; charset=utf-8');

$state = [
    'status' => 'waiting',
    'title' => '',
    'artist' => '',
    'current_line' => '',
    'lyrics' => '',
    'previous_line1' => '',
    'previous_line2' => '',
    'current_line1' => '-- waiting for a song... --',
    'current_line2' => '',
    'next_line1' => '',
    'next_line2' => '',
    'lyrics' => '',
];
$statePath = __DIR__ . '/web_state.json';

if (is_file($statePath)) {
    $contents = file_get_contents($statePath);
    if ($contents === false) {
        http_response_code(500);
        echo json_encode(['error' => 'Could not read playback state']);
        exit;
    }

    $savedState = json_decode($contents, true);
    if (!is_array($savedState)) {
        http_response_code(500);
        echo json_encode(['error' => 'Playback state is not valid JSON']);
        exit;
    }

    $state = array_merge($state, $savedState);
}

echo json_encode($state, JSON_UNESCAPED_UNICODE);
