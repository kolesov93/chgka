import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ADMIN_ENTRY_PATH,
  ENTRYPOINT_ADMIN,
  ENTRYPOINT_PLAYER,
  PLAYER_ENTRY_PATH,
  resolveEntrypoint,
} from './entrypoint.js';


test('admin paths resolve only to the host entrypoint', () => {
  assert.deepEqual(resolveEntrypoint('/admin'), {
    entrypoint: ENTRYPOINT_ADMIN,
    canonicalPath: ADMIN_ENTRY_PATH,
  });
  assert.deepEqual(resolveEntrypoint('/admin/'), {
    entrypoint: ENTRYPOINT_ADMIN,
    canonicalPath: ADMIN_ENTRY_PATH,
  });
});


test('player and fallback paths resolve to the player entrypoint', () => {
  for (const path of ['/play', '/play/', '/', '/unknown', '', null]) {
    assert.deepEqual(resolveEntrypoint(path), {
      entrypoint: ENTRYPOINT_PLAYER,
      canonicalPath: PLAYER_ENTRY_PATH,
    });
  }
});


test('nested admin-looking paths do not expose the host entrypoint', () => {
  assert.equal(resolveEntrypoint('/admin/reset').entrypoint, ENTRYPOINT_PLAYER);
  assert.equal(resolveEntrypoint('/play/admin').entrypoint, ENTRYPOINT_PLAYER);
});
