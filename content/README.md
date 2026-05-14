# Cursusinhoud

Deze map is de bron van waarheid voor de cursusinhoud. De live app leest deze bestanden rechtstreeks in op GitHub Pages.

## Structuur

```text
content/
  catalog.json
  chapters/
    ch01/
      chapter.json
      ex01/
        exercise.json
        starter.js
        tests.json
```

## Regels

- `catalog.json` bepaalt welke hoofdstukken zichtbaar zijn en in welke volgorde.
- `chapter.json` bepaalt welke oefeningen in een hoofdstuk zitten.
- `exercise.json` bevat metadata zoals titel en evaluatiemodus.
- `starter.js` bevat de startcode voor de editor.
- `tests.json` bevat de testcasegegevens als gewone JSON.

## Onderhoud

Nieuwe oefeningen maak je het makkelijkst via `tools/exercise-author.html`.

Meer uitleg voor leerkrachten staat in:

- `../TEACHER_AUTHORING.md`
- `../README.md`

## Opmerking

De cursus wordt niet meer uit een gegenereerde fallbackbundel geladen. De inhoud in deze map is dus de actuele runtime-inhoud van het platform.
