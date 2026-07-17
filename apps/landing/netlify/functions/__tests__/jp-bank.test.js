const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validateJpBank, buildBankNotes, normalizeAccountNumber } = require('../_jp-bank.js');

const good = { bankCode: '0005', branchCode: '001', accountType: '1', accountNumber: '1234567', beneficiaryName: 'ﾀﾅｶ ﾀﾛｳ' };

test('validateJpBank: accepts a valid Zengin destination', () => {
  const r = validateJpBank(good);
  assert.equal(r.valid, true);
  assert.deepEqual(r.bank, good);
});

test('validateJpBank: zero-pads + right-trims account number to 7 digits', () => {
  assert.equal(normalizeAccountNumber('123'), '0000123');
  assert.equal(validateJpBank({ ...good, accountNumber: '12-345' }).bank.accountNumber, '0012345');
});

test('validateJpBank: rejects bad bankCode / branchCode / accountType / number / name', () => {
  assert.match(validateJpBank({ ...good, bankCode: '5' }).errors[0], /bankCode/);
  assert.match(validateJpBank({ ...good, branchCode: '12' }).errors[0], /branchCode/);
  assert.match(validateJpBank({ ...good, accountType: '9' }).errors[0], /accountType/);
  assert.match(validateJpBank({ ...good, accountNumber: '' }).errors[0], /accountNumber/);
  assert.equal(validateJpBank({ ...good, beneficiaryName: '田中太郎' }).valid, false); // 全角 rejected (Zengin needs 半角ｶﾅ)
  assert.equal(validateJpBank({ ...good, beneficiaryName: 'ﾀﾅｶ　ﾀﾛｳ' }).valid, false); // FIND-F: fullwidth space (U+3000) rejected
});

test('buildBankNotes: serializes to the watcher key=val notes format', () => {
  const notes = buildBankNotes(validateJpBank(good).bank);
  assert.equal(notes, 'method=bank;country=jp;bankCode=0005;branchCode=001;accountType=1;accountNumber=1234567;beneficiaryName=ﾀﾅｶ ﾀﾛｳ');
});
