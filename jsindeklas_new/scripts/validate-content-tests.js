// JavaScript in de Klas - content test validator
// Copyright (c) 2026 Robbe Wulgaert
// Citeer/vermeld als: Robbe Wulgaert, AI in de Klas, robbewulgaert.be

const fs = require("fs");
const path = require("path");

const ROOT_DIR = path.resolve(__dirname, "..");
const CHAPTERS_DIR = path.join(ROOT_DIR, "content", "chapters");

function walkFiles(directory, predicate, output = []) {
  if (!fs.existsSync(directory)) {
    return output;
  }

  fs.readdirSync(directory, { withFileTypes: true }).forEach((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walkFiles(entryPath, predicate, output);
    } else if (predicate(entryPath)) {
      output.push(entryPath);
    }
  });

  return output;
}

function relative(filePath) {
  return path.relative(ROOT_DIR, filePath).replace(/\\/g, "/");
}

function labelFor(testcase, index) {
  return testcase && testcase.label ? `"${testcase.label}"` : `#${index + 1}`;
}

function validateRegex(errors, filePath, context, pattern, flags = "g") {
  try {
    new RegExp(pattern, flags);
  } catch (error) {
    errors.push(`${relative(filePath)} ${context}: ongeldig regex-patroon (${error.message}).`);
  }
}

function validateReplacement(errors, filePath, testcase, testcaseIndex, replacement, replacementIndex) {
  const context = `testcase ${labelFor(testcase, testcaseIndex)}, replacement #${replacementIndex + 1}`;

  if (!replacement || typeof replacement !== "object" || Array.isArray(replacement)) {
    errors.push(`${relative(filePath)} ${context}: replacement moet een object zijn.`);
    return;
  }

  if (!Object.prototype.hasOwnProperty.call(replacement, "to")) {
    errors.push(`${relative(filePath)} ${context}: ontbreekt verplichte "to".`);
  }

  if (Object.prototype.hasOwnProperty.call(replacement, "from")) {
    errors.push(`${relative(filePath)} ${context}: gebruik "pattern" in plaats van een broze exacte "from".`);
  }

  if (typeof replacement.pattern !== "string" || replacement.pattern.length === 0) {
    errors.push(`${relative(filePath)} ${context}: ontbreekt een niet-leeg "pattern".`);
    return;
  }

  const flags = replacement.flags || (replacement.replaceAll === false ? "" : "g");
  validateRegex(errors, filePath, context, replacement.pattern, flags);
}

function validateEval(errors, filePath, testcase, testcaseIndex) {
  if (!testcase || !testcase.eval || testcase.eval.type !== "regex") {
    return;
  }

  const context = `testcase ${labelFor(testcase, testcaseIndex)}, eval`;
  if (typeof testcase.eval.pattern !== "string" || testcase.eval.pattern.length === 0) {
    errors.push(`${relative(filePath)} ${context}: regex-evaluatie mist een niet-leeg "pattern".`);
    return;
  }

  validateRegex(errors, filePath, context, testcase.eval.pattern, testcase.eval.flags || "i");
}

function validateTestsFile(filePath, stats, errors) {
  stats.files += 1;

  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    errors.push(`${relative(filePath)}: JSON kon niet gelezen worden (${error.message}).`);
    return;
  }

  if (!Array.isArray(parsed)) {
    errors.push(`${relative(filePath)}: tests.json moet een array zijn.`);
    return;
  }

  stats.testcases += parsed.length;
  parsed.forEach((testcase, testcaseIndex) => {
    if (!testcase || typeof testcase !== "object" || Array.isArray(testcase)) {
      errors.push(`${relative(filePath)} testcase #${testcaseIndex + 1}: testcase moet een object zijn.`);
      return;
    }

    validateEval(errors, filePath, testcase, testcaseIndex);

    if (!Array.isArray(testcase.replacements)) {
      return;
    }

    stats.replacements += testcase.replacements.length;
    testcase.replacements.forEach((replacement, replacementIndex) => {
      validateReplacement(errors, filePath, testcase, testcaseIndex, replacement, replacementIndex);
    });
  });
}

function main() {
  const testFiles = walkFiles(CHAPTERS_DIR, filePath => path.basename(filePath) === "tests.json")
    .sort((a, b) => relative(a).localeCompare(relative(b), "nl-BE", { numeric: true }));

  const stats = {
    files: 0,
    testcases: 0,
    replacements: 0,
  };
  const errors = [];

  testFiles.forEach(filePath => validateTestsFile(filePath, stats, errors));

  if (errors.length > 0) {
    console.error("Content testvalidatie vond problemen:");
    errors.forEach(error => console.error(`- ${error}`));
    process.exit(1);
  }

  console.log(`Content testvalidatie geslaagd: ${stats.files} tests.json-bestanden, ${stats.testcases} testcases, ${stats.replacements} flexibele replacement(s).`);
}

main();
