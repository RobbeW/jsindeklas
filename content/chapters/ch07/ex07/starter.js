// Teken drie vierkanten naast elkaar met zijde 40.
// Gebruik in je lus deze kleuren op volgorde: rood, groen, blauw.
showGrid(50);
penUp();
for(var i = 0; i < 3; i++) {
  goTo(i * 70, 0);
  penDown();
  if(i === 0) {
    setPenColour(...);
  } else if(i === 1) {
    setPenColour(...);
  } else {
    setPenColour(...);
  }
  for(var zijde = 0; zijde < 4; zijde++) {
    moveForward(40);
    turnRight(90);
  }
  penUp();
}