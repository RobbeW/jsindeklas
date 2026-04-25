// JavaScript in de Klas - oefeningmaker
// Copyright (c) 2026 Robbe Wulgaert
// Citeer/vermeld als: Robbe Wulgaert, AI in de Klas, robbewulgaert.be

(function(){
  const els = {
    chapterSelect: document.getElementById("chapterSelect"),
    newChapterFields: document.getElementById("newChapterFields"),
    newChapterId: document.getElementById("newChapterId"),
    newChapterOrder: document.getElementById("newChapterOrder"),
    newChapterTitle: document.getElementById("newChapterTitle"),
    exerciseOrder: document.getElementById("exerciseOrder"),
    exerciseId: document.getElementById("exerciseId"),
    exerciseTitle: document.getElementById("exerciseTitle"),
    evaluationMode: document.getElementById("evaluationMode"),
    evalOutput: document.getElementById("evalOutput"),
    starterCode: document.getElementById("starterCode"),
    testcaseBuilder: document.getElementById("testcaseBuilder"),
    testcaseList: document.getElementById("testcaseList"),
    testLabel: document.getElementById("testLabel"),
    testCheckType: document.getElementById("testCheckType"),
    testExpected: document.getElementById("testExpected"),
    testExpectedLabel: document.getElementById("testExpectedLabel"),
    testExpectedHint: document.getElementById("testExpectedHint"),
    testToleranceWrap: document.getElementById("testToleranceWrap"),
    testTolerance: document.getElementById("testTolerance"),
    testRegexFlagsWrap: document.getElementById("testRegexFlagsWrap"),
    testRegexFlags: document.getElementById("testRegexFlags"),
    testInputs: document.getElementById("testInputs"),
    replacementRows: document.getElementById("replacementRows"),
    addReplacementRow: document.getElementById("addReplacementRow"),
    canvasLineCount: document.getElementById("canvasLineCount"),
    canvasLineLengths: document.getElementById("canvasLineLengths"),
    canvasLineColour: document.getElementById("canvasLineColour"),
    canvasClosedShape: document.getElementById("canvasClosedShape"),
    addTestcase: document.getElementById("addTestcase"),
    resetTestcaseForm: document.getElementById("resetTestcaseForm"),
    syncJsonToBuilder: document.getElementById("syncJsonToBuilder"),
    testsJson: document.getElementById("testsJson"),
    preview: document.getElementById("preview"),
    status: document.getElementById("status"),
    packageList: document.getElementById("packageList"),
    generatePreview: document.getElementById("generatePreview"),
    addToPackage: document.getElementById("addToPackage"),
    downloadZip: document.getElementById("downloadZip"),
    reloadCatalog: document.getElementById("reloadCatalog"),
  };

  const state = {
    catalog: null,
    chapters: [],
    chapterJsonById: new Map(),
    pending: [],
    testcases: [
      {
        label:"Voorbeeld",
        stdout:"Hallo wereld",
      },
    ],
    jsonEditedByUser: false,
    syncingJson: false,
  };

  function setStatus(message, type = "ok"){
    els.status.textContent = message;
    els.status.className = `status${type === "warn" ? " warn" : ""}${type === "error" ? " error" : ""}`;
  }

  function twoDigits(value){
    return String(value).padStart(2, "0");
  }

  function normalizeFolderName(value, fallback){
    const cleaned = String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
    return cleaned || fallback;
  }

  function normalizeNewlines(value){
    return String(value || "").replace(/\r\n/g, "\n");
  }

  function splitInputLines(value){
    const normalized = normalizeNewlines(value);
    if (normalized.length === 0) {
      return [];
    }
    const parts = normalized.split("\n");
    if (parts.length > 0 && parts[parts.length - 1] === "") {
      parts.pop();
    }
    return parts;
  }

  function splitNonEmptyLines(value){
    return splitInputLines(value)
      .map(part => part.trim())
      .filter(Boolean);
  }

  function parseNumberList(value){
    const matches = normalizeNewlines(value).match(/-?\d+(?:[.,]\d+)?/g) || [];
    return matches
      .map(item => Number(item.replace(",", ".")))
      .filter(Number.isFinite);
  }

  function syncTestsJsonFromBuilder(){
    state.syncingJson = true;
    els.testsJson.value = JSON.stringify(state.testcases, null, 2);
    state.syncingJson = false;
    state.jsonEditedByUser = false;
  }

  function describeCheckType(testcase){
    if (testcase && testcase.eval && testcase.eval.type === "numbers") {
      return "getallencontrole";
    }
    if (testcase && testcase.eval && testcase.eval.type === "contains") {
      return "bevat-tekstcontrole";
    }
    if (testcase && testcase.eval && testcase.eval.type === "regex") {
      return "regexcontrole";
    }
    if (testcase && typeof testcase.stdout === "string") {
      return "console-uitvoer";
    }
    if (testcase && testcase.canvas) {
      return "canvascontrole";
    }
    return "aangepaste controle";
  }

  function describeTestcase(testcase){
    const parts = [describeCheckType(testcase)];
    const inputCount = Array.isArray(testcase && testcase.inputs) ? testcase.inputs.length : 0;
    const replacementCount = Array.isArray(testcase && testcase.replacements) ? testcase.replacements.length : 0;
    if (inputCount > 0) {
      parts.push(`${inputCount} invoerantwoord${inputCount === 1 ? "" : "en"}`);
    }
    if (replacementCount > 0) {
      parts.push(`${replacementCount} vervanging${replacementCount === 1 ? "" : "en"}`);
    }
    if (testcase && testcase.canvas) {
      parts.push("canvas");
    }
    return parts.join(" - ");
  }

  function renderTestcaseList(){
    els.testcaseList.innerHTML = "";

    if (state.testcases.length === 0) {
      const empty = document.createElement("li");
      empty.className = "testcase-card";
      const text = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = "Nog geen testcases";
      const hint = document.createElement("p");
      hint.textContent = "Vul de velden hieronder in en klik op 'Voeg testcase toe'.";
      text.appendChild(title);
      text.appendChild(hint);
      empty.appendChild(text);
      els.testcaseList.appendChild(empty);
      return;
    }

    state.testcases.forEach((testcase, index) => {
      const li = document.createElement("li");
      li.className = "testcase-card";

      const text = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `${index + 1}. ${testcase.label || "Testcase"}`;
      const summary = document.createElement("p");
      summary.textContent = describeTestcase(testcase);
      text.appendChild(title);
      text.appendChild(summary);

      const actions = document.createElement("div");
      actions.className = "card-actions";

      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "secondary";
      edit.textContent = "Bewerk";
      edit.addEventListener("click", () => {
        loadTestcaseIntoForm(testcase);
        state.testcases.splice(index, 1);
        renderTestcaseList();
        syncTestsJsonFromBuilder();
        setStatus("Testcase in de velden geladen. Pas aan en klik opnieuw op 'Voeg testcase toe'.", "warn");
      });

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary";
      remove.textContent = "Verwijder";
      remove.addEventListener("click", () => {
        state.testcases.splice(index, 1);
        renderTestcaseList();
        syncTestsJsonFromBuilder();
      });

      actions.appendChild(edit);
      actions.appendChild(remove);
      li.appendChild(text);
      li.appendChild(actions);
      els.testcaseList.appendChild(li);
    });
  }

  function addReplacementRow(from = "", to = ""){
    const row = document.createElement("div");
    row.className = "replacement-row";

    const fromWrap = document.createElement("div");
    const fromLabel = document.createElement("label");
    fromLabel.textContent = "Zoek deze code";
    const fromInput = document.createElement("input");
    fromInput.type = "text";
    fromInput.value = from;
    fromInput.placeholder = "var score = 10;";
    fromInput.dataset.replacementFrom = "true";
    fromWrap.appendChild(fromLabel);
    fromWrap.appendChild(fromInput);

    const toWrap = document.createElement("div");
    const toLabel = document.createElement("label");
    toLabel.textContent = "Vervang door";
    const toInput = document.createElement("input");
    toInput.type = "text";
    toInput.value = to;
    toInput.placeholder = "var score = 15;";
    toInput.dataset.replacementTo = "true";
    toWrap.appendChild(toLabel);
    toWrap.appendChild(toInput);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "secondary compact-button";
    remove.textContent = "Weg";
    remove.addEventListener("click", () => {
      const rows = els.replacementRows.querySelectorAll(".replacement-row");
      if (rows.length <= 1) {
        fromInput.value = "";
        toInput.value = "";
        return;
      }
      row.remove();
    });

    row.appendChild(fromWrap);
    row.appendChild(toWrap);
    row.appendChild(remove);
    els.replacementRows.appendChild(row);
  }

  function resetReplacementRows(replacements = []){
    els.replacementRows.innerHTML = "";
    if (!replacements.length) {
      addReplacementRow();
      return;
    }
    replacements.forEach(replacement => addReplacementRow(replacement.from, replacement.to));
  }

  function replacementValuesFromForm(){
    return Array.from(els.replacementRows.querySelectorAll(".replacement-row"))
      .map(row => ({
        from:String(row.querySelector("[data-replacement-from]").value || ""),
        to:String(row.querySelector("[data-replacement-to]").value || ""),
      }))
      .filter(replacement => replacement.from.length > 0);
  }

  function canvasConfigFromForm(){
    const canvas = {};
    const lineCount = Number.parseInt(els.canvasLineCount.value, 10);
    if (Number.isFinite(lineCount)) {
      canvas.lineCount = lineCount;
    }

    const lineLengths = parseNumberList(els.canvasLineLengths.value);
    if (lineLengths.length > 0) {
      canvas.lineLengths = lineLengths;
    }

    const lineColour = String(els.canvasLineColour.value || "").trim();
    if (lineColour.length > 0) {
      canvas.lineColour = lineColour;
    }

    if (els.canvasClosedShape.checked) {
      canvas.closedShape = true;
    }

    return Object.keys(canvas).length > 0 ? canvas : null;
  }

  function updateTestcaseTypeUi(){
    const type = els.testCheckType.value;
    els.testToleranceWrap.classList.toggle("hidden", type !== "numbers");
    els.testRegexFlagsWrap.classList.toggle("hidden", type !== "regex");
    els.testExpected.parentElement.classList.toggle("hidden", type === "canvas");

    if (type === "numbers") {
      els.testExpectedLabel.textContent = "Verwachte getallen";
      els.testExpected.placeholder = "Bijvoorbeeld: 1, 91238.28, 2, 91238.28";
      els.testExpectedHint.textContent = "Schrijf de getallen die in de uitvoer moeten voorkomen. Komma's, spaties en nieuwe regels mogen.";
      return;
    }

    if (type === "contains") {
      els.testExpectedLabel.textContent = "Verplichte woorden of tekstfragmenten";
      els.testExpected.placeholder = "Eén woord of tekstfragment per regel";
      els.testExpectedHint.textContent = "De uitvoer is juist als elk fragment ergens voorkomt. Hoofdletters tellen niet mee.";
      return;
    }

    if (type === "regex") {
      els.testExpectedLabel.textContent = "Regex-patroon";
      els.testExpected.placeholder = "Bijvoorbeeld: ^Hallo\\s+wereld$";
      els.testExpectedHint.textContent = "Gebruik dit alleen als je vertrouwd bent met regex. De JSON-editor blijft beschikbaar voor speciale gevallen.";
      return;
    }

    els.testExpectedLabel.textContent = "Verwachte console-uitvoer";
    els.testExpected.placeholder = "Bijvoorbeeld: Hallo wereld";
    els.testExpectedHint.textContent = "Schrijf de uitvoer zoals die in de console moet verschijnen. Meerdere regels zijn toegestaan.";
  }

  function resetTestcaseForm(){
    els.testLabel.value = "";
    els.testCheckType.value = "stdout";
    els.testExpected.value = "";
    els.testTolerance.value = "0.01";
    els.testRegexFlags.value = "i";
    els.testInputs.value = "";
    resetReplacementRows();
    els.canvasLineCount.value = "";
    els.canvasLineLengths.value = "";
    els.canvasLineColour.value = "";
    els.canvasClosedShape.checked = false;
    updateTestcaseTypeUi();
  }

  function testcaseFromForm(){
    const testcase = {
      label:String(els.testLabel.value || "").trim() || `Testcase ${state.testcases.length + 1}`,
    };
    const type = els.testCheckType.value;

    if (type === "numbers") {
      const expected = parseNumberList(els.testExpected.value);
      if (expected.length === 0) {
        throw new Error("Vul minstens een verwacht getal in voor deze testcase.");
      }
      const tolerance = Number.parseFloat(String(els.testTolerance.value || "").replace(",", "."));
      testcase.eval = {
        type:"numbers",
        expected,
      };
      if (Number.isFinite(tolerance)) {
        testcase.eval.tolerance = tolerance;
      }
    } else if (type === "contains") {
      const substrings = splitNonEmptyLines(els.testExpected.value);
      if (substrings.length === 0) {
        throw new Error("Vul minstens een verplicht woord of tekstfragment in.");
      }
      testcase.eval = {
        type:"contains",
        substrings,
      };
    } else if (type === "regex") {
      const pattern = normalizeNewlines(els.testExpected.value).trim();
      if (!pattern) {
        throw new Error("Vul een regex-patroon in.");
      }
      const flags = String(els.testRegexFlags.value || "i").trim() || "i";
      try {
        new RegExp(pattern, flags);
      } catch (error) {
        throw new Error(`Dit regex-patroon is niet geldig: ${error.message}`);
      }
      testcase.eval = {
        type:"regex",
        pattern,
        flags,
      };
    } else if (type === "stdout") {
      testcase.stdout = normalizeNewlines(els.testExpected.value).replace(/\n$/g, "");
    }

    const inputs = splitInputLines(els.testInputs.value);
    if (inputs.length > 0) {
      testcase.inputs = inputs;
    }

    const replacements = replacementValuesFromForm();
    if (replacements.length > 0) {
      testcase.replacements = replacements;
    }

    const canvas = canvasConfigFromForm();
    if (canvas) {
      testcase.canvas = canvas;
    } else if (type === "canvas") {
      throw new Error("Kies minstens een canvascontrole, zoals aantal lijnen of gesloten figuur.");
    }

    return testcase;
  }

  function loadTestcaseIntoForm(testcase){
    resetTestcaseForm();
    els.testLabel.value = String((testcase && testcase.label) || "");

    if (testcase && testcase.eval && testcase.eval.type === "numbers") {
      els.testCheckType.value = "numbers";
      els.testExpected.value = Array.isArray(testcase.eval.expected) ? testcase.eval.expected.join(", ") : "";
      els.testTolerance.value = String(testcase.eval.tolerance ?? 0.01);
    } else if (testcase && testcase.eval && testcase.eval.type === "contains") {
      els.testCheckType.value = "contains";
      els.testExpected.value = Array.isArray(testcase.eval.substrings) ? testcase.eval.substrings.join("\n") : "";
    } else if (testcase && testcase.eval && testcase.eval.type === "regex") {
      els.testCheckType.value = "regex";
      els.testExpected.value = String(testcase.eval.pattern || "");
      els.testRegexFlags.value = String(testcase.eval.flags || "i");
    } else if (testcase && typeof testcase.stdout === "string") {
      els.testCheckType.value = "stdout";
      els.testExpected.value = testcase.stdout;
    } else if (testcase && testcase.canvas) {
      els.testCheckType.value = "canvas";
    }

    if (testcase && Array.isArray(testcase.inputs)) {
      els.testInputs.value = testcase.inputs.join("\n");
    }

    if (testcase && Array.isArray(testcase.replacements)) {
      resetReplacementRows(testcase.replacements);
    }

    const canvas = testcase && testcase.canvas ? testcase.canvas : null;
    if (canvas) {
      els.canvasLineCount.value = Number.isFinite(Number(canvas.lineCount)) ? String(canvas.lineCount) : "";
      els.canvasLineLengths.value = Array.isArray(canvas.lineLengths) ? canvas.lineLengths.join(", ") : "";
      els.canvasLineColour.value = String(canvas.lineColour || "");
      els.canvasClosedShape.checked = !!canvas.closedShape;
    }

    updateTestcaseTypeUi();
  }

  function addTestcaseFromForm(){
    try {
      const testcase = testcaseFromForm();
      state.testcases.push(testcase);
      renderTestcaseList();
      syncTestsJsonFromBuilder();
      resetTestcaseForm();
      setStatus(`Testcase toegevoegd: ${testcase.label}.`, "ok");
    } catch (error) {
      setStatus(error.message || String(error), "error");
    }
  }

  function loadBuilderFromJson(){
    try {
      const parsed = JSON.parse(els.testsJson.value || "[]");
      if (!Array.isArray(parsed)) {
        throw new Error("Testcases moeten een JSON-array zijn.");
      }
      state.testcases = parsed;
      renderTestcaseList();
      syncTestsJsonFromBuilder();
      setStatus("JSON is ingelezen in de visuele testcasebouwer.", "ok");
    } catch (error) {
      setStatus(error.message || String(error), "error");
    }
  }

  function selectedChapter(){
    const id = els.chapterSelect.value;
    if (id === "__new__") {
      const order = Number.parseInt(els.newChapterOrder.value, 10);
      const chapterId = normalizeFolderName(els.newChapterId.value, "ch08");
      return {
        id:chapterId,
        title:String(els.newChapterTitle.value || "").trim() || "Nieuw hoofdstuk",
        order:Number.isFinite(order) ? order : 999,
        path:`chapters/${chapterId}/chapter.json`,
        isNew:true,
      };
    }
    return state.chapters.find(chapter => chapter.id === id) || null;
  }

  async function readJson(url){
    const response = await fetch(url, { cache:"no-store" });
    if (!response.ok) {
      throw new Error(`Kan ${url} niet laden (${response.status}).`);
    }
    return response.json();
  }

  function renderChapterOptions(){
    els.chapterSelect.innerHTML = "";
    state.chapters.forEach((chapter) => {
      const option = document.createElement("option");
      option.value = chapter.id;
      option.textContent = `${chapter.id} - ${chapter.title}`;
      els.chapterSelect.appendChild(option);
    });
    const newOption = document.createElement("option");
    newOption.value = "__new__";
    newOption.textContent = "Nieuw hoofdstuk...";
    els.chapterSelect.appendChild(newOption);
  }

  async function loadChapterJson(chapter){
    if (!chapter || !chapter.path) {
      return null;
    }
    if (chapter.isNew) {
      return {
        id:chapter.id,
        title:chapter.title,
        order:chapter.order,
        exercises:[],
      };
    }
    if (state.chapterJsonById.has(chapter.id)) {
      return state.chapterJsonById.get(chapter.id);
    }
    const chapterJson = await readJson(`../content/${chapter.path}`);
    state.chapterJsonById.set(chapter.id, chapterJson);
    return chapterJson;
  }

  function pendingForChapter(chapterId){
    return state.pending.filter(item => item.chapter.id === chapterId);
  }

  async function applyNextExerciseDefaults(){
    const chapter = selectedChapter();
    if (!chapter) {
      return;
    }

    try {
      const chapterJson = await loadChapterJson(chapter);
      const exercises = Array.isArray(chapterJson && chapterJson.exercises) ? chapterJson.exercises : [];
      const existingMax = exercises.reduce((max, item) => Math.max(max, Number(item.order) || 0), 0);
      const pendingMax = pendingForChapter(chapter.id).reduce((max, item) => Math.max(max, Number(item.order) || 0), 0);
      const nextOrder = Math.max(existingMax, pendingMax) + 1;
      els.exerciseOrder.value = String(nextOrder);
      els.exerciseId.value = `ex${twoDigits(nextOrder)}`;
      els.exerciseTitle.value = `${nextOrder}. Nieuwe oefening`;
      setStatus("Catalogus geladen. Maak een preview of voeg de oefening toe aan de ZIP.", "ok");
    } catch (error) {
      setStatus(`Catalogus geladen, maar chapter.json kon niet gelezen worden: ${error.message}`, "warn");
    }
  }

  async function loadCatalog(){
    try {
      const catalog = await readJson("../content/catalog.json");
      state.catalog = catalog;
      state.chapters = Array.isArray(catalog.chapters)
        ? catalog.chapters.slice().sort((a, b) => (a.order || 0) - (b.order || 0))
        : [];
      renderChapterOptions();
      await applyNextExerciseDefaults();
    } catch (error) {
      state.catalog = null;
      state.chapters = [
        { id:"ch01", title:"Hoofdstuk 1: Hello, World!", order:1, path:"chapters/ch01/chapter.json" },
        { id:"ch02", title:"Hoofdstuk 2: Datatypes en de Sequentie", order:2, path:"chapters/ch02/chapter.json" },
        { id:"ch03", title:"Hoofdstuk 3: De Selectie", order:3, path:"chapters/ch03/chapter.json" },
        { id:"ch04", title:"Hoofdstuk 4: Figuren Plotten", order:4, path:"chapters/ch04/chapter.json" },
        { id:"ch05", title:"Hoofdstuk 5: De Begrensde Herhaling", order:5, path:"chapters/ch05/chapter.json" },
        { id:"ch06", title:"Hoofdstuk 6: De Voorwaardelijke Herhaling", order:6, path:"chapters/ch06/chapter.json" },
        { id:"ch07", title:"Hoofdstuk 7: Figuren Plotten II", order:7, path:"chapters/ch07/chapter.json" },
      ];
      renderChapterOptions();
      setStatus("Kon content/catalog.json niet laden. Controleer of je de tool via GitHub Pages opent.", "warn");
    }
  }

  function parseTestsJson(){
    if (els.evaluationMode.value === "manual") {
      return null;
    }
    if (!state.jsonEditedByUser) {
      syncTestsJsonFromBuilder();
    }
    const parsed = JSON.parse(els.testsJson.value || "[]");
    if (!Array.isArray(parsed)) {
      throw new Error("Testcases moeten een JSON-array zijn.");
    }
    if (state.jsonEditedByUser) {
      state.testcases = parsed;
      renderTestcaseList();
    }
    return parsed;
  }

  function buildExerciseFiles(draft){
    const basePath = `content/chapters/${draft.chapter.id}/${draft.exerciseId}`;
    const files = [
      {
        path:`${basePath}/exercise.json`,
        content:`${JSON.stringify(draft.exerciseMeta, null, 2)}\n`,
      },
      {
        path:`${basePath}/starter.js`,
        content:draft.starterCode.endsWith("\n") ? draft.starterCode : `${draft.starterCode}\n`,
      },
    ];

    if (draft.mode === "testcases") {
      files.push({
        path:`${basePath}/tests.json`,
        content:`${JSON.stringify(draft.tests, null, 2)}\n`,
      });
    }

    return files;
  }

  async function buildDraftFromForm(){
    const chapter = selectedChapter();
    if (!chapter) {
      throw new Error("Kies eerst een hoofdstuk.");
    }

    const order = Number.parseInt(els.exerciseOrder.value, 10);
    if (!Number.isFinite(order) || order < 1) {
      throw new Error("Het volgnummer moet een positief getal zijn.");
    }

    const exerciseId = normalizeFolderName(els.exerciseId.value, `ex${twoDigits(order)}`);
    const exerciseTitle = String(els.exerciseTitle.value || "").trim() || `${order}. Nieuwe oefening`;
    const mode = els.evaluationMode.value === "manual" ? "manual" : "testcases";
    const starterCode = String(els.starterCode.value || "").replace(/\r\n/g, "\n");
    const tests = parseTestsJson();

    const exerciseMeta = {
      id:`${chapter.id}-${exerciseId}`,
      title:exerciseTitle,
      evaluationMode:mode,
      starterPath:"starter.js",
    };

    if (mode === "testcases") {
      const evalOutput = String(els.evalOutput.value || "").replace(/\r\n/g, "\n");
      if (evalOutput.trim().length > 0) {
        exerciseMeta.evalOutput = evalOutput;
      }
      exerciseMeta.testsPath = "tests.json";
    }

    return {
      chapter,
      exerciseId,
      order,
      mode,
      title:exerciseTitle,
      starterCode,
      tests,
      exerciseEntry:{
        id:`${chapter.id}-${exerciseId}`,
        order,
        path:`${exerciseId}/exercise.json`,
      },
      exerciseMeta,
    };
  }

  async function buildUpdatedChapterFile(chapter, drafts){
    const chapterJson = await loadChapterJson(chapter);
    const existing = Array.isArray(chapterJson && chapterJson.exercises) ? chapterJson.exercises.slice() : [];
    const draftIds = new Set(drafts.map(item => item.exerciseEntry.id));
    const draftPaths = new Set(drafts.map(item => item.exerciseEntry.path));
    const merged = existing
      .filter(item => item && !draftIds.has(item.id) && !draftPaths.has(item.path))
      .concat(drafts.map(item => item.exerciseEntry))
      .sort((a, b) => (a.order || 0) - (b.order || 0));

    const updatedChapter = {
      ...(chapterJson || { id:chapter.id, title:chapter.title, order:chapter.order || 0 }),
      exercises:merged,
    };

    return {
      path:`content/chapters/${chapter.id}/chapter.json`,
      content:`${JSON.stringify(updatedChapter, null, 2)}\n`,
    };
  }

  function buildUpdatedCatalogFile(newChapters){
    const catalog = state.catalog && typeof state.catalog === "object"
      ? JSON.parse(JSON.stringify(state.catalog))
      : { version:1, chapters:state.chapters.map(chapter => ({
          id:chapter.id,
          title:chapter.title,
          order:chapter.order,
          path:chapter.path,
        })) };

    const existing = Array.isArray(catalog.chapters) ? catalog.chapters : [];
    const newIds = new Set(newChapters.map(chapter => chapter.id));
    catalog.chapters = existing
      .filter(chapter => chapter && !newIds.has(chapter.id))
      .concat(newChapters.map(chapter => ({
        id:chapter.id,
        title:chapter.title,
        order:chapter.order,
        path:`chapters/${chapter.id}/chapter.json`,
      })))
      .sort((a, b) => (a.order || 0) - (b.order || 0));

    return {
      path:"content/catalog.json",
      content:`${JSON.stringify(catalog, null, 2)}\n`,
    };
  }

  async function buildUploadPackage(drafts){
    if (!drafts.length) {
      throw new Error("Voeg eerst minstens een oefening toe aan de ZIP.");
    }

    const files = [];
    const byChapter = new Map();

    drafts.forEach((draft) => {
      if (!byChapter.has(draft.chapter.id)) {
        byChapter.set(draft.chapter.id, { chapter:draft.chapter, drafts:[] });
      }
      byChapter.get(draft.chapter.id).drafts.push(draft);
      files.push(...buildExerciseFiles(draft));
    });

    for (const item of byChapter.values()) {
      files.push(await buildUpdatedChapterFile(item.chapter, item.drafts));
    }

    const newChapters = Array.from(new Map(
      Array.from(byChapter.values())
        .map(item => item.chapter)
        .filter(chapter => chapter && chapter.isNew)
        .map(chapter => [chapter.id, chapter])
    ).values());
    if (newChapters.length > 0) {
      files.push(buildUpdatedCatalogFile(newChapters));
    }

    files.push({
      path:"UPLOAD_INSTRUCTIONS.md",
      content:[
        "# Uploadinstructies",
        "",
        "Upload de mappen en bestanden uit deze ZIP naar dezelfde paden in je GitHub-fork.",
        "",
        "Je hoeft geen build-script uit te voeren.",
        "De leeromgeving leest `content/catalog.json`, `chapter.json`, `exercise.json`, `starter.js` en `tests.json` rechtstreeks op GitHub Pages.",
        "",
        "Controleer na upload:",
        "",
        "1. Open je GitHub Pages-site.",
        "2. Ga naar het hoofdstuk waar je de oefening toevoegde.",
        "3. Test een correcte en een foute oplossing.",
        "",
      ].join("\n"),
    });

    files.sort((a, b) => a.path.localeCompare(b.path, "nl-BE", { numeric:true }));
    return {
      createdAt:new Date().toISOString(),
      drafts,
      files,
    };
  }

  async function renderPreview(drafts){
    const pack = await buildUploadPackage(drafts);
    const output = [];
    output.push(`GitHub upload ZIP - ${drafts.length} oefening(en)`);
    output.push("");
    pack.files.forEach((file) => {
      output.push(`--- ${file.path}`);
      output.push(file.content.trimEnd());
      output.push("");
    });
    els.preview.textContent = output.join("\n");
    return pack;
  }

  async function generatePreview(){
    try {
      const draft = await buildDraftFromForm();
      await renderPreview([...state.pending, draft]);
      setStatus("Preview klaar. Voeg toe aan de ZIP of pas de velden verder aan.", "ok");
      return draft;
    } catch (error) {
      setStatus(error.message || String(error), "error");
      throw error;
    }
  }

  function renderPackageList(){
    els.packageList.innerHTML = "";
    state.pending.forEach((draft, index) => {
      const li = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = `${draft.chapter.id}/${draft.exerciseId} - ${draft.title}`;
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Verwijder";
      button.addEventListener("click", async () => {
        state.pending.splice(index, 1);
        renderPackageList();
        if (state.pending.length > 0) {
          await renderPreview(state.pending);
        } else {
          els.preview.textContent = "De gegenereerde file tree verschijnt hier.";
        }
        await applyNextExerciseDefaults();
      });
      li.appendChild(label);
      li.appendChild(button);
      els.packageList.appendChild(li);
    });
  }

  async function addToPackage(){
    try {
      const draft = await buildDraftFromForm();
      const duplicateIndex = state.pending.findIndex(item =>
        item.chapter.id === draft.chapter.id && item.exerciseId === draft.exerciseId
      );
      if (duplicateIndex >= 0) {
        state.pending.splice(duplicateIndex, 1, draft);
      } else {
        state.pending.push(draft);
      }
      renderPackageList();
      await renderPreview(state.pending);
      setStatus(`${draft.chapter.id}/${draft.exerciseId} toegevoegd aan de ZIP.`, "ok");
      await applyNextExerciseDefaults();
    } catch (error) {
      setStatus(error.message || String(error), "error");
    }
  }

  function makeCrcTable(){
    const table = [];
    for (let n = 0; n < 256; n += 1) {
      let c = n;
      for (let k = 0; k < 8; k += 1) {
        c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[n] = c >>> 0;
    }
    return table;
  }

  const CRC_TABLE = makeCrcTable();

  function crc32(bytes){
    let crc = 0xffffffff;
    for (let index = 0; index < bytes.length; index += 1) {
      crc = CRC_TABLE[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function dosDateTime(date){
    const year = Math.max(1980, date.getFullYear());
    const dosTime = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
    const dosDate = ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
    return { dosTime, dosDate };
  }

  function u16(value){
    return [value & 0xff, (value >>> 8) & 0xff];
  }

  function u32(value){
    return [value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff];
  }

  function bytesFromArray(values){
    return new Uint8Array(values);
  }

  function concatBytes(chunks){
    const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const out = new Uint8Array(total);
    let offset = 0;
    chunks.forEach((chunk) => {
      out.set(chunk, offset);
      offset += chunk.length;
    });
    return out;
  }

  function createZipBlob(files){
    const encoder = new TextEncoder();
    const chunks = [];
    const central = [];
    const now = new Date();
    const { dosTime, dosDate } = dosDateTime(now);
    let offset = 0;

    files.forEach((file) => {
      const nameBytes = encoder.encode(file.path);
      const dataBytes = encoder.encode(file.content);
      const crc = crc32(dataBytes);
      const localHeader = bytesFromArray([
        ...u32(0x04034b50),
        ...u16(20),
        ...u16(0x0800),
        ...u16(0),
        ...u16(dosTime),
        ...u16(dosDate),
        ...u32(crc),
        ...u32(dataBytes.length),
        ...u32(dataBytes.length),
        ...u16(nameBytes.length),
        ...u16(0),
      ]);
      chunks.push(localHeader, nameBytes, dataBytes);

      const centralHeader = bytesFromArray([
        ...u32(0x02014b50),
        ...u16(20),
        ...u16(20),
        ...u16(0x0800),
        ...u16(0),
        ...u16(dosTime),
        ...u16(dosDate),
        ...u32(crc),
        ...u32(dataBytes.length),
        ...u32(dataBytes.length),
        ...u16(nameBytes.length),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u32(0),
        ...u32(offset),
      ]);
      central.push(centralHeader, nameBytes);
      offset += localHeader.length + nameBytes.length + dataBytes.length;
    });

    const centralStart = offset;
    const centralBytes = concatBytes(central);
    const endRecord = bytesFromArray([
      ...u32(0x06054b50),
      ...u16(0),
      ...u16(0),
      ...u16(files.length),
      ...u16(files.length),
      ...u32(centralBytes.length),
      ...u32(centralStart),
      ...u16(0),
    ]);

    return new Blob([concatBytes([...chunks, centralBytes, endRecord])], { type:"application/zip" });
  }

  async function downloadZip(){
    try {
      const drafts = state.pending.length > 0 ? state.pending : [await buildDraftFromForm()];
      const pack = await buildUploadPackage(drafts);
      const blob = createZipBlob(pack.files);
      const first = drafts[0];
      const fileName = drafts.length === 1
        ? `jsik-upload-${first.chapter.id}-${first.exerciseId}.zip`
        : `jsik-upload-${drafts.length}-oefeningen.zip`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setStatus(`ZIP gedownload: ${fileName}. Upload de inhoud naar je GitHub-fork.`, "ok");
    } catch (error) {
      setStatus(error.message || String(error), "error");
    }
  }

  els.chapterSelect.addEventListener("change", applyNextExerciseDefaults);
  els.chapterSelect.addEventListener("change", () => {
    els.newChapterFields.classList.toggle("hidden", els.chapterSelect.value !== "__new__");
  });
  [els.newChapterId, els.newChapterTitle, els.newChapterOrder].forEach((input) => {
    input.addEventListener("input", () => {
      if (els.chapterSelect.value === "__new__") {
        applyNextExerciseDefaults();
      }
    });
  });
  els.evaluationMode.addEventListener("change", () => {
    const manual = els.evaluationMode.value === "manual";
    els.testcaseBuilder.classList.toggle("hidden", manual);
    els.testsJson.disabled = manual;
    els.evalOutput.disabled = manual;
    if (manual) {
      setStatus("Manuele oefeningen krijgen geen tests.json. Ze worden open beoordeeld.", "warn");
    }
  });
  els.testCheckType.addEventListener("change", updateTestcaseTypeUi);
  els.addReplacementRow.addEventListener("click", () => addReplacementRow());
  els.addTestcase.addEventListener("click", addTestcaseFromForm);
  els.resetTestcaseForm.addEventListener("click", resetTestcaseForm);
  els.syncJsonToBuilder.addEventListener("click", loadBuilderFromJson);
  els.testsJson.addEventListener("input", () => {
    if (!state.syncingJson) {
      state.jsonEditedByUser = true;
    }
  });
  els.generatePreview.addEventListener("click", () => { generatePreview().catch(() => {}); });
  els.addToPackage.addEventListener("click", addToPackage);
  els.downloadZip.addEventListener("click", downloadZip);
  els.reloadCatalog.addEventListener("click", loadCatalog);

  renderTestcaseList();
  syncTestsJsonFromBuilder();
  resetTestcaseForm();
  loadCatalog();
})();
