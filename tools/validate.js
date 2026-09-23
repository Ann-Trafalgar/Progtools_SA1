const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const questions = JSON.parse(fs.readFileSync(path.join(root, 'data', 'questions.json'), 'utf8'));
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

assert(questions.length === 31, `Expected 31 questions, found ${questions.length}`);
assert(new Set(questions.map(question => question.id)).size === 31, 'Question IDs are not unique');

for (const [assessment, expected] of Object.entries({ FA1: 18, FA2: 13 })) {
  const items = questions.filter(question => question.assessment === assessment);
  assert(items.length === expected, `${assessment} should contain ${expected} questions`);
  assert(items.every((question, index) => question.number === index + 1), `${assessment} numbering is not sequential`);
}

for (const question of questions) {
  assert(question.text?.trim(), `${question.id} has no text`);
  assert(question.options?.length >= 2, `${question.id} has fewer than two options`);
  assert(question.answer?.length === 1, `${question.id} should have one answer`);
  const answerIndex = question.answer[0]?.charCodeAt(0) - 65;
  assert(answerIndex >= 0 && answerIndex < question.options.length, `${question.id} has an invalid answer`);
  assert(!question.text.includes('\n'), `${question.id} contains a PDF line-wrap artifact`);
}

const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'assets', 'app.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'assets', 'style.css'), 'utf8');
const htmlIds = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
const requestedIds = new Set([...app.matchAll(/\$\('([^']+)'\)/g)].map(match => match[1]));
for (const id of requestedIds) assert(htmlIds.has(id), `app.js requests missing HTML id #${id}`);

assert(app.includes("const assessmentOrder = ['FA1', 'FA2']"), 'Assessment picker order is incorrect');
assert(app.includes("state.assessmentId === 'all' ? question.globalNumber : question.number"), 'Combined reviewer numbering is incorrect');
assert(css.includes('@media(max-width:620px)'), 'Phone breakpoint is missing');
assert(css.includes('@media(max-width:360px)'), 'Small-phone breakpoint is missing');
assert(css.includes('env(safe-area-inset-left)'), 'Mobile safe-area padding is missing');
assert(css.includes('grid-template-columns:repeat(5,minmax(0,1fr))'), 'Phone question picker layout is missing');
assert(css.split('{').length === css.split('}').length, 'CSS braces are unbalanced');

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}

console.log('Validated 31 questions, FA1/FA2 grouping, answers, formatting, and all DOM references.');
