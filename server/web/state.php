<?php
header('Content-Type: application/json; charset=utf-8');

$defaultsContents = file_get_contents(__DIR__ . '/default_state.json');
if ($defaultsContents === false) {
    throw new RuntimeException('Could not read default web state.');
}
$state = json_decode($defaultsContents, true, 512, JSON_THROW_ON_ERROR);
if (!is_array($state)) {
    throw new RuntimeException('Default web state must be a JSON object.');
}
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
