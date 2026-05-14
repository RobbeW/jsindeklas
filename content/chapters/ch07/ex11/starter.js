// Teken vier vierkanten naast elkaar met zijde 30.
// Kies in elke lus eerst een variabele lijnkleur:
// even teller = rood, oneven teller = blauw.
// Als de kleur rood is, zet lijndikte op 5. Anders op 2.
showGrid(50);
penUp();
for(var i = 0; i < 4; i++) {
  goTo(i * 60, 0);
  var lijnkleur = ...;
  setPenColour(lijnkleur);
  if(lijnkleur === 'red') {
    setLineWidth(...);
  } else {
    setLineWidth(...);
  }
  penDown();
  for(var zijde = 0; zijde < 4; zijde++) {
    moveForward(30);
    turnRight(90);
  }
  penUp();
}