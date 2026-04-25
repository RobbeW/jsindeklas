// Teken een spiraal: elke lijn wordt 10px langer dan de vorige.
showGrid(30);
var lengte = 10;
for(var i = 0; i < 8; i++) {
  moveForward(lengte);
  turnRight(45);
  ... 
}