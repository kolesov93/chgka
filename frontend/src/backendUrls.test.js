import test from 'node:test';
import assert from 'node:assert/strict';

import {
  backendHttpUrl,
  backendSocketPath,
} from './backendUrls.js';


test('development backend keeps its separate localhost origin', () => {
  assert.equal(
    backendHttpUrl('media/token', { isDevelopment: true, basePath: '/chgka/' }),
    'http://localhost:8000/media/token',
  );
  assert.equal(
    backendHttpUrl('intro/author-photo/1/0', { isDevelopment: true }),
    'http://localhost:8000/intro/author-photo/1/0',
  );
  assert.equal(
    backendSocketPath({ isDevelopment: true, basePath: '/chgka/' }),
    '/socket.io',
  );
});


test('production backend URLs share the configured application prefix', () => {
  assert.equal(
    backendHttpUrl('media/token', { basePath: '/' }),
    '/media/token',
  );
  assert.equal(
    backendHttpUrl('media/token', { basePath: '/chgka/' }),
    '/chgka/media/token',
  );
  assert.equal(
    backendHttpUrl('intro/author-photo/1/0', { basePath: '/chgka/' }),
    '/chgka/intro/author-photo/1/0',
  );
  assert.equal(backendSocketPath({ basePath: '/' }), '/socket.io');
  assert.equal(backendSocketPath({ basePath: '/chgka/' }), '/chgka/socket.io');
});
