// Teken 4 vierkanten met zijde 40.
// Gebruik een variabele verschuiving die start op 0 en telkens met 20 toeneemt.
// Zet elk volgend vierkant op (verschuiving, -verschuiving).
showGrid(50);
penUp();
var verschuiving = 0;
for(var i = 0; i < 4; i++) {
  goTo(verschuiving, -verschuiving);
  penDown();
  for(var zijde = 0; zijde < 4; zijde++) {
    moveForward(40);
    turnRight(90);
  }
  penUp();
  verschuiving = verschuiving + 20;
}