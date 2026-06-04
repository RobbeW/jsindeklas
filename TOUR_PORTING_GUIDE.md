# Parnassos tour porting guide

Deze nota beschrijft hoe de rondleiding in `00-Inleiding` is opgebouwd. Het doel is niet alleen documenteren wat er in Parnassos staat, maar vooral: kunnen we dit later opnieuw gebruiken in Delphi, Papyros-projecten of andere lesplatformen?

## Wat werd gebouwd?

Voor Parnassos is een eerste theorie-element gemaakt dat de leerling stap voor stap door de leeromgeving leidt. De leerling ziet een ingevulde Python-oefening als achtergrond en krijgt telkens een paarse markering rond een belangrijk stuk van de interface:

- de voortgang bovenaan;
- de opdracht of theorie rechts;
- de code-editor links;
- de knop om code uit te voeren;
- de uitvoer;
- het invoerveld bij `input()`;
- het menu;
- het formularium.

Dit is bewust geen gewone oefening. De leerling hoeft hier geen code te schrijven. De rondleiding leert eerst de omgeving lezen.

## Nieuwe contentstructuur

De tour staat als gewoon content-item in de Parnassos-map:

```text
content/
  00-Inleiding/
    01-Wegwijs in Parnassos/
      00-Rondleiding Door De Leeromgeving/
        config.json
        description/
          description.nl.md
        starter/
          starter.py
        theory/
          theory.json
```

### `config.json`

De tour gebruikt hetzelfde mechanisme als andere theorie-items, maar met een extra subtype:

```json
{
  "title": "Rondleiding door de leeromgeving",
  "type": "theory",
  "theoryKind": "tour"
}
```

Belangrijk:

- `type: "theory"` zorgt dat het item niet als gewone programmeeroefening behandeld wordt.
- `theoryKind: "tour"` vertelt de shell dat er geen standaard theorieblok moet worden getoond, maar de interactieve rondleiding.

### `description/description.nl.md`

De beschrijving blijft kort. Ze zet de context, maar probeert niet de hele UI uit te leggen. Dat werk doet de tour zelf.

```md
## Rondleiding

Welkom in Parnassos.

Deze korte rondleiding toont waar je de opdracht leest, waar je code schrijft, waar je uitvoer ziet en hoe je naar andere onderdelen navigeert.

De code links is al ingevuld. Je hoeft hier nog niets op te lossen.
```

### `starter/starter.py`

De startercode is de achtergrond van de rondleiding. In Parnassos is gekozen voor een ingevulde variant van een oefening uit hoofdstuk 1. Daardoor ziet de leerling meteen een echte Parnassos-opdracht met herkenbare blokken:

```python
# Invoer

centrum_lat = 51.0543
centrum_lon = 3.7250

plaatsen = [
    ["Gent-Sint-Pieters", 51.0362, 3.7102],
    ["Gravensteen", 51.0573, 3.7208],
    ["Portus Ganda", 51.0559, 3.7346],
]


# Verwerking

for plaats in plaatsen:
    naam = plaats[0]
    lat = plaats[1]
    lon = plaats[2]

    if lat > centrum_lat:
        noord_zuid = "noord"
    else:
        noord_zuid = "zuid"

    if lon > centrum_lon:
        oost_west = "oost"
    else:
        oost_west = "west"


    # Uitvoer

    print(naam + ":", noord_zuid + oost_west)
```

Voor een ander project kan die startercode gewoon vervangen worden door een ingevulde oefening uit dat project.

### `theory/theory.json`

De eigenlijke rondleiding is data. Elke stap wijst naar een CSS-selector in de interface.

```json
{
  "title": "Wegwijs in Parnassos",
  "intro": "Volg de paarse markering. Je kan de rondleiding stap voor stap doorlopen.",
  "steps": [
    {
      "selector": "#exercise-progress",
      "title": "Voortgang",
      "text": "Bovenaan zie je de onderdelen van het huidige subhoofdstuk. Een paars rondje is theorie. Een groen rondje is klaar."
    }
  ]
}
```

Elke stap heeft drie velden:

- `selector`: het UI-element dat gemarkeerd moet worden;
- `title`: de korte titel in het tourkaartje;
- `text`: de uitleg voor de leerling.

Als een selector niet gevonden wordt, valt de tour terug op het opdrachtpaneel. Dat voorkomt dat de rondleiding volledig breekt wanneer een UI-element in een ander project ontbreekt.

## Aanpassing aan de catalogus

De catalogusgenerator is aangepast zodat `00-Inleiding` echt als eerste hoofdstuk verschijnt. De expliciete hoofdstukvolgorde staat in `tools/build-catalog.mjs`.

```js
includeChapters: [
  "00-Inleiding",
  "00-Hoofdstuk 1 - Gent als dataset",
  "01-Hoofdstuk 2 - Gent op de kaart",
],
```

Daarnaast filtert de generator nu op mappen met een volgnummer. Daardoor worden losse oude bestanden in `00-Inleiding` niet per ongeluk als oefeningen gelezen.

Bij porting naar een ander project moet je nakijken:

- staat het introductiehoofdstuk in de catalogusconfiguratie?
- herkent de generator theorie-items?
- wordt `theoryKind` meegenomen in de catalogus?
- worden submappen zonder volgnummer genegeerd?

## Aanpassing in `app.js`

De shell kreeg een kleine tourlaag bovenop het bestaande theorie-renderen.

### State en cleanup

Er is een actieve cleanupfunctie toegevoegd:

```js
activeTourCleanup: null
```

Bij het laden van een nieuw item roept de app `clearActiveTour()` aan. Dat verwijdert bestaande overlays en event listeners. Dit is belangrijk: zonder cleanup kan een oude markering blijven hangen wanneer een leerling naar een andere oefening gaat.

### Theorie-item herkennen

In de theorie-rendering wordt nu gecontroleerd of het item een tour is:

```js
if (exercise.theoryKind === "tour" && exercise.theoryPath) {
  const tour = await fetchJsonFile(exercise.theoryPath);
  renderTheoryTour(ui.assignmentMarkdown, exercise, tour);
  return;
}
```

Voor andere theorie-items blijft de bestaande flow werken.

### Tour renderen

De functie `renderTheoryTour(container, exercise, tour)` doet vier dingen:

1. Ze toont een korte intro en een knop `Start rondleiding`.
2. Ze maakt een overlay met een highlight en een callout.
3. Ze positioneert de highlight rond het gekozen UI-element.
4. Ze markeert de theorie als voltooid wanneer de leerling de laatste stap afrondt.

De tour start in Parnassos niet automatisch. Dat is bewust: de gewone loading screen moet eerst rustig klaar zijn. Daarna kiest de leerling zelf `Start rondleiding`.

De startknop krijgt alleen een korte puls wanneer het theorie-item nog niet voltooid is. Zodra de leerling de laatste tourstap afrondt, wordt de bestaande theorie-status op `success` gezet en verandert de knop naar `Rondleiding opnieuw starten`.

Voor een ander project zijn dit de nuttige opties:

- manueel starten: beste keuze wanneer het platform een eigen loading screen heeft;
- subtiel laten pulseren: goed voor eerste gebruikers zonder extra modal;
- opnieuw starten: altijd nuttig;
- automatisch starten: alleen gebruiken wanneer de shell al volledig geladen en rustig is.

### Selectors

De huidige Parnassos-tour gebruikt deze selectors:

```text
#exercise-progress
#assignment-markdown
.CodeMirror
#run-code
#console-output
.runtime-input-wrap
#menu-tab
#help-btn
```

Bij porting zijn selectors de belangrijkste koppeling tussen tourdata en platform. Als Delphi of een ander project andere IDs of classes gebruikt, moet je alleen de selectors in `theory.json` aanpassen, zolang de renderer zelf generiek blijft.

## Aanpassing in `styles.css`

De tour gebruikt eigen CSS-klassen:

```text
.tour-intro
.tour-overlay
.tour-highlight
.tour-callout
.tour-status
.tour-controls
```

De overlay ligt boven de volledige pagina met `position: fixed`. De highlight krijgt een paarse rand en een zachte donkere laag rond het doelgebied. Het calloutkaartje heeft gewone knoppen voor `Vorige`, `Volgende` en `Overslaan`.

Er is ook rekening gehouden met `prefers-reduced-motion`. Wie minder animatie wil, krijgt geen vloeiende verschuivingen.

Bij porting moet vooral dit mee:

- de overlay moet boven de app liggen;
- de callout moet klikbaar blijven;
- de rest van de overlay mag geen knoppen blokkeren;
- de highlight moet opnieuw gepositioneerd worden bij scrollen en resizen;
- de kleur moet naar de branding van het project worden aangepast.

## Werking tijdens runtime

Wanneer de leerling het tour-item opent, gebeurt dit:

1. De shell laadt het item uit de catalogus.
2. De beschrijving verschijnt rechts.
3. De startercode verschijnt in de editor.
4. `theory/theory.json` wordt opgehaald.
5. De tourintro wordt toegevoegd aan het opdrachtpaneel.
6. De leerling klikt op `Start rondleiding`.
7. Per stap zoekt de shell het element via `document.querySelector()`.
8. De highlight wordt over het element gelegd.
9. Het calloutkaartje wordt naast of onder het element geplaatst.
10. Bij de laatste stap wordt het theorie-item als gelezen gemarkeerd.

De tour sluit het menu voor de start. Dat maakt de beginsituatie voorspelbaar.

## Porting naar een ander project

Gebruik deze checklist.

### 1. Kies het juiste contenttype

Maak van de rondleiding een theorie-item, geen oefening. De leerling moet hier niet slagen of falen op code.

Minimale config:

```json
{
  "title": "Rondleiding door de leeromgeving",
  "type": "theory",
  "theoryKind": "tour"
}
```

### 2. Kies een realistische achtergrond

Gebruik een ingevulde oefening uit het project zelf. Dat werkt beter dan een lege editor, omdat de tour dan meteen toont hoe een echte opdracht eruitziet.

Goede achtergrondcode:

- is kort;
- gebruikt herkenbare commentaarblokken;
- bevat invoer, verwerking en uitvoer;
- heeft geen fouten;
- vraagt geen lange interactie van de leerling.

### 3. Schrijf de tour als data

Maak een `theory/theory.json` met stappen. Vermijd uitleg die te sterk afhangt van exacte schermposities zoals "links boven" of "helemaal rechts". Gebruik liever functionele taal:

- "Hier lees je de opdracht."
- "Hier schrijf je code."
- "Hier verschijnt de uitvoer."
- "Met deze knop voer je je code uit."

Zo blijft de tekst bruikbaar op laptop, beamer en kleiner scherm.

### 4. Controleer de selectors

Open het platform in de browser en controleer of elke selector bestaat. Gebruik waar mogelijk stabiele IDs. Classes zoals `.CodeMirror` kunnen nodig zijn wanneer een component geen eigen ID heeft, maar IDs zijn betrouwbaarder.

Als een selector in meerdere elementen voorkomt, pakt `querySelector()` het eerste element. Dat kan fout zijn. Maak dan liever een specifieker selectorpad.

### 5. Voeg de renderer toe

In een Papyros-achtige shell zijn dit de nodige hooks:

- item laden;
- theorie-item herkennen;
- `theory.json` ophalen;
- overlay maken;
- target zoeken;
- highlight positioneren;
- callout positioneren;
- cleanup bij navigatie;
- voortgang markeren bij afronden.

Hou de renderer generiek. Projectspecifieke tekst hoort in `theory.json`, niet in `app.js`.

### 6. Voeg CSS toe

Neem de tourklassen over en pas kleuren, radius en schaduwen aan aan de projectbranding. Voor Parnassos is paars de primaire tourkleur.

### 7. Test met cachebuster

Bij Parnassos moest zowel `app.js` als `styles.css` een nieuwe versie krijgen. Anders werd de nieuwe JavaScript wel geladen, maar de tour-CSS niet. Dan lijkt het alsof de tour niet werkt, terwijl de DOM-elementen wel bestaan.

Controleer dus altijd:

- is de nieuwe `app.js` geladen?
- is de nieuwe `styles.css` geladen?
- staat de nieuwe catalogus online?
- verwijst `platform.html` naar de juiste versies?

## Valkuilen uit deze implementatie

### De CSS-cache kan misleiden

Tijdens het testen verschenen `.tour-highlight` en `.tour-callout` wel in de DOM, maar niet zichtbaar op het scherm. De oorzaak was een oude stylesheet in de browsercache. De oplossing was de stylesheetversie in `platform.html` verhogen.

### De tour mag niet blijven hangen

Een overlay met event listeners moet altijd een cleanup hebben. Anders kan een vorige tour op een volgende oefening blijven reageren.

### Selectors zijn kwetsbaar

Een tour is zo stabiel als de selectors waarop ze steunt. Wanneer de UI later hertekend wordt, moet `theory.json` opnieuw nagekeken worden.

### Een rondleiding is geen leerinhoud

De tour mag kort blijven. Ze moet leerlingen oriënteren in de omgeving, niet de inhoud van Python of GIS uitleggen. Daarvoor zijn oefeningen, theorie B-elementen en Colab-notebooks beter geschikt.

### Automatisch starten is meestal te vroeg

Parnassos gebruikt een loading screen terwijl Papyros en de workers laden. Een tour die automatisch start, kan dan voor de loading layer springen. Daarom start de Parnassos-tour alleen via de knop. Voor eerste gebruikers pulseert die knop kort zolang het item nog niet als gelezen gemarkeerd is.

## Aanbevolen standaard voor toekomstige projecten

Voor Delphi, Parnassos en latere shells zou dit een vaste conventie kunnen worden:

```text
00-Inleiding/
  01-Wegwijs in [projectnaam]/
    00-Rondleiding Door De Leeromgeving/
      config.json
      description/
        description.nl.md
      starter/
        starter.py
      theory/
        theory.json
```

Met deze vaste structuur kan de tourrenderer in meerdere projecten dezelfde code gebruiken. Alleen de startercode, tekst, selectors en branding verschillen.

## Snelle porting-checklist

- Maak een introductiehoofdstuk aan.
- Voeg een theorie-item met `theoryKind: "tour"` toe.
- Gebruik een ingevulde starter als achtergrond.
- Schrijf de stappen in `theory/theory.json`.
- Controleer alle selectors in de doelinterface.
- Voeg of kopieer de tourrenderer in `app.js`.
- Voeg of kopieer de tour-CSS.
- Verhoog de cacheversie van `app.js`, `styles.css` en eventueel de catalogus.
- Bouw de catalogus opnieuw.
- Test lokaal en op GitHub Pages.
- Controleer mobiel of smal scherm.
- Controleer of afronden de theorie als gelezen markeert.

## Mogelijke uitbreidingen

Later kunnen we deze tourlaag uitbreiden met:

- meerdere tours per platform;
- een tour die alleen bij het eerste bezoek automatisch start;
- een knop `Rondleiding opnieuw starten` in het menu;
- voortgang per tourstap in local storage;
- screenshots of korte animaties in het calloutkaartje;
- aparte tekst voor leerling en leerkracht;
- vertalingen per taalmap.

Voor nu is de Parnassos-versie bewust eenvoudig gehouden: data in de contentmap, een kleine renderer in de shell, en CSS die de bestaande huisstijl volgt.
