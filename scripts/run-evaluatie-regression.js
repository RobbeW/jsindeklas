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

    const allowedFiles = new Set(["platform.html", "workspace.css", "favicon.png", "rgbcolor.js", "library.js"]);
    const allowed = allowedFiles.has(relPath) || /^evaluaties\/(?:[a-z0-9_]+\.html|launcher\.css|timed\.css|timed-attempt\.js|assessments\.json|content\/(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+\.(?:json|js))$/.test(relPath) || /^content\/(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+\.(?:json|js)$/.test(relPath);
    if (!allowed || !filePath.startsWith(rootDir + path.sep)) {
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
        setOption() {},
        getOption() {},
        getWrapperElement() { return element; },
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

async function configurePage(page, baseUrl) {
  await installCodeMirrorStub(page);
  await page.route("**/*", async route => {
    const url = route.request().url();
    if (url.startsWith(baseUrl + "/")) return route.continue();
    if (/jspdf[^/]*\.umd(?:\.min)?\.js(?:\?|$)/i.test(url)) {
      if (process.env.JSIK_JSPDF_PATH) return route.fulfill({ path: process.env.JSIK_JSPDF_PATH, contentType: "text/javascript" });
      return route.fulfill({ contentType: "text/javascript", body: "window.jspdf = { jsPDF: function jsPDF() {} };" });
    }
    return route.abort();
  });
}

async function startAssessment(page) {
  await page.locator("#timed-start[open]").waitFor({ state: "visible", timeout: 30000 });
  await page.getByLabel("Voornaam", { exact: true }).fill("Zoë");
  await page.getByLabel("Achternaam", { exact: true }).fill("Van den Berg");
  await page.getByLabel("Klas", { exact: true }).fill("2A");
  await page.locator("#timed-start-button").click();
  await page.locator("#timed-start").waitFor({ state: "hidden", timeout: 30000 });
}

async function checkFallbacks(browser, baseUrl) {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    await context.route("**/*", route => route.request().url().startsWith(baseUrl + "/")
      ? route.continue() : route.abort());
    const page = await context.newPage();
    for (const assessment of ASSESSMENTS) {
      await page.goto(`${baseUrl}/evaluaties/${assessment.launchFile}`);
      const href = await page.locator("main a").getAttribute("href");
      const target = new URL(href, page.url());
      if (target.pathname !== "/platform.html" || target.searchParams.get("assessment") !== assessment.id || target.searchParams.get("assessmentTitle") !== assessment.title) {
        throw new Error(`Fallback van ${assessment.id} verwijst onjuist: ${href}`);
      }
      await page.locator("main a").click();
      if (new URL(page.url()).pathname !== "/platform.html") throw new Error(`Fallback van ${assessment.id} opent de editor niet.`);
    }
    console.log(`[OK] ${ASSESSMENTS.length} fallback-links`);
  } finally { await context.close(); }
}

function assert(condition, message) { if (!condition) throw new Error(message); }

async function withSyntheticPage(browser, baseUrl, callback, options = {}) {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  try {
    const page = await context.newPage();
    await configurePage(page, baseUrl);
    await page.clock.setFixedTime(new Date("2026-01-01T12:00:00Z"));
    if (options.duration) {
      await page.route("**/evaluaties/assessments.json", route => {
        const manifest = JSON.parse(fs.readFileSync(path.join(EVAL_DIR, "assessments.json"), "utf8"));
        manifest.assessments.find(item => item.id === options.id).durationMinutes = options.duration;
        return route.fulfill({ json: manifest });
      });
    }
    await callback(page, context);
  } finally { await context.close(); }
}

async function launchTimed(page, baseUrl, assessment) {
  await page.goto(`${baseUrl}/evaluaties/${assessment.launchFile}`);
  await page.waitForURL(url => url.pathname === "/platform.html");
  await startAssessment(page);
  await page.locator("#timed-controls").waitFor({ state: "visible" });
}

async function checkLifecycle(browser, baseUrl) {
  const test = ASSESSMENTS.find(item => item.kind === "test");
  const exam = ASSESSMENTS.find(item => item.kind === "exam");
  for (const [assessment, duration] of [[test, test.durationMinutes], [exam, exam.durationMinutes], [test, 2]]) {
    await withSyntheticPage(browser, baseUrl, async (page, context) => {
      await launchTimed(page, baseUrl, assessment);
      const key = `jsik-attempt:${assessment.id}:${assessment.contentRevision}`;
      const state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), key);
      assert(state.deadline - state.startedAt === duration * 60000, `Duur onjuist voor ${assessment.id}: ${duration}`);
      assert(await page.locator("#timed-clock-value").textContent() === `${duration}:00`, "Begintijd klopt niet");
      if (duration !== 2) return;
      await page.evaluate(() => eval("editor").setValue('console.log("synthetisch")'));
      const before = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), key);
      assert(Object.values(before.drafts).includes('console.log("synthetisch")'), "Concept niet opgeslagen");
      const other = await context.newPage();
      await configurePage(other, baseUrl);
      await other.goto(`${baseUrl}/evaluaties/${assessment.launchFile}`);
      await other.locator("#timed-retry").waitFor({ state: "visible" });
      assert(await other.locator("#timed-start-button").isDisabled(), "Tweede tabblad kreeg toegang");
      await other.close();
      await page.reload();
      await page.locator("#timed-start").waitFor({ state: "hidden" });
      await page.waitForFunction(() => typeof editor !== "undefined" && editor && editor.getValue().includes("synthetisch"));
      const resumed = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), key);
      assert(resumed.deadline === before.deadline && resumed.attemptId === before.attemptId, "Herladen wijzigde poging of deadline");
      await page.clock.setFixedTime(new Date(state.startedAt + duration * 60000 * .80));
      await page.evaluate(() => window.dispatchEvent(new Event("focus")));
      assert(await page.locator("#timed-clock").getAttribute("data-urgency") === "20", "20%-waarschuwing ontbreekt");
      assert(await page.locator("#timed-announcement").textContent() === "Nog 0:24.", "Waarschuwing is niet aangekondigd");
      assert(!await page.locator("#timed-nudge").isVisible(), "Nudge verscheen al op 20%");
      await page.clock.setFixedTime(new Date(state.startedAt + duration * 60000 * .90));
      await page.evaluate(() => window.dispatchEvent(new Event("focus")));
      await page.locator("#timed-nudge").waitFor({ state: "visible" });
      assert(await page.locator("#timed-clock").getAttribute("data-urgency") === "10", "10%-waarschuwing ontbreekt");
      assert(!await page.locator("#timed-clock").evaluate(el => el.classList.contains("is-pulsing")), "Reduced motion pulseert");
      await page.locator("#timed-submit").focus();
      await page.clock.setFixedTime(new Date(state.startedAt + duration * 60000 * .95));
      await page.evaluate(() => window.dispatchEvent(new Event("focus")));
      assert(await page.locator("#timed-clock").getAttribute("data-urgency") === "5", "5%-waarschuwing ontbreekt");
      assert(await page.locator("#timed-submit").evaluate(el => document.activeElement === el), "Waarschuwing stal focus");
      await page.evaluate(() => {
        window.runStudentCode = () => new Promise(resolve => { window.finishExpiryRun = resolve; });
        const originalClick = HTMLAnchorElement.prototype.click;
        window.blockDownload = true;
        HTMLAnchorElement.prototype.click = function () {
          if (this.download && window.blockDownload) {
            window.attemptedFilename = this.download;
            return;
          }
          originalClick.call(this);
        };
      });
      await page.locator("#run-code").click();
      await page.waitForFunction(() => typeof window.finishExpiryRun === "function");
      await page.clock.setFixedTime(new Date(state.deadline));
      await page.evaluate(() => window.dispatchEvent(new Event("focus")));
      await page.locator("#timed-complete[open]").waitFor({ state: "visible" });
      assert((await page.locator("#timed-complete-title").textContent()).includes("Tijd is om"), "Eindscherm ontbreekt");
      assert(await page.locator("#timed-download").isVisible(), "Herstelknop download ontbreekt");
      const final = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), key);
      assert(final.final && final.final.reason === "expiry", "Verlopen poging niet vastgezet");
      assert(final.final.records[0].interrupted && await page.locator("#timed-interrupted").isVisible(),
        "Onderbroken uitvoering niet gemeld");
      await page.evaluate(() => { window.finishExpiryRun(); });
      await page.waitForFunction(() => !timedRunInFlight);
      if (process.env.JSIK_JSPDF_PATH) {
        const expectedFilename = "Zoë_Van_den_Berg_2A_2026-01-01_Toets_1.pdf";
        assert(await page.evaluate(() => window.attemptedFilename) === expectedFilename, "Automatische PDF-bestandsnaam onjuist");
        await page.evaluate(() => { window.blockDownload = false; });
        const firstDownload = page.waitForEvent("download");
        await page.locator("#timed-download").click();
        const first = await firstDownload;
        assert(first.suggestedFilename() === expectedFilename, "Handmatige PDF-bestandsnaam onjuist");
        const original = fs.readFileSync(await first.path());
        await page.evaluate(key => {
          const legacy = JSON.parse(localStorage.getItem(key));
          delete legacy.firstName;
          delete legacy.lastName;
          delete legacy.final.dateKey;
          localStorage.setItem(key, JSON.stringify(legacy));
        }, key);
        await page.addInitScript(() => {
          Storage.prototype.setItem = () => { throw new Error("synthetische opslagfout"); };
        });
        await page.reload();
        await page.locator("#timed-complete[open]").waitFor({ state: "visible" });
        const repeatDownload = page.waitForEvent("download");
        await page.locator("#timed-download").click();
        const repeat = await repeatDownload;
        assert(repeat.suggestedFilename() === expectedFilename, "Opgeslagen poging heeft een afwijkende PDF-bestandsnaam");
        const recovered = fs.readFileSync(await repeat.path());
        assert(original.subarray(0, 5).toString() === "%PDF-" && recovered.equals(original), "PDF-herstel wijkt af van de eerste download");
      }
    }, { id: assessment.id, duration: duration === 2 ? 2 : undefined });
  }
  await withSyntheticPage(browser, baseUrl, async page => {
    await launchTimed(page, baseUrl, test);
    const key = `jsik-attempt:${test.id}:${test.contentRevision}`;
    await page.evaluate(() => eval("editor").setValue("eerste concept"));
    await page.locator(".exercise-btn").nth(1).click();
    await page.evaluate(() => eval("editor").setValue("tweede concept"));
    await page.locator(".exercise-btn").nth(0).click();
    await page.evaluate(() => {
      window.originalStorageSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function () { throw new Error("synthetische opslagfout"); };
      eval("editor").setValue("niet opgeslagen concept");
    });
    await page.locator(".exercise-btn").nth(1).click();
    assert(await page.locator(".exercise-btn").nth(0).evaluate(el => el.classList.contains("current")), "Navigatie ging door na opslagfout");
    assert((await page.locator("#timed-save-status").textContent()).includes("niet gelukt"), "Opslagfout niet gemeld");
    await page.evaluate(() => { Storage.prototype.setItem = window.originalStorageSetItem; });
    await page.locator(".exercise-btn").nth(1).click();
    await page.locator(".exercise-btn").nth(0).click();
    await page.locator("#timed-restart").click();
    await page.locator("#timed-confirm-restart").click();
    const state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), key);
    assert(!Object.values(state.drafts).includes("niet opgeslagen concept") && Object.values(state.drafts).includes("tweede concept"), "Herstart wijzigde de verkeerde concepten");
  });
  console.log("[OK] opslagfout en herstart van één oefening");
  await withSyntheticPage(browser, baseUrl, async page => {
    let calls = 0;
    await page.route("**/jspdf.umd.min.js", route => {
      calls += 1;
      if (calls === 1) return route.abort();
      return route.fulfill({ contentType: "text/javascript", body: "window.jspdf = { jsPDF: function jsPDF() {} };" });
    });
    await page.goto(`${baseUrl}/evaluaties/${test.launchFile}`);
    await page.locator("#timed-retry").waitFor({ state: "visible" });
    assert(await page.locator("#timed-start-button").isDisabled(), "Start niet geblokkeerd na CDN-fout");
    await page.locator("#timed-retry").click();
    await page.waitForFunction(() => !document.getElementById("timed-start-button").disabled);
    assert(calls === 2, "PDF-bibliotheek niet opnieuw geladen");
  });
  console.log("[OK] PDF-bibliotheek opnieuw laden vóór start");
  await withSyntheticPage(browser, baseUrl, async page => {
    await launchTimed(page, baseUrl, test);
    const key = `jsik-attempt:${test.id}:${test.contentRevision}`;
    await page.evaluate(() => {
      const original = window.runStudentCode;
      let first = true;
      window.runStudentCode = async (...args) => {
        if (first) { first = false; await new Promise(resolve => { window.releaseSyntheticRun = resolve; }); }
        return original(...args);
      };
      eval("editor").setValue('console.log("eerste versie")');
    });
    await page.locator("#run-code").click();
    await page.waitForFunction(() => typeof window.releaseSyntheticRun === "function");
    assert(await page.locator(".exercise-btn").nth(1).isDisabled(), "Navigatie tijdens uitvoering niet geblokkeerd");
    assert(await page.locator("#timed-submit").isDisabled(), "Vroeg indienen tijdens uitvoering niet geblokkeerd");
    await page.evaluate(() => { eval("editor").setValue('console.log("latere versie")'); window.releaseSyntheticRun(); });
    await page.locator("#eval-modal-primary").waitFor({ state: "visible" });
    await page.locator("#eval-modal-primary").click();
    await page.waitForFunction(() => !document.getElementById("run-code").disabled);
    await page.locator("#timed-submit").click();
    await page.locator("#timed-review[open]").waitFor({ state: "visible" });
    await page.locator("#timed-confirm-submit").click();
    await page.locator("#timed-complete[open]").waitFor({ state: "visible" });
    const final = await page.evaluate(key => JSON.parse(localStorage.getItem(key)).final, key);
    assert(final.reason === "manual", "Vroeg indienen niet opgeslagen");
    const record = final.records[0];
    assert(record.code === 'console.log("latere versie")' && record.runCode === 'console.log("eerste versie")' && record.outputFromEarlierCode, "Uitvoering en laatste concept niet afzonderlijk vastgezet");
  });
  console.log("[OK] vertraagde uitvoering en vroeg indienen");
  await withSyntheticPage(browser, baseUrl, async page => {
    await launchTimed(page, baseUrl, test);
    const runCorrectExercise = async () => {
      await page.evaluate(() => {
        const expected = chapters[currentChapterIdx].exercises[currentExerciseIdx].tests[0].stdout;
        editor.setValue(`console.log(${JSON.stringify(expected)});`);
      });
      await page.locator("#run-code").click();
      await page.locator("#eval-modal-pill.ok").waitFor({ state: "visible" });
    };
    const deadline = await page.evaluate(() => timedState.deadline);
    await runCorrectExercise();
    const next = page.getByRole("button", { name: "Volgende oefening" });
    assert(await next.evaluate(el => document.activeElement === el), "Volgende oefening krijgt geen toetsenbordfocus");
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => currentExerciseIdx === 1);
    assert(await page.evaluate(() => timedState.deadline) === deadline, "Volgende oefening wijzigt de deadline");

    await page.locator(".exercise-btn").last().click();
    await runCorrectExercise();
    assert(!await next.isVisible(), "Laatste oefening heeft een knop voor de volgende oefening");
    assert(await page.locator("#eval-modal-primary").textContent() === "Sluiten", "Laatste oefening mist Sluiten");
    await page.keyboard.press("Escape");
    await page.locator("#eval-modal").waitFor({ state: "hidden" });
  });
  console.log("[OK] volgende oefening na een geslaagde uitvoering");
  console.log("[OK] tijdslimieten, herladen, tweede tabblad en vervallen");
}

async function checkPracticeMode(browser, baseUrl) {
  await withSyntheticPage(browser, baseUrl, async page => {
    await page.goto(`${baseUrl}/platform.html`);
    await page.waitForFunction(() => document.getElementById("course-loading").classList.contains("is-hidden"));
    assert(await page.locator("#export-pdf").isVisible(), "Oefenmodus mist PDF-reeks");
    assert(!await page.locator("#timed-controls").isVisible(), "Oefenmodus toont een evaluatieklok");
    const consoleTab = page.getByRole("tab", { name: "Console-uitvoer" });
    const canvasTab = page.getByRole("tab", { name: "Canvas" });
    assert(await consoleTab.getAttribute("aria-selected") === "true", "Oefenmodus start niet op de console");
    assert(await page.locator("#canvas-pane #console-output").isVisible(), "Oefenmodus mist de gedeelde console");
    await page.locator("#export-pdf").click();
    assert(await page.locator("#pdf-modal").isVisible(), "Oefenmodus opent de bestaande exportdialoog niet");
    await page.locator("#close-pdf-modal").click();

    await page.locator(".tour-start-button").click();
    for (let step = 0; step < 5; step += 1) await page.getByRole("button", { name: "Volgende", exact: true }).click();
    assert(await canvasTab.getAttribute("aria-selected") === "true", "Rondleiding opent het canvas niet");
    await page.getByRole("button", { name: "Overslaan", exact: true }).click();
    assert(await consoleTab.getAttribute("aria-selected") === "true", "Rondleiding herstelt het uitvoertabblad niet");

    await page.evaluate(() => {
      isDirty = false;
      switchChapter(chapters.findIndex(chapter => chapter.id === "ch01"));
      const expected = chapters[currentChapterIdx].exercises[0].tests[0].stdout;
      editor.setValue(`console.log(${JSON.stringify(expected)});`);
      window.originalSyntheticRun = window.runStudentCode;
      window.runStudentCode = (code, options) => {
        if (options?.captureGlobal === false) moveForward(10);
        return window.originalSyntheticRun(code, options);
      };
    });
    await page.locator("#run-code").click();
    await page.locator("#eval-modal-pill.ok").waitFor({ state: "visible" });
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => !document.getElementById("run-code").disabled);
    assert(!await canvasTab.evaluate(tab => tab.classList.contains("has-canvas-output")),
      "Consolecode signaleert canvasgebruik uit een verborgen test");

    await page.evaluate(() => {
      window.runStudentCode = window.originalSyntheticRun;
      editor.setValue(editor.getValue() + "\nmoveForward(80);");
    });
    await page.locator("#run-code").click();
    await page.locator("#eval-modal-pill.ok").waitFor({ state: "visible" });
    await page.locator("#eval-modal-primary").click();
    assert(await canvasTab.evaluate(tab => tab.classList.contains("has-canvas-output")), "Canvasuitvoer mist de statische markering");
    assert(await canvasTab.evaluate(tab => getComputedStyle(tab).animationName) === "none", "Canvas pulseert bij beperkte beweging");
    if (process.env.JSIK_JSPDF_PATH) {
      await page.locator("#modal-naam").fill("Demo Leerling");
      await page.locator("#modal-klas").fill("TEST");
      const download = page.waitForEvent("download");
      await page.locator("#modal-ok").click();
      const pdf = fs.readFileSync(await (await download).path());
      assert(pdf.includes(Buffer.from("/Subtype /Image")), "Oefen-PDF mist de tekening van het verborgen canvas");
    }
  });
  console.log("[OK] gedeelde oefenmodus, rondleiding, canvassignaal en PDF-export");
}

async function checkTimedWorkspace(browser, baseUrl) {
  await withSyntheticPage(browser, baseUrl, async page => {
    await page.setViewportSize({ width: 1366, height: 820 });
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await launchTimed(page, baseUrl, ASSESSMENTS[0]);
    const editorPane = page.locator("#editor-pane");
    const outputPane = page.locator("#canvas-pane");
    const splitter = page.getByRole("separator", { name: "Verdeling werkruimte" });
    const consoleTab = page.getByRole("tab", { name: "Console-uitvoer" });
    const canvasTab = page.getByRole("tab", { name: "Canvas" });
    const turtleCanvas = page.locator("#turtlecanvas");
    const noPageScroll = () => page.evaluate(() => document.scrollingElement.scrollHeight <= innerHeight);

    assert(await consoleTab.getAttribute("aria-selected") === "true", "Console is niet standaard actief");
    assert(!await turtleCanvas.isVisible(), "Canvas neemt ruimte in bij de consoletab");
    const left = await editorPane.boundingBox();
    const right = await outputPane.boundingBox();
    assert(Math.abs(left.width - right.width) <= 1 && right.x > left.x, "Desktop start zonder gelijke zijpanelen");

    const divider = await splitter.boundingBox();
    const x = divider.x + divider.width / 2;
    const y = divider.y + divider.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 125, y, { steps: 5 });
    await page.mouse.up();
    assert((await editorPane.boundingBox()).width > left.width + 100, "Slepen verandert de paneelbreedte niet");

    await page.evaluate(() => editor.setValue('console.log("synthetische uitvoer"); moveForward(80);'));
    await page.locator("#run-code").click();
    await page.locator("#eval-modal-primary").click();
    assert((await page.locator("#console-output").textContent()).includes("synthetische uitvoer"), "Console mist de uitvoer");
    assert(await page.evaluate(() => window.__getCanvasEvaluationData().trace.some(entry => entry.type === "moveForward")),
      "Canvas ontvangt geen tekenopdrachten terwijl de console actief is");
    assert(await canvasTab.evaluate(tab => getComputedStyle(tab).animationName) === "canvas-output-pulse",
      "Canvasuitvoer laat het tabblad niet pulseren");
    const drawing = await turtleCanvas.evaluate(canvas => canvas.toDataURL());
    await consoleTab.focus();
    await page.keyboard.press("ArrowRight");
    assert(await canvasTab.getAttribute("aria-selected") === "true", "Pijltoets opent canvas niet");
    assert(!await canvasTab.evaluate(tab => tab.classList.contains("has-canvas-output")), "Bekeken canvas blijft als nieuw gemarkeerd");
    assert(await turtleCanvas.isVisible(), "Canvas blijft verborgen");
    await page.keyboard.press("ArrowLeft");
    assert((await page.locator("#console-output").textContent()).includes("synthetische uitvoer"), "Tabwisseling wist console-uitvoer");
    assert(await turtleCanvas.evaluate(canvas => canvas.toDataURL()) === drawing, "Tabwisseling wijzigt de tekening");
    assert(await noPageScroll(), "Desktopwerkruimte laat de pagina scrollen");

    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForFunction(() => document.getElementById("splitter").getAttribute("aria-orientation") === "horizontal");
    const upper = await editorPane.boundingBox();
    const lower = await outputPane.boundingBox();
    assert(lower.y > upper.y && Math.abs(upper.width - lower.width) <= 1, "Smalle werkruimte stapelt de panelen niet");
    await splitter.focus();
    await page.keyboard.press("ArrowUp");
    assert((await editorPane.boundingBox()).height < upper.height, "Toetsenbord wijzigt de paneelhoogte niet");
    await page.locator("#console-output").evaluate(el => { el.textContent = "lange uitvoer\n".repeat(100); });
    assert(await page.locator("#console-panel").evaluate(el => el.scrollHeight > el.clientHeight),
      "Lange uitvoer kan niet binnen het consolepaneel scrollen");
    assert(await noPageScroll(), "Smalle werkruimte laat de pagina scrollen");
    await canvasTab.click();
    const canvas = await turtleCanvas.boundingBox();
    const stage = await page.locator(".canvas-stage").boundingBox();
    assert(canvas.width > 10 && Math.abs(canvas.width - canvas.height) <= 1 &&
      canvas.width <= stage.width + 1 && canvas.height <= stage.height + 1, "Canvas past niet vierkant in het paneel");
  });
  console.log("[OK] 50/50-werkruimte, uitvoertabs en paneelverdeling op desktop en mobiel");
}

async function inspectAssessment(page, baseUrl, assessment) {
  await page.goto(`${baseUrl}/evaluaties/${assessment.launchFile}`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(url => url.toString().includes(`/platform.html?assessment=${assessment.id}`), { timeout: 30000 });
  await startAssessment(page);
  let readySnapshot = null;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    readySnapshot = await page.evaluate(() => ({
      assessmentId: String(window.JSIK_ACTIVE_ASSESSMENT_ID || ""),
      courseSource: String(window.JSIK_COURSE_CONTENT_SOURCE || ""),
      contentCache: String(window.JSIK_COURSE_FETCH_CACHE || ""),
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
      contentCache: String(window.JSIK_COURSE_FETCH_CACHE || ""),
      courseSource: String(window.JSIK_COURSE_CONTENT_SOURCE || ""),
      loadStats: window.JSIK_COURSE_LOAD_STATS && typeof window.JSIK_COURSE_LOAD_STATS === "object"
        ? {
            cache: String(window.JSIK_COURSE_LOAD_STATS.cache || ""),
            chapterCount: Number(window.JSIK_COURSE_LOAD_STATS.chapterCount) || 0,
            exerciseCount: Number(window.JSIK_COURSE_LOAD_STATS.exerciseCount) || 0,
          }
        : null,
      loaderHidden: !!(document.getElementById("course-loading") && document.getElementById("course-loading").classList.contains("is-hidden")),
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
  if (snapshot.contentCache !== (assessment.contentCache || "no-store")) {
    issues.push(`unexpected content cache (${snapshot.contentCache})`);
  }
  if (snapshot.chapterCount !== 1) {
    issues.push(`expected 1 chapter, got ${snapshot.chapterCount}`);
  }
  if (snapshot.exerciseCount !== assessment.exerciseCount) {
    issues.push(`expected ${assessment.exerciseCount} exercises, got ${snapshot.exerciseCount}`);
  }
  if (!snapshot.loadStats || snapshot.loadStats.exerciseCount !== assessment.exerciseCount) {
    issues.push("course load stats are missing or inconsistent");
  }
  if (snapshot.loadStats && snapshot.loadStats.cache !== (assessment.contentCache || "no-store")) {
    issues.push(`load stats cache is ${snapshot.loadStats.cache}`);
  }
  if (!snapshot.loaderHidden) {
    issues.push("loading overlay did not hide after boot");
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
    await configurePage(page, baseUrl);
    await checkFallbacks(browser, baseUrl);
    await checkPracticeMode(browser, baseUrl);
    await checkTimedWorkspace(browser, baseUrl);
    await checkLifecycle(browser, baseUrl);
    for (const assessment of ASSESSMENTS) {
      const cap = assessment.kind === "exam" ? 100 : 45;
      if (!Number.isInteger(assessment.durationMinutes) || assessment.durationMinutes <= 0 || assessment.durationMinutes > cap) throw new Error(`Ongeldige duur voor ${assessment.id}`);
    }
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
