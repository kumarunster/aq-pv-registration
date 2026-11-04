# Analyse: e-netz Südhessen

Stand: 2. November 2026. Einstieg: `https://www.e-netz-suedhessen.de/installateurportal/`.

## Technik und Login

Die Startseite enthält ein Frameset. Die eigentliche Anwendung liegt unter `/installateurportal/secure/portalaufgabe.jsf`. Es handelt sich um eine serverseitig gerenderte JavaServer-Faces-Anwendung; beobachtete Version: **2.10.6**, erstellt am 23. Oktober 2026.

Loginablauf:

1. GET auf den tatsächlichen Portalpfad, Session-Cookie übernehmen.
2. Loginformular `form#login` und seine versteckten Werte lesen.
3. Die veröffentlichte JavaScript-Funktion setzt das Formularziel auf `j_security_check`.
4. POST an `/installateurportal/secure/j_security_check` mit `j_username`, `j_password` und den ursprünglichen versteckten Feldern.
5. Cookies weiterverwenden; eingeloggten Kontonamen und das Fehlen des Passwortformulars prüfen.

Für diese Abfragen ist keine JavaScript-Ausführung erforderlich. Die Anwendung verwendet jedoch JSF-ViewState und transaktionsbezogene Felder. Ein generischer Formular-POST ohne diese Zustände ist keine zuverlässige Schreibschnittstelle.

## Vorgeschaltete Hinweise

Beim ersten Login wurden Status-/Aufgaben-/Firmen-/Meldungsseiten auf „Aktuelle Informationen“ umgeleitet. Zwei Hinweise waren zu bestätigen. Der Adapter hat sie nicht automatisch bestätigt. Nach Bestätigung durch den Kontoinhaber wurden die zuvor blockierten Abfragen wiederholt; sie funktionierten.

`POST /session` prüft deshalb die tatsächliche Erreichbarkeit der Statusseite und meldet bei einer solchen Umleitung `authenticated=true`, `action_required=true`. Listen-/Detailfunktionen liefern in diesem Fall HTTP 409. Das Muster bleibt für künftig hinzukommende Pflichtinformationen erhalten.

Die Hinweise-API liefert nur die erste Tabellenseite und kennzeichnet diese ausdrücklich als unvollständig. Eine Detailansicht markiert nichts als gelesen.

## Sichtbare Navigation

- **Neuigkeiten**
  - Aktuelle Informationen
  - Aufgaben
- **Firmenverwaltung**
  - Kennwort ändern
  - Firmenstammdaten
  - Zulassung
  - Benutzerverwaltung
  - Installateurausweis
- **Meldungsverwaltung**
  - Meldung abgeben
  - Meldungsstatus
  - Meldung aus Kundenportal übernehmen
- **Links**
  - Technische Anschlussbedingungen Strom, Gas, Wasser
  - Anleitung Bezugs-/Liefermeldung als PDF
  - Anleitung Bezugs-/Liefermeldung als Video
- Abmelden sowie Impressum, Datenschutz, Nutzungsbedingungen und Ansprechpartner.

Der Menü-Endpunkt gibt die direkt sichtbaren authentifizierten Navigationslinks zurück. Nicht jede darin genannte Funktion ist bereits als Schreib-API implementiert.

## Meldungsstatus

Nach Freigabe lieferte das Konto zwei Meldungen, darunter einen Entwurf („in Vorbereitung“) und eine Meldung in Bearbeitung. Typ: Bezugs-/Liefermeldung; Sparte Strom. Kundennamen und Adressen werden hier nicht vervielfältigt.

Sichtbare Filter:

- Status: In Bearbeitung durch e-netz Südhessen, Anmeldung freigegeben, abgewiesen, abgeschlossen, in Vorbereitung, storniert, fertiggemeldet, in Korrektur, Netzverträglichkeit wird geprüft.
- Sparte: Strom, Gas, Wasser.
- Kundenportal: alle/ja/nein.
- Weitere Suchfelder u. a. Baustelle, Ort, Datum und Anschlussobjekt.

Spalten enthalten Status, Ausführung, AO-Nr., Baustellenbezeichnung, Ort, Datum, Sparte, Kundenportal und Zeilenaktionen.

Sichtbare Aktionen: Details, je nach Zustand Kopieren, Drucken, Löschen oder Stornieren. **Ausgeführt wurden nur GET-Detailabfragen.** Die API stellt die Schreibaktionen nicht bereit.

Die Liste liest `formId:auswertungenTableId:table`. Weitere Seiten werden durch den konkret ermittelten JSF-Weiter-Submit aufgerufen. Nur dieser Submit und der unveränderte Formular-/Filterzustand werden gesendet, keine Zeilenaktion. Wiederholte Seiten/IDs oder eine Überschreitung des Traversierungslimits führen zu einem Fehler. Das Live-Konto hat eine Seite; zusätzliche Seiten sind mit synthetischen JSF-Antworten getestet.

## Details und Einstiegsformular

Der Details-Link enthält u. a. Meldungs-, Baustellen- und Meldungsdetail-ID. Der Adapter verwendet ausschließlich den im eigenen Statusdatensatz enthaltenen „Details“-Link und keinen vom API-Aufrufer übergebenen URL. Ein Link mit Löschaktion wird abgelehnt.

Die geprüfte Detailansicht enthielt 12 sichtbare Eingabefelder, u. a. Sparte, Adresse/Flurstück, Ausführung, Detailbeschreibung und Bemerkung. Die API gibt Werte/Optionen des **aktuell gerenderten Reiters** zurück und kennzeichnet `complete=false`. Andere Reiter und davon abhängige PV-Technikfelder sind noch nicht vollständig untersucht.

„Meldung abgeben“ zeigt vor dem Anlegen die Auswahl **Strom, Gas, Wasser** und die Schaltfläche **Anlegen**. `/registration-options` liest diesen Einstieg. Es drückt nicht „Anlegen“ und erzeugt keine Meldung.

Zusätzlich angesehen:

- Firmenstammdaten: Unternehmensdaten, Firmeninhaber, Plombenverträge; Bearbeiten-Schaltfläche.
- Zulassung: Installateurart, Heimatnetzbetreiber/Ausweis/Gültigkeit, Unterlagen und verantwortliche Leiter; Zulassung beantragen/verlängern.
- Aufgaben: aktuell keine sichtbaren Aufgabeneinträge. Die API kennzeichnet die Abfrage als Erstseite.

Firmen-/Zulassungsänderungen, Benutzerverwaltung und Passwortwechsel sind nicht implementiert.

## Nächster Ausbauschritt

Eine kontrollierte Erstellung eines Testentwurfs samt Untersuchungen der Bezugs-/Liefermeldung für Strom, der Reiterwechsel, Erzeugungsanlagen-/Speicherdaten und Dateiuploads. Dafür müssen CSRF/ViewState, Transaktions-IDs, Speichern/Weiter und Finalisierung gesondert erfasst werden. Die bisherige Leseintegration darf nicht als fertige Anmelde-/Absendeautomatik verstanden werden.
