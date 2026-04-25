// JavaScript in de Klas - evaluatieregressietests
// Copyright (c) 2026 Robbe Wulgaert
// Citeer/vermeld als: Robbe Wulgaert, AI in de Klas, robbewulgaert.be

const fs = require("fs");
const path = require("path");
const http = require("http");

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
    "playwright",
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
const EVAL_DIR = path.join(ROOT_DIR, "evaluaties");
const ASSESSMENTS = JSON.parse(fs.readFileSync(path.join(EVAL_DIR, "assessments.json"), "utf8")).assessments || [];

function createStaticServer(rootDir) {
  return http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    const relPath = decodeURIComponent(url.pathname).replace(/^\/+/, "") || "index.html";
    const filePath = path.resolve(rootDir, relPath);

    if (!filePath.startsWith(rootDir)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.readFile(filePath, (error, data) => {
      if (error) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }

      const typeByExt = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".png": "image/png",
      };

      res.writeHead(200, {
        "content-type": typeByExt[path.extname(filePath)] || "application/octet-stream",
      });
      res.end(data);
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
        refresh() {},
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
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ];

    for (const executablePath of fallbackExecutables) {
      if (fs.existsSync(executablePath)) {
        return chromium.launch({
          executablePath,
          headless: true,
        });
      }
    }

    throw error;
  }
}

async function inspectAssessment(page, baseUrl, assessment) {
  await page.goto(`${baseUrl}/evaluaties/${assessment.launchFile}`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(url => url.toString().includes(`/index.html?assessment=${assessment.id}`), { timeout: 30000 });
  let readySnapshot = null;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    readySnapshot = await page.evaluate(() => ({
      assessmentId: String(window.JSIK_ACTIVE_ASSESSMENT_ID || ""),
      courseSource: String(window.JSIK_COURSE_CONTENT_SOURCE || ""),
      hasLoadExercise: typeof loadExercise === "function",
      hasEvaluateExercise: typeof evaluateExercise === "function",
      hasStructuredReveal: typeof structuredShouldRevealEvaluationDetails === "function",
      chaptersLength: Array.isArray(eval("chapters")) ? eval("chapters").length : 0,
    }));

    if (
      readySnapshot.assessmentId === assessment.id &&
      readySnapshot.courseSource === "source-files" &&
      readySnapshot.hasLoadExercise &&
      readySnapshot.hasEvaluateExercise &&
      readySnapshot.hasStructuredReveal &&
      readySnapshot.chaptersLength > 0
    ) {
      break;
    }

    await page.waitForTimeout(500);
  }

  const ready =
    readySnapshot &&
    readySnapshot.assessmentId === assessment.id &&
    readySnapshot.courseSource === "source-files" &&
    readySnapshot.hasLoadExercise &&
    readySnapshot.hasEvaluateExercise &&
    readySnapshot.hasStructuredReveal &&
    readySnapshot.chaptersLength > 0;

  if (!ready) {
    return {
      id: assessment.id,
      title: assessment.title,
      exerciseCount: 0,
      issues: [
        `page did not finish booting correctly (${JSON.stringify(readySnapshot)})`,
      ],
    };
  }

  const snapshot = await page.evaluate(async () => {
    localStorage.clear();
    eval("currentChapterIdx = 0");
    eval("currentExerciseIdx = 0");
    renderChapterMenu();
    renderExerciseProgress();
    loadExercise();

    const wrongCode = 'console.log("fout")';
    eval("editor").setValue(wrongCode);
    eval("isDirty = false");

    const evalResult = await evaluateExercise(wrongCode, "", "");
    openStructuredEvaluationModal(evalResult, eval("chapters")[0].exercises[0].title);

    return {
      assessmentId: String(window.JSIK_ACTIVE_ASSESSMENT_ID || ""),
      assessmentTitle: String(window.JSIK_ACTIVE_ASSESSMENT_TITLE || ""),
      contentRoot: String(window.JSIK_CONTENT_ROOT || ""),
      courseSource: String(window.JSIK_COURSE_CONTENT_SOURCE || ""),
      chapterCount: eval("chapters").length,
      exerciseCount: eval("chapters")[0].exercises.length,
      revealDetails: structuredShouldRevealEvaluationDetails(),
      menuTabDisplay: getComputedStyle(document.getElementById("menu-tab")).display,
      assignmentText: (document.getElementById("opdracht-tekst").textContent || "").trim(),
      assignmentVisible: getComputedStyle(document.getElementById("opdracht-tekst")).display !== "none",
      title: document.title,
      success: !!evalResult.success,
      failedCount: evalResult.failedCount,
      modalDisplay: getComputedStyle(document.getElementById("eval-modal")).display,
      modalText: (document.getElementById("eval-modal-cases").textContent || "").trim(),
    };
  });

  const issues = [];
  if (snapshot.assessmentId !== assessment.id) {
    issues.push(`assessment-id mismatch (${snapshot.assessmentId})`);
  }
  if (snapshot.courseSource !== "source-files") {
    issues.push(`unexpected content source (${snapshot.courseSource})`);
  }
  if (snapshot.chapterCount !== 1) {
    issues.push(`expected 1 chapter, got ${snapshot.chapterCount}`);
  }
  if (snapshot.exerciseCount !== assessment.exerciseCount) {
    issues.push(`expected ${assessment.exerciseCount} exercises, got ${snapshot.exerciseCount}`);
  }
  if (snapshot.menuTabDisplay !== "none") {
    issues.push(`menu tab display is ${snapshot.menuTabDisplay}`);
  }
  if (snapshot.revealDetails !== false) {
    issues.push("revealDetails should be false in toetsmodus");
  }
  if (snapshot.success !== false || snapshot.failedCount < 1) {
    issues.push("failing smoke testcase did not fail as expected");
  }
  if (snapshot.modalDisplay === "none") {
    issues.push("evaluation modal did not open");
  }
  if (snapshot.modalText.includes("Verwachte uitvoer") || snapshot.modalText.includes("Jouw uitvoer") || snapshot.modalText.includes("Invoer")) {
    issues.push("modal leaked detailed testcase fields");
  }

  if (assessment.assignmentTextMode === "comment" && snapshot.assignmentText.length === 0) {
    issues.push("assignment text should be preserved from starter comments");
  }
  if (assessment.assignmentTextMode === "empty" && snapshot.assignmentText.length !== 0) {
    issues.push("assignment text should be empty");
  }
  if (snapshot.assignmentVisible) {
    issues.push("assignment text should stay hidden in the topbar");
  }

  return {
    id: assessment.id,
    title: snapshot.title,
    exerciseCount: snapshot.exerciseCount,
    issues,
  };
}

async function main() {
  const server = createStaticServer(ROOT_DIR);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;

  const browser = await launchBrowser();
  const page = await browser.newPage();
  const pageErrors = [];

  page.on("pageerror", error => {
    pageErrors.push(String(error && error.stack ? error.stack : error));
  });

  try {
    await installCodeMirrorStub(page);
    const results = [];
    for (const assessment of ASSESSMENTS) {
      results.push(await inspectAssessment(page, baseUrl, assessment));
    }

    results.forEach((result) => {
      if (result.issues.length === 0) {
        console.log(`[OK] ${result.id}: ${result.exerciseCount} oefeningen`);
      } else {
        console.log(`[FAIL] ${result.id}: ${result.issues.join(" | ")}`);
      }
    });

    if (pageErrors.length > 0) {
      console.log("");
      console.log("Paginafouten tijdens evaluatie-regressie:");
      pageErrors.forEach(message => console.log(`- ${message}`));
    }

    if (results.some(result => result.issues.length > 0) || pageErrors.length > 0) {
      process.exitCode = 1;
    } else {
      console.log("");
      console.log(`Alle ${results.length} evaluaties zijn geslaagd.`);
    }
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});
