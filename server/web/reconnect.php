<?php
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    header('Allow: POST');
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$requestPath = __DIR__ . '/reconnect.request';
if (file_put_contents($requestPath, '1', LOCK_EX) === false) {
    http_response_code(500);
    echo json_encode(['error' => 'Could not request a Navidrome check']);
    exit;
}

echo json_encode(['ok' => true]);
