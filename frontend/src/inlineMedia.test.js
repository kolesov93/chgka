import test from 'node:test';
import assert from 'node:assert/strict';

import { inlineImagePreviews } from './inlineMedia.js';


const image = {
  media_ref: 'image-ref',
  type: 'image',
  name: 'painting.jpg',
};


test('resolved image placeholder becomes a private inline thumbnail', () => {
  const html = '<p>До <span class="media-placeholder" data-media-ref="image-ref"></span> после</p>';
  const rendered = inlineImagePreviews(html, [image], {
    'image-ref': {
      status: 'ready',
      preview: { url: '/media/private-token?x=1&y=2' },
    },
  });

  assert.match(rendered, /<button type="button" class="media-placeholder media-inline-preview"/);
  assert.match(rendered, /data-media-ref="image-ref"/);
  assert.match(rendered, /src="\/media\/private-token\?x=1&amp;y=2"/);
  assert.match(rendered, /alt="painting.jpg"/);
  assert.equal(rendered.includes('<p>До '), true);
  assert.equal(rendered.includes(' после</p>'), true);
});


test('pending and failed images render visible fallbacks', () => {
  const placeholder = '<span class="media-placeholder" data-media-ref="image-ref"></span>';

  assert.match(inlineImagePreviews(placeholder, [image]), /Загрузка изображения…/);
  assert.match(
    inlineImagePreviews(placeholder, [image], { 'image-ref': { status: 'error' } }),
    /Изображение недоступно/,
  );
});


test('non-image and unknown placeholders stay unchanged', () => {
  const audioPlaceholder = '<span class="media-placeholder" data-media-ref="audio-ref"></span>';
  const unknownPlaceholder = '<span class="media-placeholder" data-media-ref="unknown-ref"></span>';
  const html = `${audioPlaceholder}${unknownPlaceholder}`;

  assert.equal(
    inlineImagePreviews(html, [{ media_ref: 'audio-ref', type: 'audio', name: 'sound.mp3' }]),
    html,
  );
});


test('thumbnail attributes escape descriptor and resolved values', () => {
  const descriptor = {
    media_ref: 'safe-ref',
    type: 'image',
    name: '"bad" <name>.jpg',
  };
  const html = '<span class="media-placeholder" data-media-ref="safe-ref"></span>';
  const rendered = inlineImagePreviews(html, [descriptor], {
    'safe-ref': {
      status: 'ready',
      preview: { url: '/media/a"b<c' },
    },
  });

  assert.match(rendered, /src="\/media\/a&quot;b&lt;c"/);
  assert.match(rendered, /alt="&quot;bad&quot; &lt;name&gt;.jpg"/);
  assert.equal(rendered.includes('src="/media/a"b<c"'), false);
});
