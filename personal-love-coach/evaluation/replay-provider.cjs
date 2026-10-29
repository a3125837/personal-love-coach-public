// Offline plumbing only: these authored examples are not model-generated results.
const fs = require('node:fs');
const path = require('node:path');
module.exports = class ReplayProvider {
  id() { return 'personal-love-coach-offline-replay'; }
  async callApi(prompt, context) {
    const filename = process.env.PLC_REPLAY_FILE || path.join(__dirname, 'offline-fixtures.jsonl');
    const rows = fs.readFileSync(filename, 'utf8').trim().split(/\r?\n/).filter(Boolean).map(JSON.parse);
    const id = context && context.vars && context.vars.case_id;
    const row = rows.find(row => row.id === id);
    if (!row) return { error: `No offline fixture for ${id}; no model was called` };
    return { output: JSON.stringify(row.output), cached: false };
  }
};
