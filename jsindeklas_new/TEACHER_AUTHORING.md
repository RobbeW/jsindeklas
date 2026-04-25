# Leerkrachtenhandleiding

Deze handleiding is bedoeld voor leerkrachten die een GitHub-fork van JavaScript in de Klas gebruiken en die via GitHub Pages nieuwe oefeningen willen toevoegen.

## Kernidee

Je hoeft geen lokale server op te zetten.
Je hoeft geen build-script uit te voeren.
Je werkt rechtstreeks via:

```text
https://jouw-gebruikersnaam.github.io/jouw-repo/tools/exercise-author.html
```

## Stappen

1. Fork de repository op GitHub.
2. Activeer GitHub Pages op je fork.
3. Open de oefeningmaker op je GitHub Pages-site.
4. Kies een bestaand hoofdstuk of maak een nieuw hoofdstuk aan.
5. Vul titel, oefennummer, startcode en testcases in.
6. Controleer de preview.
7. Voeg de oefening toe aan het ZIP-pakket.
8. Download het GitHub-upload-ZIP.
9. Pak het ZIP-bestand uit.
10. Upload de inhoud naar exact dezelfde mappen in je GitHub-fork.
11. Wacht tot GitHub Pages opnieuw gepubliceerd is.
12. Test daarna minstens een correcte en een foute oplossing.

## Wat de oefeningmaker oplevert

Voor een nieuwe oefening in hoofdstuk 2, bijvoorbeeld `ex14`, bevat het pakket typisch:

```text
content/chapters/ch02/chapter.json
content/chapters/ch02/ex14/exercise.json
content/chapters/ch02/ex14/starter.js
content/chapters/ch02/ex14/tests.json
UPLOAD_INSTRUCTIONS.md
```

Bij een nieuw hoofdstuk krijg je ook een aangepast `content/catalog.json`.

## Testcases

Een eenvoudige outputtest:

```json
[
  {
    "label": "Voorbeeld",
    "stdout": "Hallo wereld"
  }
]
```

Een testcase met `ask()`-invoer:

```json
[
  {
    "label": "Naam vragen",
    "inputs": ["Ada"],
    "stdout": "Hallo Ada"
  }
]
```

Een canvas-test:

```json
[
  {
    "label": "Vierkant",
    "canvas": {
      "lineCount": 4,
      "lineLengths": [50, 50, 50, 50],
      "closedShape": true
    }
  }
]
```

## Manuele oefeningen

Gebruik `manual` voor open opdrachten zonder uniek juist antwoord. In dat geval wordt geen `tests.json` meegestuurd en rekent de app de oefening niet automatisch juist of fout.

## Publicatie-opmerking

De app leest de oefenbestanden rechtstreeks uit:

```text
content/catalog.json
content/chapters/chXX/chapter.json
content/chapters/chXX/exNN/exercise.json
content/chapters/chXX/exNN/starter.js
content/chapters/chXX/exNN/tests.json
```

Daarom is GitHub Pages voldoende. Open de app niet via `file://`.

## Copyright en bronvermelding

Gebruik bij publicatie of afgeleid materiaal bij voorkeur deze vermelding:

```text
Robbe Wulgaert, AI in de Klas, robbewulgaert.be
```

De projectcode en didactische uitwerking blijven auteurswerk van Robbe Wulgaert. Gebruik in eigen onderwijscontext is toegelaten mits duidelijke bronvermelding.
