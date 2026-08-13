import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  APP_BASE_PATH,
  appPath,
  normalizeBasePath,
} from './appPaths.js';


test('base paths have one leading and trailing slash', () => {
  assert.equal(normalizeBasePath(), '/');
  assert.equal(normalizeBasePath('/'), '/');
  assert.equal(normalizeBasePath(''), '/');
  assert.equal(normalizeBasePath('chgka'), '/chgka/');
  assert.equal(normalizeBasePath('/chgka'), '/chgka/');
  assert.equal(normalizeBasePath('//chgka///preview/'), '/chgka/preview/');
  assert.equal(normalizeBasePath(null), '/');
});


test('application paths work at root and below a prefix', () => {
  assert.equal(appPath('play'), '/play');
  assert.equal(appPath('/admin/history/', '/'), '/admin/history');
  assert.equal(appPath('', '/chgka/'), '/chgka/');
  assert.equal(appPath('/', '/chgka/'), '/chgka/');
  assert.equal(appPath('play', '/chgka/'), '/chgka/play');
  assert.equal(appPath('/images/table.png', 'chgka'), '/chgka/images/table.png');
});


test('plain node tests retain the root default used by local development', () => {
  assert.equal(APP_BASE_PATH, '/');
});


test('runtime source does not bypass the base path for static assets', () => {
  const sourceRoot = fileURLToPath(new URL('.', import.meta.url));
  const runtimeFiles = [];
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) {
        visit(path);
      } else if (
        ['.js', '.jsx'].includes(extname(entry.name))
        && !entry.name.endsWith('.test.js')
      ) {
        runtimeFiles.push(path);
      }
    }
  };
  visit(sourceRoot);

  const absoluteAssetPattern = /['"`]\/(?:images|sounds)\//;
  for (const path of runtimeFiles) {
    assert.doesNotMatch(
      readFileSync(path, 'utf8'),
      absoluteAssetPattern,
      `${path} must build static asset URLs through currentAppPath`,
    );
  }
});
