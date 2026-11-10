# Lokaal nakijken · JavaScript in de Klas

Deze workflow ondersteunt twee gebundelde pdf-versies van **Toets Hoofdstuk 3: De Selectie**. Elke versie heeft een eigen correctiesleutel met een maximum van **45 punten**. De leerkracht beoordeelt de zichtbare antwoorden en bevestigt de punten. De workflow voert geen ingezonden JavaScript uit.

| PDF-versie | Revisie voor de correctiesleutel |
| --- | --- |
| Historische `toets_4.html`, vóór het uitvoervoorbeeld bij oefening 9 | `legacy-toets-4-741bede` |
| Huidige getimede toets, met het uitvoervoorbeeld bij oefening 9 | `toets-3-2026-01-09-v1` |

Gebruik voor de getimede versie een eigen correctiesleutel in de privémap `rubrics/`. Zet `revision` op `toets-3-2026-01-09-v1` en neem `prompt_source_blob` over uit `intake/timed-prompts.json` binnen de map `grading/`. Controleer de criteria voor het uitvoervoorbeeld bij oefening 9 en kalibreer de nieuwe sleutel volgens D02. Geef de bestandsnaam van de gekalibreerde sleutel mee vóór elke nakijkopdracht, bijvoorbeeld `python -m grading --rubric toets_3-getimed-v1.yaml prepare "$SUBMISSION"`. De historische sleutel blijft de standaardkeuze. Andere toetsen en examens hebben een eigen route en gekalibreerde sleutel nodig.

De getimede pdf gebruikt de laatste code als antwoordbewijs, ook als die versie nooit werd uitgevoerd. Uitvoer en canvas van eerdere code zijn als zodanig gelabeld en blijven raadpleegbaar in het origineel. De browsergegevens onderaan dienen als context voor de intake en worden uit de leerlingkopie verwijderd. Controleer de indiening met het schoolplatform en het originele bestand.

## Installatie

Gebruik Python 3.12 op macOS of Linux. Installeer de afhankelijkheden vóór je met privégegevens werkt. De opdrachten na de installatie werken lokaal en offline.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r grading/requirements.txt
python -m grading --help
```

## Inzendingen en dossiers

Gebruik de genegeerde map `grading/private/` of geef met `--workspace` een afzonderlijke privémap op. De submappen `submissions/`, `intake/`, `rubrics/`, `review/` en `reports/` horen bij dezelfde werkmap. Bewaar de oorspronkelijke pdf's in `submissions/` en zet één rij per verwachte inzending in `intake/manifest.json`. Gebruik de eigen roster- en klas-ID's en vergelijk de naam en klas zoals ze zichtbaar zijn op het voorblad. Houd de bronbestanden alleen-lezen en serveer de privéwerkmap nooit via een webserver.

```json
{
  "entries": [
    {
      "roster_id": "demo-pupil",
      "class_id": "demo-class",
      "name": "Demo Leerling",
      "class_name": "TEST",
      "assessment_id": "toets_3",
      "attempt_slot": "eerste",
      "source": "demo.pdf"
    }
  ]
}
```

Kies bij meerdere inzendingen eerst zelf de juiste poging en corrigeer het manifest. Voer vervolgens de intake opnieuw uit. Voor een aanvaarde inzending gebruik je de getoonde ID als `SUBMISSION` in de volgende opdrachten.

```sh
python -m grading intake
python -m grading prepare "$SUBMISSION"
python -m grading show "$SUBMISSION" --question toets_3-ex01
```

`prepare` controleert de bronhash, revisie, correctiesleutel en bijbehorende D02-kalibratie. Een gewijzigde pdf vraagt een nieuwe intake. Een gewijzigde sleutel vraagt een nieuwe versie met eigen kalibratie. Oude dossiers blijven beschikbaar in de private back-up. De intake geeft ook aan welke inzendingen ontbreken of in conflict zijn.

## Nakijken en goedkeuren

Open het originele bestand dat `show` aanwijst. Vergelijk identiteit, poging, code, uitvoer en de plaatsen in de pdf. Gebruik de rubric bij elke oefening. Een onduidelijke of onleesbare bron blijft open totdat er een bruikbare inzending is. Een door jou bevestigde lege antwoordzone krijgt nul volgens de sleutel.

Gebruik de revisie die `show` bij `revisie` toont. Na elke wijziging toont de CLI de nieuwe revisie. Een oud revisienummer wordt geweigerd.

```sh
python -m grading attest "$SUBMISSION" --revision 0 --actor "$TEACHER" --reason "Originele pdf en inzending gecontroleerd"
python -m grading marks "$SUBMISSION" --revision 1 --actor "$TEACHER" --reason "Bewijs per criterium gecontroleerd" --file "$MARKS" --checked all
python -m grading preview "$SUBMISSION"
```

Het privébestand `$MARKS` bevat een JSON-lijst. Je kunt eerst één criterium opslaan en later de lijst aanvullen. `--checked all` bevestigt de opgeloste criteria in dit bestand. Gebruik `--checked none` om een wijziging als concept te bewaren.

```json
[
  {
    "criterion_id": "toets_3-ex01.functioneel",
    "points": 0,
    "evidence_ids": ["toets_3-ex01:code"],
    "rationale": "Bij exact 60 verschijnt er geen korting."
  }
]
```

Sla desgewenst een sterkte en maximaal drie werkpunten op met `feedback`. De sterkte verwijst naar een bewijs-ID. Een werkpunt verwijst naar een criterium met een bevestigd puntenverlies. Maak de omschrijving en verbetering kort en leerlinggericht. Deze teksten komen op de feedbackkaart. Persoonlijke notities horen in de beoordelingsreden.

```json
{
  "strength": {"text": "Je bouwt twee duidelijke takken op.", "evidence_id": "toets_3-ex02:code"},
  "priorities": [
    {
      "criterion_id": "toets_3-ex01.functioneel",
      "title": "Drempel van 60",
      "observation": "Bij exact 60 verschijnt er geen korting.",
      "correction": "Gebruik >= en probeer 59 en 60."
    }
  ]
}
```

```sh
python -m grading feedback "$SUBMISSION" --revision 2 --actor "$TEACHER" --reason "Werkpunt uit zichtbaar bewijs" --file "$FEEDBACK"
python -m grading approve "$SUBMISSION" --revision 3 --actor "$TEACHER" --reason "Alle criteria en het totaal nagekeken"
```

Goedkeuren kan zodra alle criteria zijn opgelost en nagekeken en de bronverklaring bij dezelfde inzending hoort. Een nieuwe wijziging vraagt opnieuw goedkeuring. De voorvertoningen blijven privé in `reports/preview/`.

## Lokaal vrijgeven en bewaren

Gebruik de huidige goedgekeurde revisie. Dit schrijft een complete set naar de privémap en toont het exacte pad naar de leerlingbestanden.

```sh
python -m grading release "$SUBMISSION" --revision 4
python -m grading overview
```

De drie leerlingbestanden zijn `puntenoverzicht.pdf`, `feedbackkaart.pdf` en `toets-met-feedback.pdf`. De laatste gebruikt afbeeldingen van de bronpagina's om technische voetregels en verborgen pdf-inhoud te verwijderen. Bewaar de oorspronkelijke, doorzoekbare bron apart. Het CSV-overzicht en de controlemanifesten staan onder `reports/teacher/`. Een status `stale` betekent dat een eerder bewaarde set bij een andere beoordeling, bron of rapportlay-out hoort. Controleer de huidige inzending opnieuw voordat je een volgende versie vrijgeeft.

De feedbackkaart begint met de score, een overzicht van Functioneel, Leesbaar, Programmeerconcept en Wiskundeconcept, en de gekozen werkpunten. Bij puntenverlies of open punten volgt een overzicht per oefening met afzonderlijke tabellen voor aftrek en open criteria. Het losse puntenoverzicht toont dezelfde rubriekscores en alle criteria per oefening. Een nieuwe rapportlay-out krijgt een eigen uitvoerversie. Maak opnieuw een voorvertoning of geef dezelfde goedgekeurde beoordelingsrevisie opnieuw lokaal vrij om die lay-out te gebruiken.

Maak een besloten back-up van de volledige werkmap. Daarin zitten het manifest, de originele pdf's, de sleutel met kalibratie, de onveranderde basisdossiers, de beoordelingsgeschiedenis en de uitvoerversies. Herstel die onderdelen samen. Na een mislukte vrijgave blijft de vorige complete set bewaard. Herhaal de opdracht voor dezelfde revisie zodra de fout is opgelost. De workflow stuurt geen bestanden door.

## Synthetische start

Gebruik dit om de workflow uit te proberen met een fictieve inzending, sleutel en scorelijst. Voer de opdrachten uit in de projectmap.

```sh
demo_parent="$(mktemp -d)"
demo_workspace="$demo_parent/demo"
python -m tests.grading.demo "$demo_workspace"
python -m grading --workspace "$demo_workspace" --rubric demo.yaml intake
```

Gebruik voor alle volgende demo-opdrachten dezelfde opties `--workspace "$demo_workspace" --rubric demo.yaml` vóór de naam van de opdracht. De fictieve markeringen staan in `intake/demo-marks.json` binnen de demowerkmap.

De geautomatiseerde proef doorloopt deze opdrachten met een fictieve leerkracht en leerling.

```sh
python -m unittest tests.grading.test_workflow -v
for suite in intake evidence scoring proposals review_store reviewer reports release; do
  python -m unittest discover -s "tests/grading/$suite" -v || break
done
```
