// JavaScript in de Klas - regressietests
// Copyright (c) 2026 Robbe Wulgaert
// Citeer/vermeld als: Robbe Wulgaert, AI in de Klas, robbewulgaert.be

const fs = require("fs");
const path = require("path");
const http = require("http");
const { pathToFileURL } = require("url");

function loadPlaywright() {
  const candidates = [
    process.env.PLAYWRIGHT_PATH,
    path.join(
      process.env.USERPROFILE || "",
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "node",
      "node_modules",
      "playwright"
    ),
    "playwright"
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      // Try the next location.
    }
  }

  throw new Error("Playwright kon niet geladen worden. Zet PLAYWRIGHT_PATH of gebruik de Codex-runtime.");
}

const { chromium } = loadPlaywright();

const ROOT_DIR = path.resolve(__dirname, "..");
const INDEX_FILE = path.join(ROOT_DIR, "index.html");

const EXPECTED_CHAPTER_ORDER = [
  "Hoofdstuk 1: Hello, World!",
  "Hoofdstuk 2: Datatypes en de Sequentie",
  "Hoofdstuk 3: De Selectie",
  "Hoofdstuk 4: Figuren Plotten",
  "Hoofdstuk 5: De Begrensde Herhaling",
  "Hoofdstuk 6: De Voorwaardelijke Herhaling",
  "Hoofdstuk 7: Figuren Plotten II"
];

const REGRESSION_CASES = [
  {
    chapterTitle: "Hoofdstuk 1: Hello, World!",
    exerciseTitle: "1. Hello, World!",
    code: 'console.log("Hello, World!")',
    expectStyleWarnings: true
  },
  {
    chapterTitle: "Hoofdstuk 1: Hello, World!",
    exerciseTitle: "7. Naam Plotten",
    code: [
      "showGrid();",
      "penUp();",
      "goTo(0, 120);",
      "var volledigeNaam = 'Ada Lovelace';",
      "console.log(volledigeNaam);",
      "writeText(volledigeNaam);"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 1: Hello, World!",
    exerciseTitle: "9. Scorebord",
    code: [
      "showGrid();",
      "penUp();",
      "var uitslag1 = '12/04 Gent 3-1 Brugge';",
      "var uitslag2 = '13/04 Antwerp 2-2 Genk';",
      "var uitslag3 = '14/04 Anderlecht 1-0 Standard';",
      "var uitslag4 = '15/04 Cercle 0-4 Union';",
      "goTo(-150, 150);",
      "writeText(uitslag1);",
      "goTo(150, 150);",
      "writeText(uitslag2);",
      "goTo(-150, -150);",
      "writeText(uitslag3);",
      "goTo(150, -150);",
      "writeText(uitslag4);"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 2: Datatypes en de Sequentie",
    exerciseTitle: "1. Defect Geldautomaat",
    code: [
      "var rekening = '500';",
      "var storting = '275';",
      "rekening = parseInt(rekening) + parseInt(storting);",
      "console.log('Uw nieuw saldo bedraagt ' + rekening + ' euro.');"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 2: Datatypes en de Sequentie",
    exerciseTitle: "1. Defect Geldautomaat",
    code: [
      "var rekening = 500;",
      "var storting = 275;",
      "var rekening = rekening + storting",
      "console.log('Uw nieuw saldo bedraagt ' + rekening + ' euro.');"
    ].join("\n"),
    expectStyleWarnings: true
  },
  {
    chapterTitle: "Hoofdstuk 2: Datatypes en de Sequentie",
    exerciseTitle: "2. Statiegeld",
    code: [
      "var cola = 3.5;",
      "var aantal = 4;",
      "var taks = (cola * aantal)/10;",
      "var totaal = cola*aantal+taks;",
      "console.log(\"Fred moet\", totaal, \"euro betalen\");"
    ].join("\n"),
    expectStyleWarnings: true
  },
  {
    chapterTitle: "Hoofdstuk 3: De Selectie",
    exerciseTitle: "9. Canvas: kleur kiezen op basis van temperatuur",
    code: [
      "var temp = 105;",
      "if(temp <= 0) {",
      "  setPenColour('blue');",
      "} else if(temp >= 100) {",
      "  setPenColour('red');",
      "} else {",
      "  setPenColour('green');",
      "}",
      "var kleur = '';",
      "if(temp <= 0) {",
      "  kleur = 'blue';",
      "} else if(temp >= 100) {",
      "  kleur = 'red';",
      "} else {",
      "  kleur = 'green';",
      "}",
      "console.log('Kleur ingesteld: ' + kleur + '.');",
      "moveForward(200);"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 4: Figuren Plotten",
    exerciseTitle: "8. Twee Figuren",
    code: [
      "showGrid(50);",
      "setPenColour('green');",
      "var zijde = 40;",
      "for(var i = 0; i < 4; i++) {",
      "  moveForward(zijde);",
      "  turnRight(90);",
      "}",
      "penUp();",
      "goTo(140, 0);",
      "penDown();",
      "setPenColour('orange');",
      "drawCircle(25);"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 4: Figuren Plotten",
    exerciseTitle: "13. Zijde Opvragen",
    code: [
      "showGrid(50);",
      "var zijde = parseInt(ask('Hoe lang is de zijde?'));",
      "for(var i = 0; i < 4; i++) {",
      "  moveForward(zijde);",
      "  turnRight(90);",
      "}"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 5: De Begrensde Herhaling",
    exerciseTitle: "1. Countdown naar Lancering",
    code: [
      "for(var teller = 10; teller >= 0; teller--){",
      "  console.log(teller);",
      "}",
      "console.log('LANCERING!');"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 6: De Voorwaardelijke Herhaling",
    exerciseTitle: "1. Countdown naar Lancering (while)",
    code: [
      "var teller = 10;",
      "while(teller >= 0) {",
      "  console.log(teller);",
      "  teller--;",
      "}",
      "console.log('LANCERING!');"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 7: Figuren Plotten II",
    exerciseTitle: "7. Vierkanten in diverse kleuren",
    code: [
      "showGrid(50);",
      "penUp();",
      "for(var i = 0; i < 3; i++) {",
      "  goTo(i * 70, 0);",
      "  penDown();",
      "  if(i === 0) {",
      "    setPenColour('red');",
      "  } else if(i === 1) {",
      "    setPenColour('green');",
      "  } else {",
      "    setPenColour('blue');",
      "  }",
      "  for(var zijde = 0; zijde < 4; zijde++) {",
      "    moveForward(40);",
      "    turnRight(90);",
      "  }",
      "  penUp();",
      "}"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 7: Figuren Plotten II",
    exerciseTitle: "11. Lijnkleur kiezen in een lus",
    code: [
      "showGrid(50);",
      "penUp();",
      "for(var i = 0; i < 4; i++) {",
      "  goTo(i * 60, 0);",
      "  var lijnkleur = i % 2 === 0 ? 'red' : 'blue';",
      "  setPenColour(lijnkleur);",
      "  if(lijnkleur === 'red') {",
      "    setLineWidth(5);",
      "  } else {",
      "    setLineWidth(2);",
      "  }",
      "  penDown();",
      "  for(var zijde = 0; zijde < 4; zijde++) {",
      "    moveForward(30);",
      "    turnRight(90);",
      "  }",
      "  penUp();",
      "}"
    ].join("\n")
  },
  {
    chapterTitle: "Hoofdstuk 7: Figuren Plotten II",
    exerciseTitle: "14. Random Gevulde Cirkel",
    code: [
      "showGrid(50);",
      "penUp();",
      "for(var i = 0; i < 3; i++) {",
      "  goTo(-120 + (i * 120), 0);",
      "  penDown();",
      "  setPenColour(randomColour());",
      "  fillCircle(20);",
      "  penUp();",
      "}"
    ].join("\n")
  }
];

function createStaticServer(rootDir) {
  return http.createServer((request, response) => {
    const requestUrl = new URL(request.url || "/", "http://127.0.0.1");
    let relativePath = decodeURIComponent(requestUrl.pathname || "/");
    if (relativePath === "/") {
      relativePath = "/index.html";
    }

    const resolvedPath = path.resolve(rootDir, `.${relativePath}`);
    if (!resolvedPath.startsWith(rootDir)) {
      response.writeHead(403);
      response.end("Forbidden");
      return;
    }

    fs.readFile(resolvedPath, (error, data) => {
      if (error) {
        response.writeHead(404);
        response.end("Not found");
        return;
      }

      const extension = path.extname(resolvedPath).toLowerCase();
      const contentTypes = {
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".svg": "image/svg+xml"
      };

      response.writeHead(200, {
        "Content-Type": contentTypes[extension] || "application/octet-stream"
      });
      response.end(data);
    });
  });
}

function installCodeMirrorStub(page) {
  return page.addInitScript(() => {
    window.CodeMirror = function(element, options = {}) {
      let value = String(options.value || "");
      const listeners = { change: [] };

      const api = {
        getValue() {
          return value;
        },
        setValue(nextValue) {
          value = String(nextValue || "");
          (listeners.change || []).forEach(listener => listener(api));
        },
        on(eventName, listener) {
          if (!listeners[eventName]) {
            listeners[eventName] = [];
          }
          listeners[eventName].push(listener);
        },
        focus() {},
        refresh() {}
      };

      if (element) {
        element.textContent = "";
      }

      return api;
    };
  });
}

async function launchBrowser() {
  try {
    return await chromium.launch({ headless: true });
  } catch (error) {
    const message = String(error && error.message ? error.message : error);
    if (!/Executable doesn't exist/i.test(message)) {
      throw error;
    }

    const fallbackExecutables = [
      "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    ];

    for (const executablePath of fallbackExecutables) {
      if (fs.existsSync(executablePath)) {
        return chromium.launch({
          executablePath,
          headless: true
        });
      }
    }

    throw error;
  }
}

async function runRegressionCase(page, testCase) {
  return page.evaluate(async ({ chapterTitle, exerciseTitle, code }) => {
    const chaptersRef = eval("chapters");
    const chapterIndex = chaptersRef.findIndex(chapter => chapter.title === chapterTitle);
    if (chapterIndex < 0) {
      throw new Error(`Hoofdstuk niet gevonden: ${chapterTitle}`);
    }

    const exerciseIndex = chaptersRef[chapterIndex].exercises.findIndex(exercise => exercise.title === exerciseTitle);
    if (exerciseIndex < 0) {
      throw new Error(`Oefening niet gevonden: ${exerciseTitle}`);
    }

    localStorage.clear();
    eval(`currentChapterIdx = ${chapterIndex}`);
    eval(`currentExerciseIdx = ${exerciseIndex}`);
    renderChapterMenu();
    renderExerciseProgress();
    loadExercise();

    const editorInstance = eval("editor");
    editorInstance.setValue(code);
    eval("isDirty = false");

    const result = await evaluateExercise(code, "", "");
    return JSON.parse(JSON.stringify(result));
  }, testCase);
}

async function main() {
  const server = createStaticServer(ROOT_DIR);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}/index.html`;

  const browser = await launchBrowser();
  const page = await browser.newPage();

  const pageErrors = [];
  page.on("pageerror", error => {
    pageErrors.push(String(error && error.stack ? error.stack : error));
  });

  try {
    await installCodeMirrorStub(page);
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() =>
      typeof loadExercise === "function" &&
      typeof evaluateExercise === "function" &&
      Array.isArray(eval("chapters")) &&
      eval("chapters").length > 0 &&
      window.JSIK_COURSE_CONTENT_SOURCE !== "not-loaded"
    );

    const chapterOrder = await page.evaluate(() => eval("chapters").map(chapter => chapter.title));
    if (chapterOrder.join(" | ") !== EXPECTED_CHAPTER_ORDER.join(" | ")) {
      throw new Error(`Onverwachte hoofdstukvolgorde: ${chapterOrder.join(" | ")}`);
    }

    const contentSource = await page.evaluate(() => window.JSIK_COURSE_CONTENT_SOURCE);
    if (contentSource !== "source-files") {
      throw new Error(`Onverwachte contentbron: ${contentSource}`);
    }

    const results = [];
    for (const testCase of REGRESSION_CASES) {
      const result = await runRegressionCase(page, testCase);
      const expectedSuccess = testCase.expectSuccess !== false;
      const hasStyleWarnings = Array.isArray(result.styleWarnings) && result.styleWarnings.length > 0;
      results.push({
        chapterTitle: testCase.chapterTitle,
        exerciseTitle: testCase.exerciseTitle,
        success: !!result.success,
        expectedSuccess,
        successMatchesExpectation: !!result.success === expectedSuccess,
        total: Number.isFinite(result.total) ? result.total : 0,
        failedCount: Number.isFinite(result.failedCount) ? result.failedCount : 0,
        styleWarnings: hasStyleWarnings ? result.styleWarnings.length : 0,
        styleWarningMismatch: !!testCase.expectStyleWarnings !== hasStyleWarnings,
        firstFailInfo: result.firstFailCase && result.firstFailCase.info ? result.firstFailCase.info : "",
        runtimeError: result.errorMessage || ""
      });
    }

    const failedCases = results.filter(result => !result.successMatchesExpectation || result.styleWarningMismatch);
    results.forEach(result => {
      const prefix = result.successMatchesExpectation && !result.styleWarningMismatch ? "[OK]" : "[FAIL]";
      const successSuffix = result.expectedSuccess
        ? `${result.total} testcase(s)`
        : `verwacht afgewezen (${result.failedCount} mislukte testcase(s))`;
      const failureSuffix = result.expectedSuccess
        ? `${result.failedCount} mislukte testcase(s)`
        : "onverwacht geslaagd";
      const suffix = result.successMatchesExpectation && !result.styleWarningMismatch
        ? `${successSuffix}${result.styleWarnings ? `, ${result.styleWarnings} stijlmelding(en)` : ""}`
        : `${failureSuffix}${result.styleWarningMismatch ? " - stijlcheck kwam niet overeen met verwachting" : ""}${result.firstFailInfo ? ` - ${result.firstFailInfo}` : ""}${result.runtimeError ? ` - ${result.runtimeError}` : ""}`;
      console.log(`${prefix} ${result.chapterTitle} / ${result.exerciseTitle}: ${suffix}`);
    });

    if (pageErrors.length > 0) {
      console.log("");
      console.log("Paginafouten tijdens regressie:");
      pageErrors.forEach(message => console.log(`- ${message}`));
    }

    if (failedCases.length > 0 || pageErrors.length > 0) {
      process.exitCode = 1;
    } else {
      console.log("");
      console.log(`Alle ${results.length} regressiecases hebben het verwachte resultaat.`);
    }
  } finally {
    await page.close();
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});
