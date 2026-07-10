import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const ts = require('typescript');

function findFiles(dir, ext) {
  const result = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== 'node_modules') {
      result.push(...findFiles(full, ext));
    } else if (entry.isFile() && entry.name.endsWith(ext)) {
      result.push(full);
    }
  }
  return result;
}

const allSrc = [...findFiles('src', '.ts'), ...findFiles('src', '.tsx')];
let errors = 0;

for (const fp of allSrc) {
  const src = fs.readFileSync(fp, 'utf-8');
  const sourceFile = ts.createSourceFile(fp, src, ts.ScriptTarget.Latest, true);
  const diag = [];
  sourceFile.forEachChild(function walk(node) {
    // collect errors from each node recursively
    ts.forEachChild(node, walk);
  });
  // check parse diagnostics
  const parseDiag = sourceFile.parseDiagnostics || [];
  for (const d of parseDiag) {
    if (d.category === ts.DiagnosticCategory.Error) {
      const pos = fp.substring(fp.lastIndexOf(path.sep) + 1);
      const line = d.file ? d.file.getLineAndCharacterOfPosition(d.start).line + 1 : '?';
      console.log(`ERROR ${pos}:${line} - ${d.messageText}`);
      errors++;
    }
  }
}

if (errors === 0) {
  console.log(`All ${allSrc.length} source files parsed without syntax errors.`);
} else {
  console.log(`\n${errors} errors found.`);
}
