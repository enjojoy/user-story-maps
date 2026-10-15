# Generated files

Everything here is produced from `../stories.yaml` by `storymap.py build`. **Do not edit these files by hand - your changes are overwritten.**

| File | What it is |
|---|---|
| `story-map.html` | Single-file viewer: architecture tab, click a screen to enlarge, filter by status / persona / topic, search. Open in any browser. |
| `one-pager.pdf` | One-page A3 overview (also `one-pager.png`): status counts, topic table, architecture, top gaps, all screens. |
| `architecture.png` | Architecture by topic: screens (in device frames) grouped in coloured topic swimlanes, cross-topic arrows highlighted. |
| `overview.png` | How the flows connect, with status counts. |
| `flows/<flow>.png` | One diagram per flow: real screenshots in device frames as nodes, a status badge under each, arrows labelled with the action. |
| `flow-map.png` | All flows in one big image. |
| `story-map.md` | Story map table + Mermaid diagrams (render directly on GitHub). |
| `user-stories.md / .csv` | Every story with persona, screens, status, where it lives, verified-how, notes. |
| `gaps-and-risks.md` | Gaps and risks ordered by severity. |
| `mermaid/architecture.mmd, topics.mmd` | Topic architecture as Mermaid (subgraphs per topic); also embedded in `story-map.md`. |
| `mermaid/*.mmd` | Mermaid sources (edit nothing here; they are regenerated). |
| `thumbs/*.png` | Framed device images (transparent PNG) that Graphviz draws as node pictures. |
| `dot/*.dot` | Graphviz sources (only when Graphviz is installed). |
