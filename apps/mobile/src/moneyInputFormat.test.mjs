import assert from 'node:assert/strict';
import test from 'node:test';
import { formatMoneyInput } from './moneyInputFormat.ts';

test('digitação sequencial interpreta os números como centavos', () => {
  assert.equal(formatMoneyInput('2'), '0,02');
  assert.equal(formatMoneyInput('0,025', '0,02'), '0,25');
  assert.equal(formatMoneyInput('0,125', '0,12'), '1,25');
});

test('colagem, apagar e limite preservam valores corretos', () => {
  assert.equal(formatMoneyInput('R$ 1.234,56'), '1.234,56');
  assert.equal(formatMoneyInput('1,2', '1,25'), '0,12');
  assert.equal(formatMoneyInput('0,0', '0,01'), '0,00');
  assert.equal(formatMoneyInput('0,0', '0,00'), '');
  assert.equal(formatMoneyInput('1234567890', '1,25'), '1,25');
});
