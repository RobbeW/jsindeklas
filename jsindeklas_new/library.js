// JavaScript in de Klas
// Copyright (c) 2026 Robbe Wulgaert
// Citeer/vermeld als: Robbe Wulgaert, AI in de Klas, robbewulgaert.be

(function() {
  // --- Settings ---
  const CANVAS_SIZE = 1000;
  const TURTLE_SIZE = 32;
  let zoom = 1.0;          
  let panX = 0;            
  let panY = 0;            
  
  

  // --- Canvas & Contexts ---
  let turtleCanvas = document.getElementById('turtlecanvas');
  let turtleCtx = turtleCanvas.getContext('2d');
  let imageCanvas = document.getElementById('imagecanvas');
  let imageCtx = imageCanvas.getContext('2d');

  turtleCanvas.width = CANVAS_SIZE;
  turtleCanvas.height = CANVAS_SIZE;
  imageCanvas.width = CANVAS_SIZE;
  imageCanvas.height = CANVAS_SIZE;
  
  let bounds = {
  minX: 0, maxX: 0,
  minY: 0, maxY: 0,
  initialized: false
  };
  let canvasTrace = [];

  // --- Turtle State ---
  let turtle = {
    x: 0,
    y: 0,
    angle: 0,           // graden
    penDown: true,
    penColour: [0,0,0],
    lineWidth: 2,
    visible: true
  };

  // --- Helpers ---
  function degToRad(deg) { return deg * Math.PI / 180; }
  function radToDeg(rad) { return rad * 180 / Math.PI; }
  function kleurToStyle(rgb) {
    if(Array.isArray(rgb)) return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
    return rgb;
  }
  function roundTraceValue(value, decimals = 2) {
    const num = Number(value);
    if (!Number.isFinite(num)) return 0;
    const factor = Math.pow(10, decimals);
    return Math.round(num * factor) / factor;
  }
  function cloneSimple(value) {
    return JSON.parse(JSON.stringify(value));
  }
  function serializeBounds() {
    return {
      minX: roundTraceValue(bounds.minX),
      maxX: roundTraceValue(bounds.maxX),
      minY: roundTraceValue(bounds.minY),
      maxY: roundTraceValue(bounds.maxY),
      initialized: !!bounds.initialized
    };
  }
  function serializeTurtleState() {
    return {
      x: roundTraceValue(turtle.x),
      y: roundTraceValue(turtle.y),
      angle: roundTraceValue(turtle.angle),
      penDown: !!turtle.penDown,
      penColour: kleurToStyle(turtle.penColour),
      lineWidth: roundTraceValue(turtle.lineWidth),
      visible: !!turtle.visible
    };
  }
  function resetCanvasTrace() {
    canvasTrace = [];
  }
  function recordCanvasTrace(entry) {
    canvasTrace.push(entry);
    if (canvasTrace.length > 4000) {
      canvasTrace.shift();
    }
  }

    // --- Rounding helper for students ---
  // round(waarde, decimalen) -> number
  window.round = function(value, decimals = 0) {
    let num = Number(value);
    if (isNaN(num)) return NaN;

    decimals = Math.max(0, Math.min(10, Number(decimals) || 0));

    const factor = Math.pow(10, decimals);
    return Math.round(num * factor) / factor;
  };
  
  // modal ter vervanging van prompt voor gebruik binnen SEB: 
// Modal-gestuurde ask()-functie
window.ask = function(message) {
  return new Promise((resolve) => {
    const modal = document.getElementById('ask-modal');
    const msgDiv = document.getElementById('ask-modal-msg');
    const input = document.getElementById('ask-modal-input');
    const okBtn = document.getElementById('ask-modal-ok');

    msgDiv.textContent = message;
    input.value = '';
    modal.style.display = 'flex';
    input.focus();

    function cleanup() {
      modal.style.display = 'none';
      okBtn.removeEventListener('click', onOk);
      input.removeEventListener('keydown', onEnter);
    }
    function onOk() {
      cleanup();
      resolve(input.value);
    }
    function onEnter(e) {
      if (e.key === 'Enter') onOk();
    }

    okBtn.addEventListener('click', onOk);
    input.addEventListener('keydown', onEnter);
  });
};

// Asynchrone runner, zorgt dat alle await's werken
window.runStudentCode = async function(studentCode) {
  // Vervang alle ask( door await ask(
  const transformed = studentCode.replace(/ask\s*\(/g, 'await ask(');
  // Wrap in async functie en wacht op volledige uitvoer
  const wrapper = `
    return (async function() {
      ${transformed}
    })();
  `;
  // Gebruik Function-constructor om ask en console te injecteren
  return new Function('ask', 'console', wrapper)(window.ask, window.console);
};



  
  function centerX(x) { return Math.round(CANVAS_SIZE/2 + x); }
  function centerY(y) { return Math.round(CANVAS_SIZE/2 - y); }

  // --- Drawing functions ---
  function drawTurtle() {
    if (!turtle.visible) return;
    let { x, y, angle } = turtle;
    let px = centerX(x), py = centerY(y);
    turtleCtx.save();
    turtleCtx.translate(px, py);
    turtleCtx.rotate(-degToRad(angle));
    turtleCtx.beginPath();
    turtleCtx.moveTo( TURTLE_SIZE,           0);
    turtleCtx.lineTo(-TURTLE_SIZE/2,  TURTLE_SIZE/2);
    turtleCtx.lineTo(-TURTLE_SIZE/2, -TURTLE_SIZE/2);
    turtleCtx.closePath();
    turtleCtx.fillStyle = "#5200FF";
    turtleCtx.shadowColor = "#3700B3";
    turtleCtx.shadowBlur = 6;
    turtleCtx.fill();
    turtleCtx.restore();
  }

  function redrawAll() {
  // Clear en reset
  turtleCtx.save();
  turtleCtx.setTransform(1, 0, 0, 1, 0, 0); 
  turtleCtx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
  
  turtleCtx.setTransform(zoom, 0, 0, zoom, CANVAS_SIZE/2*(1-zoom)+panX, CANVAS_SIZE/2*(1-zoom)+panY);

  turtleCtx.drawImage(imageCanvas, 0, 0);
  drawTurtle(); // This will use the current transform!
  turtleCtx.restore();
}



  function drawLine(x0, y0, x1, y1, colour, width) {
    imageCtx.save();
    imageCtx.strokeStyle = kleurToStyle(colour);
    imageCtx.lineWidth = width;
    imageCtx.lineCap = "round";
    imageCtx.beginPath();
    imageCtx.moveTo(centerX(x0), centerY(y0));
    imageCtx.lineTo(centerX(x1), centerY(y1));
    imageCtx.stroke();
    imageCtx.restore();
  }

  function drawCircleShape(x, y, radius, colour, width, filled = false) {
    const safeRadius = Math.abs(Number(radius) || 0);
    imageCtx.save();
    imageCtx.beginPath();
    imageCtx.arc(centerX(x), centerY(y), safeRadius, 0, Math.PI * 2);
    if (filled) {
      imageCtx.fillStyle = kleurToStyle(colour);
      imageCtx.fill();
    } else {
      imageCtx.strokeStyle = kleurToStyle(colour);
      imageCtx.lineWidth = width;
      imageCtx.stroke();
    }
    imageCtx.restore();
  }

  function updateCircleBounds(x, y, radius) {
    const safeRadius = Math.abs(Number(radius) || 0);
    updateBounds(x - safeRadius, y - safeRadius);
    updateBounds(x + safeRadius, y + safeRadius);
  }

  function clearImageCanvas() {
    imageCtx.clearRect(0,0,CANVAS_SIZE,CANVAS_SIZE);
  }

  // Reset turtle and clear drawing
  window.resetTurtle = function() {
    turtle.x = 0;
    turtle.y = 0;
    turtle.angle = 0;
    turtle.penDown = true;
    turtle.penColour = [0,0,0];
    turtle.lineWidth = 2;
    turtle.visible = true;
    clearImageCanvas();
    redrawAll();
    bounds = { minX: 0, maxX: 0, minY: 0, maxY: 0, initialized: false };
    resetCanvasTrace();
  };

  // Only clear drawing, keep turtle state
  window.clearCanvas = function() {
    clearImageCanvas();
    redrawAll();
    bounds = { minX: 0, maxX: 0, minY: 0, maxY: 0, initialized: false };
    resetCanvasTrace();
    recordCanvasTrace({ type: "clearCanvas" });
  };

  // Beweeg vooruit
  window.moveForward = function(distance) {
  let rad = degToRad(turtle.angle);
  let x1 = turtle.x;
  let y1 = turtle.y;
  let x2 = turtle.x + distance * Math.cos(rad);
  let y2 = turtle.y + distance * Math.sin(rad);
  if (turtle.penDown) {
    drawLine(x1, y1, x2, y2, turtle.penColour, turtle.lineWidth);
    updateBounds(x1, y1);  // both endpoints
    updateBounds(x2, y2);
  }
  turtle.x = x2;
  turtle.y = y2;
  recordCanvasTrace({
    type: "moveForward",
    distance: roundTraceValue(distance),
    drawn: !!turtle.penDown,
    from: { x: roundTraceValue(x1), y: roundTraceValue(y1) },
    to: { x: roundTraceValue(x2), y: roundTraceValue(y2) },
    penColour: kleurToStyle(turtle.penColour),
    lineWidth: roundTraceValue(turtle.lineWidth)
  });
  redrawAll();
};


  // Beweeg achteruit
  window.moveBackward = function(distance) {
    window.moveForward(-distance);
  };

  // Rechtsom draaien (graden)
  window.turnRight = function(angle) {
    turtle.angle = (turtle.angle - angle + 360) % 360;
    recordCanvasTrace({
      type: "turnRight",
      angle: roundTraceValue(angle),
      newAngle: roundTraceValue(turtle.angle)
    });
    redrawAll();
  };

  // Linksom draaien (graden)
  window.turnLeft = function(angle) {
    turtle.angle = (turtle.angle + angle) % 360;
    recordCanvasTrace({
      type: "turnLeft",
      angle: roundTraceValue(angle),
      newAngle: roundTraceValue(turtle.angle)
    });
    redrawAll();
  };

  // Pen omhoog
  window.penUp = function() {
    turtle.penDown = false;
    recordCanvasTrace({ type: "penUp" });
  };

  // Pen omlaag
  window.penDown = function() {
    turtle.penDown = true;
    recordCanvasTrace({ type: "penDown" });
  };

  // Zet penkleur (r,g,b) of string
  window.setPenColour = function(r,g,b) {
    if (arguments.length === 1 && typeof r === "string") {
      // CSS colour
      turtle.penColour = r;
    } else if (arguments.length === 1 && Array.isArray(r)) {
      turtle.penColour = r;
    } else if (arguments.length === 3) {
      turtle.penColour = [r,g,b];
    }
    // else ignore
    recordCanvasTrace({
      type: "setPenColour",
      penColour: kleurToStyle(turtle.penColour)
    });
  };

  // Random kleuren toekennen aan de pen
  function randomColour() {
    var colours = [
      'red', 'green', 'blue', 'orange', 'purple',
      'pink', 'crimson', 'gold', 'yellow', 'cyan',
      'magenta', 'brown', 'lime', 'turquoise', 'black'
    ];
    var i = Math.floor(Math.random() * colours.length);
    return colours[i];
  }

  // Zet lijndikte
  window.setLineWidth = function(width) {
    turtle.lineWidth = width;
    recordCanvasTrace({
      type: "setLineWidth",
      lineWidth: roundTraceValue(width)
    });
  };

  // Ga naar absolute positie
  window.goTo = function(x, y) {
  if (turtle.penDown) {
    drawLine(turtle.x, turtle.y, x, y, turtle.penColour, turtle.lineWidth);
    updateBounds(turtle.x, turtle.y);
    updateBounds(x, y);
  }
  recordCanvasTrace({
    type: "goTo",
    drawn: !!turtle.penDown,
    from: { x: roundTraceValue(turtle.x), y: roundTraceValue(turtle.y) },
    to: { x: roundTraceValue(x), y: roundTraceValue(y) },
    penColour: kleurToStyle(turtle.penColour),
    lineWidth: roundTraceValue(turtle.lineWidth)
  });
  turtle.x = x;
  turtle.y = y;
  redrawAll();
};

  // Toon raster (rasterafstand in pixels)
  window.showGrid = function(stapgrootte=50) {
    resetCanvasTrace();
    clearImageCanvas();
    bounds = { minX: 0, maxX: 0, minY: 0, maxY: 0, initialized: false };
    imageCtx.save();
    imageCtx.strokeStyle = "#e0e0e0";
    imageCtx.lineWidth = 1;
    // Verticaal
    for (let x=-CANVAS_SIZE/2; x<=CANVAS_SIZE/2; x+=stapgrootte) {
      imageCtx.beginPath();
      imageCtx.moveTo(centerX(x), centerY(-CANVAS_SIZE/2));
      imageCtx.lineTo(centerX(x), centerY(CANVAS_SIZE/2));
      imageCtx.stroke();
    }
    // Horizontaal
    for (let y=-CANVAS_SIZE/2; y<=CANVAS_SIZE/2; y+=stapgrootte) {
      imageCtx.beginPath();
      imageCtx.moveTo(centerX(-CANVAS_SIZE/2), centerY(y));
      imageCtx.lineTo(centerX(CANVAS_SIZE/2), centerY(y));
      imageCtx.stroke();
    }
    // Assen
    imageCtx.strokeStyle = "#5200FF";
    imageCtx.lineWidth = 2;
    // X-as
    imageCtx.beginPath();
    imageCtx.moveTo(centerX(-CANVAS_SIZE/2), centerY(0));
    imageCtx.lineTo(centerX(CANVAS_SIZE/2), centerY(0));
    imageCtx.stroke();
    // Y-as
    imageCtx.beginPath();
    imageCtx.moveTo(centerX(0), centerY(-CANVAS_SIZE/2));
    imageCtx.lineTo(centerX(0), centerY(CANVAS_SIZE/2));
    imageCtx.stroke();
    imageCtx.restore();
    recordCanvasTrace({
      type: "showGrid",
      step: roundTraceValue(stapgrootte)
    });
    redrawAll();
  };

  // Zet turtle-hoek (absoluut)
  window.setTurtleAngle = function(angle) {
    turtle.angle = angle % 360;
    recordCanvasTrace({
      type: "setTurtleAngle",
      angle: roundTraceValue(turtle.angle)
    });
    redrawAll();
  };

  // Toon/hide turtle
  window.showTurtle = function() {
    turtle.visible = true;
    recordCanvasTrace({ type: "showTurtle" });
    redrawAll();
  };
  window.hideTurtle = function() {
    turtle.visible = false;
    recordCanvasTrace({ type: "hideTurtle" });
    redrawAll();
  };
  

  // Tekst schrijven op canvas op turtle positie
window.writeText = function(text) {
  imageCtx.save();
  imageCtx.font = "bold 20px Roboto, sans-serif";
  imageCtx.fillStyle = kleurToStyle(turtle.penColour);
  imageCtx.textAlign = "center";
  imageCtx.textBaseline = "middle";
  imageCtx.fillText(text, centerX(turtle.x), centerY(turtle.y));
  imageCtx.restore();
  updateBounds(turtle.x, turtle.y);
  recordCanvasTrace({
    type: "writeText",
    text: String(text),
    x: roundTraceValue(turtle.x),
    y: roundTraceValue(turtle.y),
    penColour: kleurToStyle(turtle.penColour)
  });
  redrawAll();
};

  window.drawCircle = function(radius) {
    const safeRadius = Math.abs(Number(radius) || 0);
    drawCircleShape(turtle.x, turtle.y, safeRadius, turtle.penColour, turtle.lineWidth, false);
    updateCircleBounds(turtle.x, turtle.y, safeRadius);
    recordCanvasTrace({
      type: "drawCircle",
      x: roundTraceValue(turtle.x),
      y: roundTraceValue(turtle.y),
      radius: roundTraceValue(safeRadius),
      penColour: kleurToStyle(turtle.penColour),
      lineWidth: roundTraceValue(turtle.lineWidth)
    });
    redrawAll();
  };

  window.fillCircle = function(radius) {
    const safeRadius = Math.abs(Number(radius) || 0);
    drawCircleShape(turtle.x, turtle.y, safeRadius, turtle.penColour, turtle.lineWidth, true);
    updateCircleBounds(turtle.x, turtle.y, safeRadius);
    recordCanvasTrace({
      type: "fillCircle",
      x: roundTraceValue(turtle.x),
      y: roundTraceValue(turtle.y),
      radius: roundTraceValue(safeRadius),
      penColour: kleurToStyle(turtle.penColour),
      lineWidth: roundTraceValue(turtle.lineWidth)
    });
    redrawAll();
  };


  // Initialiseren bij laden
  window.addEventListener('DOMContentLoaded', function() {
    window.resetTurtle();
  });

  // Expose randomColour to window
  window.randomColour = randomColour;

  // Zorg dat functies altijd bestaan (no-op fallback)
  [
    'resetTurtle','clearCanvas','moveForward','moveBackward','turnRight',
    'turnLeft','penUp','penDown','setPenColour','setLineWidth','goTo',
    'showGrid','setTurtleAngle','showTurtle','hideTurtle','writeText',
    'drawCircle','fillCircle','randomColour', 'round'
  ].forEach(fn=>{
    if (!window[fn]) window[fn]=function(){};
  });

  window.__getCanvasEvaluationData = function() {
    return {
      trace: cloneSimple(canvasTrace),
      finalState: serializeTurtleState(),
      bounds: serializeBounds()
    };
  };

  window.__captureCanvasRuntimeSnapshot = function() {
    return {
      trace: cloneSimple(canvasTrace),
      turtle: serializeTurtleState(),
      bounds: serializeBounds(),
      zoom: roundTraceValue(zoom, 4),
      panX: roundTraceValue(panX),
      panY: roundTraceValue(panY)
    };
  };

  window.__restoreCanvasRuntimeSnapshot = function(snapshot) {
    if (!snapshot || typeof snapshot !== "object") return;

    if (snapshot.turtle && typeof snapshot.turtle === "object") {
      turtle.x = Number(snapshot.turtle.x) || 0;
      turtle.y = Number(snapshot.turtle.y) || 0;
      turtle.angle = Number(snapshot.turtle.angle) || 0;
      turtle.penDown = !!snapshot.turtle.penDown;
      turtle.penColour = snapshot.turtle.penColour || [0,0,0];
      turtle.lineWidth = Number(snapshot.turtle.lineWidth) || 2;
      turtle.visible = snapshot.turtle.visible !== false;
    }

    if (snapshot.bounds && typeof snapshot.bounds === "object") {
      bounds = {
        minX: Number(snapshot.bounds.minX) || 0,
        maxX: Number(snapshot.bounds.maxX) || 0,
        minY: Number(snapshot.bounds.minY) || 0,
        maxY: Number(snapshot.bounds.maxY) || 0,
        initialized: !!snapshot.bounds.initialized
      };
    } else {
      bounds = { minX: 0, maxX: 0, minY: 0, maxY: 0, initialized: false };
    }

    zoom = Number(snapshot.zoom) || 1;
    panX = Number(snapshot.panX) || 0;
    panY = Number(snapshot.panY) || 0;
    canvasTrace = Array.isArray(snapshot.trace) ? cloneSimple(snapshot.trace) : [];
    redrawAll();
  };
  
function zoomIn() {
  zoom *= 1.25;
  redrawAll(); 
}
function zoomOut() {
  zoom /= 1.25;
  redrawAll();
}




window.pan = function(dx, dy) {
  panX += dx;
  panY += dy;
  redrawAll();
};

  function updateBounds(x, y) {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  if (!bounds.initialized) {
    bounds.minX = bounds.maxX = x;
    bounds.minY = bounds.maxY = y;
    bounds.initialized = true;
  } else {
    if (x < bounds.minX) bounds.minX = x;
    if (x > bounds.maxX) bounds.maxX = x;
    if (y < bounds.minY) bounds.minY = y;
    if (y > bounds.maxY) bounds.maxY = y;
  }
}
  
  function fitToDrawing() {
  if (!bounds.initialized) return; // nothing drawn yet

  const margin = 20; // pixels around the drawing

  const drawWidth = Math.max(1, bounds.maxX - bounds.minX);
  const drawHeight = Math.max(1, bounds.maxY - bounds.minY);

  // Compute scaling factors for both axes
  const scaleX = (CANVAS_SIZE - 2*margin) / drawWidth;
  const scaleY = (CANVAS_SIZE - 2*margin) / drawHeight;
  // Choose the smaller scale to fit both dimensions
  zoom = Math.min(scaleX, scaleY);

  // Center the drawing
  const centerXOfDrawing = (bounds.minX + bounds.maxX) / 2;
  const centerYOfDrawing = (bounds.minY + bounds.maxY) / 2;
  panX = CANVAS_SIZE/2 - zoom * centerXOfDrawing;
  panY = CANVAS_SIZE/2 - zoom * centerYOfDrawing;

  redrawAll();
}


window.CANVAS_SIZE = CANVAS_SIZE;
window.panX = panX;
window.panY = panY;
window.zoom = zoom;
window.zoomOut = zoomOut;
window.zoomIn = zoomIn;

})();
