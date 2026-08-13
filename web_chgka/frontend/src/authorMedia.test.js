import test from 'node:test';
import assert from 'node:assert/strict';

import {
  AUTHOR_FALLBACK_SOURCE,
  SECTOR_THIRTEEN_SOURCE,
  authorMediaCaption,
  authorMediaSource,
  isAuthorMedia,
} from './authorMedia.js';


test('author media formats optional city and pack photo source', () => {
  const media = {
    presentation_kind: 'author',
    author_name: 'Елена Орлова',
    author_city: 'Минск',
    author_asset: 'photo',
    has_photo: true,
  };

  assert.equal(isAuthorMedia(media), true);
  assert.equal(authorMediaCaption(media), 'Елена Орлова (Минск)');
  assert.equal(authorMediaSource(media, '/media/token'), '/media/token');
});


test('author media uses fallback without a pack photo', () => {
  const media = {
    presentation_kind: 'author',
    author_name: 'Алексей Иванов',
    author_city: null,
    author_asset: 'fallback',
    has_photo: false,
  };

  assert.equal(authorMediaCaption(media), 'Алексей Иванов');
  assert.equal(authorMediaSource(media, '/media/token'), AUTHOR_FALLBACK_SOURCE);
});


test('sector thirteen uses its static image without an author caption', () => {
  const media = {
    presentation_kind: 'author',
    author_name: '13-й сектор',
    author_asset: 'sector13',
    has_photo: false,
  };

  assert.equal(authorMediaCaption(media), null);
  assert.equal(authorMediaSource(media, '/media/token'), SECTOR_THIRTEEN_SOURCE);
});
