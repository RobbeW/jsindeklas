# JavaScript in de Klas

Auteur: Robbe Wulgaert - AI in de Klas - [robbewulgaert.be](https://www.robbewulgaert.be)
(c) 2026 Robbe Wulgaert

Demo: [klik hier](https://robbew.github.io/jsindeklas/) of download de volledige code en publiceer via GitHub Pages of een lokale webserver.

## Doel

Deze webapplicatie stelt leerlingen van 12-14 jaar in staat om:

* Op een laagdrempelige, visuele manier kennis te maken met JavaScript-programmeren.
* Turtle Graphics-opdrachten stap voor stap uit te voeren in een intuitieve webomgeving.
* Direct feedback te krijgen op hun code: groene/rode voortgang, automatische controle van hun uitvoer en testcasefeedback.
* Duidelijke, Nederlandstalige foutmeldingen te zien bij codefouten.
* Hun voortgang en werk automatisch lokaal te bewaren, zonder account of cloud.
* Eenvoudig alles te exporteren naar PDF, inclusief feedbackrubriek voor de leerkracht.

## Vereisten

* Geen installatie nodig wanneer je de gepubliceerde GitHub Pages-versie gebruikt.

### Software & Browser

* Google Chrome of een moderne Chromium/Edge-browser voor de beste compatibiliteit.
* Voor lokaal testen gebruik je best een eenvoudige lokale webserver.
* Open de app niet via `file://`, omdat de leeromgeving haar JSON-bestanden rechtstreeks inlaadt.

### Installatie en Gebruik

#### 1. Downloaden en starten

* Download of clone deze repository naar jouw eigen toestel, of
* gebruik de link naar de webpagina die bij deze repo hoort.
* Publiceer je fork via GitHub Pages of open de map via een lokale webserver.

#### 2. Aan de slag

* Selecteer een oefening via de navigatiebalk bovenaan.
* Schrijf code in de ingebouwde editor; elke oefening bevat startcode als scaffolding.
* Klik op `Uitvoeren`: zie het resultaat direct in het canvas en in de console.
* Voortgangsbalk: zie per oefening of je oplossing overeenkomt met de verwachte controle.
* Foutmeldingen: onbegrijpelijke Engelse errors? Geen zorgen, je krijgt beperkte Nederlandstalige uitleg als beginner.
* Formularium: klik op het `?`-icoon rechtsonder voor het overzicht van alle commando's en kleurmogelijkheden.

#### 3. PDF-export

Klik op `Exporteren naar PDF` voor een rapport inclusief code, console-output, canvas, en feedbacktabellen voor de leerkracht.

### Zelf oefeningen aanpassen?

Alle oefeningen staan nu als losse contentbestanden in `content/`. Je kan ze aanpassen, uitbreiden of nieuwe oefeningen toevoegen zonder in een grote monolithische oefenlijst te werken.

De structuur is bewust eenvoudig:

```text
content/catalog.json
content/chapters/chXX/chapter.json
content/chapters/chXX/exNN/exercise.json
content/chapters/chXX/exNN/starter.js
content/chapters/chXX/exNN/tests.json
```

Er is ook een browsertool om nieuwe oefeningen aan te maken:

```text
tools/exercise-author.html
```

Voor leerkrachten is er een aparte handleiding:

```text
TEACHER_AUTHORING.md
```

Alles is open en transparant. Je kan de hele cursus naar eigen wens aanpassen.

Opgelet: dit project werd geschreven vanuit mijn eigen lespraktijk, waar programmeren en computationeel denken een beperkter deel uitmaakt van het curriculum. Grotere inhoudelijke aanpassingen voor jouw specifieke context kunnen dus nodig zijn.

### Vragen, bugs of feedback?

Voor alle vragen, opmerkingen, bug reports of suggesties:
Join de Discord-server: [Klik hier!](https://discord.com/invite/U77FKEQfC6)

## Leerkrachtentips

De beoordelingsrubriek in het PDF-rapport biedt ruimte voor scores op:

* Functioneel
* Leesbaar
* Programmeerconcept
* Wiskundeconcept
* Creativiteit

Laat leerlingen hun rapport indienen als bewijs.

Bovenstaande criteria voor evaluatie zijn gebaseerd op onderzoek door Tom Neutens uit 2022:
[UGent-publicatie](https://biblio.ugent.be/publication/8748195)

## Licentie & Copyright

(c) 2026 Robbe Wulgaert, AI in de Klas, robbewulgaert.be
Alle rechten voorbehouden.

Gebruik in eigen klas of eigen onderwijscontext is toegelaten mits duidelijke en expliciete naamsvermelding:

```text
Robbe Wulgaert, AI in de Klas, robbewulgaert.be
```

Herdistributie of herverpakking buiten die context gebeurt best alleen met toestemming van de auteur.

## Derdepartijbronnen

De live app gebruikt ook enkele externe of meegeleverde componenten:

* `rgbcolor.js`: RGBColor parser door Stoyan Stefanov, met MIT-licentieheader in het bestand zelf.
* CodeMirror 5: editorbibliotheek, geladen via jsDelivr CDN.
* jsPDF: PDF-exportbibliotheek, geladen via jsDelivr CDN.
* html2canvas: canvas/screenshotbibliotheek voor export, geladen via jsDelivr CDN.
* Google Fonts / Roboto: extern lettertype in de HTML-pagina's.

## Vragen of feedback? Contacteer Robbe

Voor alle vragen, opmerkingen, bug reports of suggesties:
Join de Discord-server: [Klik hier!](https://discord.com/invite/U77FKEQfC6)
