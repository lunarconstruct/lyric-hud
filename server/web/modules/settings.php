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