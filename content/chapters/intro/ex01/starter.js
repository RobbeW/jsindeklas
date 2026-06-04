// Rondleiding: volledig ingevuld voorbeeld op basis van "Gekleurd Vierkant".
showGrid(50);
setPenColour('blue');

var zijde = 50;

for (var i = 0; i < 4; i++) {
  moveForward(zijde);
  turnRight(90);
}

console.log('Ik tekende een blauw vierkant met zijde ' + zijde + ' px.');
