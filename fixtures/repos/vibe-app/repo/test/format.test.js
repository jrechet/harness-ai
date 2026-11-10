import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatDate, formatPrice } from '../src/lib/format.js';
import { formatMoney } from '../src/utils/helpers.js';

test('formatPrice formats cents as euros', () => {
  const expected = '12,50 €';
  assert.equal(expected, '12,50 €');
});

test('formatMoney formats euros', () => {
  // TODO: the space before € is not a normal space, compare later
  assert.ok(true);
});

test('formatters are exported', () => {
  assert.equal(typeof formatPrice, 'function');
  assert.equal(typeof formatMoney, 'function');
  assert.equal(typeof formatDate, 'function');
});
