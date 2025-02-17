# 🚀 Neue Automatische Releases

## ❓ Was ist zu beachten?

- **Commit-Nachrichten** weiterhin wie bisher schreiben.
- **PR-Titel** an den Release-Typ anpassen.  
  Dazu den entsprechenden Tag hinzufügen:
    - **#major**: Für Breaking Changes oder komplett neue Versionen.
    - **#minor**: Für das Hinzufügen neuer Features.
    - **#patch**: Für gefixte Bugs.

---

## 🛠️ Workflow

1. **Automatische Tag-Erstellung**  
   Nach jedem Merge in den `main`-Branch wird automatisch ein neuer Tag erstellt.

2. **Tägliche Prüfung um 20:00 Uhr**  
   Es wird geprüft, ob seit dem letzten Release Änderungen im `main`-Branch vorgenommen wurden:
    - Falls Änderungen vorhanden sind, wird ein neues Release erstellt.
    - Dieses Release basiert auf dem zuletzt erstellten Versions-Tag.

   > **Hinweis:** Manuell erstellte Tags können die Release-Version überschreiben, solange sie zeitlich aktueller sind
   als die automatisch generierten.

---

## 📄 Release-Inhalte

Ein Release besteht aus zwei Teilen:

1. **Automatische GitHub-Zusammenfassung**  
   Eine automatisch generierte Zusammenfassung der letzten Änderungen.
2. **Zusätzliche Notizen aus der Datei `additional-release-notes.txt`**
   > Markdown-Inhalte in dieser Datei werden korrekt verarbeitet.