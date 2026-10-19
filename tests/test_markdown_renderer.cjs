const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('frontend/js/app.js', 'utf8');
const start = source.indexOf('function renderInlineMarkdown(value){');
const end = source.indexOf('\nfunction renderMarkdown(message){', start);
assert.ok(start >= 0 && end > start, 'inline Markdown renderer must exist in app.js');
const rendererSource = source.slice(start, end);
const context = {
  escapeHTML(value) {
    return String(value ?? '').replace(/[&<>\"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#39;',
    })[char]);
  },
};
vm.runInNewContext(rendererSource + '\nglobalThis.renderInlineMarkdown = renderInlineMarkdown;', context);

assert.equal(
  context.renderInlineMarkdown('Rainfall is **34.8 mm** over the next 48 hours.'),
  'Rainfall is <strong>34.8 mm</strong> over the next 48 hours.',
);
assert.equal(
  context.renderInlineMarkdown('The forecast shows \\*\\*heavy rainfall\\*\\*.'),
  'The forecast shows <strong>heavy rainfall</strong>.',
);
assert.equal(
  context.renderInlineMarkdown('<img src=x onerror=alert(1)> and **bold text**'),
  '&lt;img src=x onerror=alert(1)&gt; and <strong>bold text</strong>',
);
console.log('Inline Markdown renderer tests passed.');
