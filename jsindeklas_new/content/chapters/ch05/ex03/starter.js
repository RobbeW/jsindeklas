// Vraag 5 keer een afstand aan de gebruiker en tel alles op.
// Toon op het einde: De totale afstand die ik heb afgelegd is: ... km.
// De afstanden zijn: 245.2km, 199.2km, 312km, 231km, 119.4km.

var totaal = 0;
for(var i = 1; i <= 5; i++){
  var afstand = parseFloat(ask('Geef de afstand van rit ' + i + ' in km:'));
...
console.log('De totale afstand die ik heb afgelegd is: ... km.');