import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ADMIN_ENTRY_PATH,
  ADMIN_HISTORY_PATH,
  ENTRYPOINT_ADMIN,
  ENTRYPOINT_ADMIN_HISTORY,
  ENTRYPOINT_PLAYER,
  PLAYER_ENTRY_PATH,
  entrypointDocumentTitle,
  entrypointLoginSubtitle,
  resolveEntrypoint,
  isAdminEntrypoint,
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

test('history has its own exact admin entrypoint', () => {
  assert.deepEqual(resolveEntrypoint('/admin/history'), {
    entrypoint: ENTRYPOINT_ADMIN_HISTORY,
    canonicalPath: ADMIN_HISTORY_PATH,
  });
  assert.deepEqual(resolveEntrypoint('/admin/history/'), {
    entrypoint: ENTRYPOINT_ADMIN_HISTORY,
    canonicalPath: ADMIN_HISTORY_PATH,
  });
  assert.equal(isAdminEntrypoint(ENTRYPOINT_ADMIN), true);
  assert.equal(isAdminEntrypoint(ENTRYPOINT_ADMIN_HISTORY), true);
  assert.equal(isAdminEntrypoint(ENTRYPOINT_PLAYER), false);
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
  assert.equal(resolveEntrypoint('/admin/history/export').entrypoint, ENTRYPOINT_PLAYER);
  assert.equal(resolveEntrypoint('/play/admin').entrypoint, ENTRYPOINT_PLAYER);
});


test('entrypoints provide distinct document titles and admin login subtitles', () => {
  assert.equal(
    entrypointDocumentTitle(ENTRYPOINT_ADMIN),
    'Что? Где? Когда? — Ведущий',
  );
  assert.equal(entrypointLoginSubtitle(ENTRYPOINT_ADMIN), '[ведущий]');
  assert.equal(
    entrypointDocumentTitle(ENTRYPOINT_ADMIN_HISTORY),
    'Что? Где? Когда? — История игр',
  );
  assert.equal(
    entrypointLoginSubtitle(ENTRYPOINT_ADMIN_HISTORY),
    '[история игр]',
  );
  assert.equal(entrypointDocumentTitle(ENTRYPOINT_PLAYER), 'Что? Где? Когда?');
  assert.equal(entrypointLoginSubtitle(ENTRYPOINT_PLAYER), null);
});
