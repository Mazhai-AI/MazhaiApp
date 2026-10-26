const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('frontend/js/app.js', 'utf8');
const start = source.indexOf('function sumKnown(days){');
const end = source.indexOf('\n', start);
assert.ok(start >= 0 && end > start, 'sumKnown helper must exist in app.js');
const context = {};
vm.runInNewContext(source.slice(start, end) + '\nglobalThis.sumKnown = sumKnown;', context);

// Missing values are unknown, never zero.
assert.equal(context.sumKnown([]), null);
assert.equal(context.sumKnown(undefined), null);
assert.equal(context.sumKnown([{ precipitation_mm: null }, { precipitation_mm: undefined }, {}]), null);
assert.equal(context.sumKnown([{ precipitation_mm: 1.5 }, { precipitation_mm: null }, { precipitation_mm: 2 }]), 3.5);
assert.equal(context.sumKnown([{ precipitation_mm: 0 }, { precipitation_mm: 0 }]), 0, 'a real 0 mm stays 0');
assert.equal(context.sumKnown([{ precipitation_mm: NaN }, { precipitation_mm: '4' }]), null, 'only finite numbers count');
console.log('App helper tests passed.');
