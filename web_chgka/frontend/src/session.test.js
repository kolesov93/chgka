import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ADMIN_TOKEN_KEY,
  PLAYER_TOKEN_KEY,
  getAdminExpiryMs,
  getExpiredAdminSession,
  getSessionRestorePayload,
  saveAdminToken,
} from './session.js';

function createStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return values.get(key) ?? null;
    },
    removeItem(key) {
      values.delete(key);
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}

test('session restore prefers an admin token and emits only one payload', () => {
  const storage = createStorage({
    [ADMIN_TOKEN_KEY]: 'admin-token',
    [PLAYER_TOKEN_KEY]: 'player-token',
  });

  assert.deepEqual(getSessionRestorePayload(storage), { token: 'admin-token' });
});

test('session restore falls back to the player token', () => {
  const storage = createStorage({ [PLAYER_TOKEN_KEY]: 'player-token' });

  assert.deepEqual(getSessionRestorePayload(storage), {
    player_token: 'player-token',
  });
  assert.equal(getSessionRestorePayload(createStorage()), null);
});

test('admin login removes an obsolete player token', () => {
  const storage = createStorage({ [PLAYER_TOKEN_KEY]: 'player-token' });

  saveAdminToken(storage, 'admin-token');

  assert.equal(storage.getItem(ADMIN_TOKEN_KEY), 'admin-token');
  assert.equal(storage.getItem(PLAYER_TOKEN_KEY), null);
});

test('expired admin state clears private and joined-session data', () => {
  assert.deepEqual(getExpiredAdminSession({ message: 'Войдите снова' }), {
    role: 'player',
    name: '',
    hasJoined: false,
    isPending: false,
    packInfo: null,
    adminQuestion: null,
    notice: 'Войдите снова',
  });
});

test('admin expiry accepts only a positive finite server timestamp', () => {
  assert.equal(getAdminExpiryMs({ expires_at_ms: 123_456 }), 123_456);
  assert.equal(getAdminExpiryMs({ expires_at_ms: '123456' }), null);
  assert.equal(getAdminExpiryMs({ expires_at_ms: Number.POSITIVE_INFINITY }), null);
  assert.equal(getAdminExpiryMs({}), null);
});
