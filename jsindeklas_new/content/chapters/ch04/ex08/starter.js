// Teken eerst een groen vierkant met zijde 40 op de oorsprong.
// Ga daarna zonder extra lijn naar (140, 0),
// zet de penkleur op oranje en teken daar een cirkel met straal 25.
showGrid(50);
setPenColour('green');
var zijde = 40;
for(var i = 0; i < 4; i++) {
  ...
}
penUp();
goTo(140, 0);
penDown();
setPenColour('orange');
drawCircle(...);