// JavaScript in de Klas - evaluatievalidatie
// Copyright (c) 2026 Robbe Wulgaert
// Citeer/vermeld als: Robbe Wulgaert, AI in de Klas, robbewulgaert.be

const fs = require("fs");
const path = require("path");

const ROOT_DIR = path.resolve(__dirname, "..");
const EVAL_DIR = path.join(ROOT_DIR, "evaluaties");
const ASSESSMENTS_PATH = path.join(EVAL_DIR, "assessments.json");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function expect(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function launcherTargets(wrapperHtml) {
  return Array.from(wrapperHtml.matchAll(/["'](\.\.\/index\.html\?[^"']+)["']/g))
    .map(match => match[1]);
}

function queryParamsFromTarget(target) {
  return new URL(target, "https://example.invalid/evaluaties/").searchParams;
}

function expectQueryParam(params, name, expected, context) {
  expect(
    params.get(name) === String(expected),
    `${context} heeft ${name}=${params.get(name)}, verwacht ${expected}`
  );
}

function expectBooleanQueryParam(params, name, expected, context) {
  expectQueryParam(params, name, expected ? "1" : "0", context);
}

function readExerciseEntries(chapterPath) {
  const chapter = readJson(chapterPath);
  expect(Array.isArray(chapter.exercises), `chapter.json van ${chapterPath} bevat geen oefeningenarray.`);
  return chapter.exercises;
}

function validateReplacementRegex(testcase, context) {
  const replacements = Array.isArray(testcase.replacements) ? testcase.replacements : [];
  replacements.forEach((replacement, index) => {
    expect(!Object.prototype.hasOwnProperty.call(replacement, "from"), `${context} replacement ${index + 1} gebruikt nog "from" in plaats van "pattern".`);
    expect(typeof replacement.pattern === "string" && replacement.pattern.length > 0, `${context} replacement ${index + 1} mist pattern.`);
    expect(Object.prototype.hasOwnProperty.call(replacement, "to"), `${context} replacement ${index + 1} mist to.`);

    const flags = typeof replacement.flags === "string"
      ? replacement.flags
      : (replacement.replaceAll === false ? "" : "g");
    try {
      new RegExp(replacement.pattern, flags);
    } catch (error) {
      throw new Error(`${context} replacement ${index + 1} bevat een ongeldig regex-patroon: ${error.message}`);
    }
  });
}

function validateEvalRegex(testcase, context) {
  if (!testcase.eval || testcase.eval.type !== "regex") {
    return;
  }

  expect(typeof testcase.eval.pattern === "string" && testcase.eval.pattern.length > 0, `${context} regex-evaluatie mist pattern.`);
  try {
    new RegExp(testcase.eval.pattern, testcase.eval.flags || "i");
  } catch (error) {
    throw new Error(`${context} regex-evaluatie bevat een ongeldig regex-patroon: ${error.message}`);
  }
}

function main() {
  const manifest = readJson(ASSESSMENTS_PATH);
  const assessments = Array.isArray(manifest.assessments) ? manifest.assessments : [];
  expect(assessments.length > 0, "Geen assessments gevonden in evaluaties/assessments.json.");

  const seenLabels = new Set();

  assessments.forEach((assessment) => {
    expect(assessment.id, "Elk assessment moet een id hebben.");
    expect(assessment.launchFile, `${assessment.id} mist launchFile.`);
    expect(assessment.contentRoot, `${assessment.id} mist contentRoot.`);
    expect(Number.isInteger(assessment.exerciseCount) && assessment.exerciseCount > 0, `${assessment.id} mist een geldige exerciseCount.`);
    expect(!seenLabels.has(assessment.testLabel), `Dubbel testLabel: ${assessment.testLabel}`);
    seenLabels.add(assessment.testLabel);

    const wrapperPath = path.join(EVAL_DIR, assessment.launchFile);
    expect(fs.existsSync(wrapperPath), `Ontbrekend launch-bestand: ${assessment.launchFile}`);
    const wrapperHtml = fs.readFileSync(wrapperPath, "utf8");
    expect(
      wrapperHtml.includes(`assessment=${assessment.id}`),
      `${assessment.launchFile} verwijst niet naar assessment=${assessment.id}`
    );
    const targets = launcherTargets(wrapperHtml);
    expect(targets.length >= 2, `${assessment.launchFile} moet zowel een fallback-link als automatische redirect bevatten.`);
    targets.forEach((target, index) => {
      const context = `${assessment.launchFile} target ${index + 1}`;
      const params = queryParamsFromTarget(target);
      expectQueryParam(params, "assessment", assessment.id, context);
      expectQueryParam(params, "contentRoot", assessment.contentRoot, context);
      expectQueryParam(params, "testLabel", assessment.testLabel, context);
      expectQueryParam(params, "assignmentTextMode", assessment.assignmentTextMode, context);
      expectQueryParam(params, "contentCache", assessment.contentCache || "no-store", context);
      expectBooleanQueryParam(params, "testMode", !!assessment.testMode, context);
      expectBooleanQueryParam(params, "enableMenu", !!assessment.enableMenu, context);
      expectBooleanQueryParam(params, "revealExpected", !!assessment.revealExpectedOnFail, context);
    });

    const contentRoot = path.join(ROOT_DIR, assessment.contentRoot.replace(/^evaluaties[\\/]/, "evaluaties/"));
    const catalogPath = path.join(contentRoot, "catalog.json");
    expect(fs.existsSync(catalogPath), `Ontbrekende catalogus voor ${assessment.id}`);
    const catalog = readJson(catalogPath);
    expect(Array.isArray(catalog.chapters) && catalog.chapters.length === 1, `${assessment.id} moet exact een hoofdstuk hebben.`);

    const chapterEntry = catalog.chapters[0];
    expect(chapterEntry.id === assessment.chapterId, `${assessment.id} heeft een afwijkend chapterId in catalog.json.`);
    expect(chapterEntry.title === assessment.chapterTitle, `${assessment.id} heeft een afwijkende chapterTitle in catalog.json.`);

    const chapterPath = path.join(contentRoot, chapterEntry.path);
    expect(fs.existsSync(chapterPath), `Ontbrekende chapter.json voor ${assessment.id}`);
    const exerciseEntries = readExerciseEntries(chapterPath);
    expect(
      exerciseEntries.length === assessment.exerciseCount,
      `${assessment.id} chapter.json telt ${exerciseEntries.length} oefeningen, verwacht ${assessment.exerciseCount}`
    );

    exerciseEntries.forEach((exerciseEntry, index) => {
      const exerciseDir = path.join(path.dirname(chapterPath), exerciseEntry.path.replace(/[\\/]+exercise\.json$/i, ""));
      const exerciseJsonPath = path.join(exerciseDir, "exercise.json");
      const starterPath = path.join(exerciseDir, "starter.js");
      const testsPath = path.join(exerciseDir, "tests.json");

      expect(fs.existsSync(exerciseJsonPath), `Ontbrekende exercise.json voor ${assessment.id} oefening ${index + 1}`);
      expect(fs.existsSync(starterPath), `Ontbrekende starter.js voor ${assessment.id} oefening ${index + 1}`);
      expect(fs.existsSync(testsPath), `Ontbrekende tests.json voor ${assessment.id} oefening ${index + 1}`);

      const exerciseJson = readJson(exerciseJsonPath);
      const tests = readJson(testsPath);
      expect(exerciseJson.evaluationMode === "testcases", `${assessment.id} oefening ${index + 1} moet testcases gebruiken.`);
      expect(Array.isArray(tests) && tests.length === 1, `${assessment.id} oefening ${index + 1} moet exact een testcase hebben.`);
      expect(
        typeof tests[0].stdout === "string" || (tests[0].eval && typeof tests[0].eval === "object"),
        `${assessment.id} oefening ${index + 1} testcase mist stdout/eval`
      );
      tests.forEach((testcase, testcaseIndex) => {
        const context = `${assessment.id} oefening ${index + 1} testcase ${testcaseIndex + 1}`;
        validateReplacementRegex(testcase, context);
        validateEvalRegex(testcase, context);
      });
    });
  });

  console.log(`Validatie geslaagd voor ${assessments.length} evaluaties.`);
}

main();
