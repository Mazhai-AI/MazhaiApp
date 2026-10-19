const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('frontend/js/i18n.js', 'utf8').replace(/^export function /gm, 'function ');
const storage = new Map();
const context = {
  localStorage: {
    getItem(key) { return storage.has(key) ? storage.get(key) : null; },
    setItem(key, value) { storage.set(key, String(value)); },
  },
};
vm.runInNewContext(source + '\nglobalThis.languageApi = { getLanguage, setLanguage, t };', context);

const languageApi = context.languageApi;
assert.equal(languageApi.getLanguage(), 'en', 'English is the default');
assert.equal(languageApi.setLanguage('ta'), 'ta');
assert.equal(languageApi.getLanguage(), 'ta', 'Tamil choice persists');
assert.equal(languageApi.t('Settings'), 'அமைப்புகள்');
assert.equal(languageApi.t('Chennai'), 'சென்னை');
assert.equal(languageApi.t('Tiruchirappalli'), 'திருச்சிராப்பள்ளி');
assert.equal(languageApi.setLanguage('en'), 'en');
assert.equal(languageApi.t('Settings'), 'Settings');
assert.equal(languageApi.getLanguage(), 'en', 'switching back to English persists');
console.log('Language preference and Tamil translation tests passed.');
