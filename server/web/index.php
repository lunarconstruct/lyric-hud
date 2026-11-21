<?php
    $nowPlaying = 'test by test'
?>

<html>
    <head>

    </head>
    <body>
        <h1>lyric-hud web ui</h1>
        <p> woah fun </p>

        <h2>playing now...</h2>
        <p><?php echo $nowPlaying ?></p>

        <h2>settings</h2>
        <h3>lyric formatting</h3>
        <h4>dual-line format for non-latin characters</h4>
        <form action="/" method="post">
        <label for="line_1_format">top line will display </label>
            <select id="line_1_format" name="line 1 format">
                <option value="orig" selected>original</option>
                <option value="kana">kanji/kana</option>
                <option value="romaji">romaji</option>
                <option value="hiragana">hiragana</option>
                <option value="katakana">katakana</option>
            </select>
            <br>
        <label for="line_2_format">bottom line will display </label>
            <select id="line_2_format" name="line 2 format">
                <option value="orig">original</option>
                <option value="kana">kanji/kana</option>
                <option value="romaji" selected>romaji</option>
                <option value="hiragana">hiragana</option>
                <option value="katakana">katakana</option>
            </select>
            <br>
            <input type="submit" value="save">
        </form>

    </body>
</html>