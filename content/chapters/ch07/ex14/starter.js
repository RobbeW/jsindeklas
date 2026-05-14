// Teken drie opgevulde cirkels met straal 20.
// Gebruik in elke herhaling randomColour() voor de kleur.
// Zet de cirkels op x = -120, 0 en 120, telkens op y = 0.
showGrid(50);
penUp();
for(var i = 0; i < 3; i++) {
  goTo(-120 + (i * 120), 0);
  penDown();
  setPenColour(...);
  fillCircle(...);
  penUp();
}