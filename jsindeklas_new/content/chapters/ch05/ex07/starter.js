// Vraag 5 temperaturen op, tel telkens wanneer de temp. > 25°C.
// Toon 'Alarm: hittegolf!' als alle 5 temperaturen > 25, anders 'Geen hittegolf.'
// Je zal twee IF-Statements moeten gebruiken.

var alarmTeller = 0;
for(var i = 1; i <= 5; i++){
  var temp = parseFloat(ask('Geef temperatuur ' + i + ' in °C:'));
  ...
