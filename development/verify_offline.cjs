// Execute the exact offline provider and assertions without a model or network.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..', 'personal-love-coach');
const config = JSON.parse(fs.readFileSync(path.join(root, 'evaluation/promptfooconfig.yaml'), 'utf8'));
const Provider = require(path.join(root, 'evaluation/replay-provider.cjs'));
(async () => {
  const provider = new Provider();
  const results = [];
  for (const test of config.tests) {
    const prompt = config.prompts[0].replace('{{instructions}}', test.vars.instructions).replace('{{input}}', test.vars.input);
    if (/{{[^}]+}}/.test(prompt)) throw new Error('Unresolved prompt variable');
    const response = await provider.callApi(prompt, { vars: test.vars });
    if (response.error) throw new Error(response.error);
    const passed = test.assert.every(assertion => {
      if (assertion.type !== 'javascript') throw new Error('Offline test unexpectedly requires a judge');
      return Function('output', 'context', `return ${assertion.value}`)(response.output, {vars: test.vars}) === true;
    });
    results.push({id: test.description, passed});
  }
  const missing = await provider.callApi('', {vars: {case_id: 'missing'}});
  if (!missing.error) throw new Error('Missing fixtures must fail closed');
  if (!results.every(result => result.passed)) throw new Error('Offline assertion failure');
  const report = {kind: 'hand-authored-offline-replay-not-model-evaluation', cases: results.length,
                  passed: results.filter(result => result.passed).length, missing_fixture_rejected: true, results};
  const out = path.join(root, 'evaluation/reports/offline-adapter.json');
  fs.mkdirSync(path.dirname(out), {recursive: true});
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  process.stdout.write(JSON.stringify(report) + '\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
