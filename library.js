// Auteur: Robbe Wulgaert / aiindeklas.be
// Copyright 2024 - Gebruik vrij voor educatie

(function() {
  // --- Settings ---
  const CANVAS_SIZE = 500;
  const TURTLE_SIZE = 16;

  // --- Canvas & Contexts ---
  let turtleCanvas = document.getElementById('turtlecanvas');
  let turtleCtx = turtleCanvas.getContext('2d');
  let imageCanvas = document.getElementById('imagecanvas');
  let imageCtx = imageCanvas.getContext('2d');

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
    turtleCtx.moveTo(0, 0);
    turtleCtx.lineTo(-TURTLE_SIZE/2, TURTLE_SIZE);
    turtleCtx.lineTo(TURTLE_SIZE/2, TURTLE_SIZE);
    turtleCtx.closePath();
    turtleCtx.fillStyle = "#32b43a";
    turtleCtx.shadowColor = "#333";
    turtleCtx.shadowBlur = 4;
    turtleCtx.fill();
    turtleCtx.restore();
  }

  function redrawAll() {
    // Draw persistent lines
    turtleCtx.clearRect(0,0,CANVAS_SIZE,CANVAS_SIZE);
    turtleCtx.drawImage(imageCanvas, 0,0);
    drawTurtle();
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
  };

  // Only clear drawing, keep turtle state
  window.clearCanvas = function() {
    clearImageCanvas();
    redrawAll();
  };

  // Beweeg vooruit
  window.moveForward = function(distance) {
    let rad = degToRad(turtle.angle);
    let x2 = turtle.x + distance * Math.cos(rad);
    let y2 = turtle.y + distance * Math.sin(rad);
    if (turtle.penDown) {
      drawLine(turtle.x, turtle.y, x2, y2, turtle.penColour, turtle.lineWidth);
    }
    turtle.x = x2;
    turtle.y = y2;
    redrawAll();
  };

  // Beweeg achteruit
  window.moveBackward = function(distance) {
    window.moveForward(-distance);
  };

  // Rechtsom draaien (graden)
  window.turnRight = function(angle) {
    turtle.angle = (turtle.angle + angle) % 360;
    redrawAll();
  };

  // Linksom draaien (graden)
  window.turnLeft = function(angle) {
    turtle.angle = (turtle.angle - angle + 360) % 360;
    redrawAll();
  };

  // Pen omhoog
  window.penUp = function() {
    turtle.penDown = false;
  };

  // Pen omlaag
  window.penDown = function() {
    turtle.penDown = true;
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
  };

  // Ga naar absolute positie
  window.goTo = function(x, y) {
    if (turtle.penDown) {
      drawLine(turtle.x, turtle.y, x, y, turtle.penColour, turtle.lineWidth);
    }
    turtle.x = x;
    turtle.y = y;
    redrawAll();
  };

  // Toon raster (rasterafstand in pixels)
  window.showGrid = function(stapgrootte=50) {
    clearImageCanvas();
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
    redrawAll();
  };

  // Zet turtle-hoek (absoluut)
  window.setTurtleAngle = function(angle) {
    turtle.angle = angle % 360;
    redrawAll();
  };

  // Toon/hide turtle
  window.showTurtle = function() {
    turtle.visible = true;
    redrawAll();
  };
  window.hideTurtle = function() {
    turtle.visible = false;
    redrawAll();
  };

  // Tekst schrijven op canvas op turtle positie
  window.writeText = function(text) {
    imageCtx.save();
    imageCtx.font = "bold 20px Roboto, sans-serif";
    imageCtx.fillStyle = kleurToStyle(turtle.penColour);
    imageCtx.textAlign = "center";
    imageCtx.textBaseline = "middle";
    imageCtx.fillText(
      text,
      centerX(turtle.x),
      centerY(turtle.y)
    );
    imageCtx.restore();
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
    'showGrid','setTurtleAngle','showTurtle','hideTurtle','writeText','randomColour'
  ].forEach(fn=>{
    if (!window[fn]) window[fn]=function(){};
  });

})();
