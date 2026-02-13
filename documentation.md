# HTML Propagation Dotfiles

## What they are

Two dotfiles that control how `.html` files propagate (accumulate) upward through the folder tree. By default, all HTML files in child folders bubble up to their parents — so a parent node displays the combined HTML content of its entire subtree. These dotfiles let you control that behavior.

## The two dotfiles

### `.html_only_here`

Prevents this folder's HTML files from propagating to its parent. The folder itself still displays its accumulated HTML content (own files + children), but the parent will not include any of it.

Think of it as: "my HTML stays at this level only."

### `.html_stops_here`

Creates a hard boundary. Nothing below this folder propagates upward — not its own HTML files, and not any HTML from its children or descendants.

Think of it as: "no HTML passes through this ceiling."

## How to use

Place an empty file with the name `.html_only_here` or `.html_stops_here` in any directory. The file content doesn't matter — only its presence.

```bash
touch /path/to/folder/.html_only_here
touch /path/to/folder/.html_stops_here
```

## UI visualization

In both the tree view and breadcrumb labels, dots appear next to folder names:

- **Blue dot** — `.html_only_here` is present in this folder
- **Green dot** — `.html_stops_here` is present in this folder
- **White dots** (or colored if `COLORED_HTML_DOTS = True`) — each dot represents one HTML file accumulated at this node. The number of dots shows how many HTML files are visible when you click that folder. When `COLORED_HTML_DOTS` is enabled, each HTML file gets a deterministic random color based on its file path and the `SEED` value, so the same file always appears as the same color across all nodes it propagates through.

## Examples

Legend: `X` = .html_stops_here, `I` = .html_only_here, `O` = white dot (one per accumulated HTML file)

---

### Example 1 — No dotfiles (default behavior)

All HTML files propagate to the root.

```
└── root  O O O
    ├── about  O O
    │   ├── intro
    │   │   └── page.html
    │   └── team
    │       └── page.html
    └── contact
        └── page.html
```

---

### Example 2 — `.html_only_here` on a leaf folder

The leaf's HTML stays at its level, parent doesn't receive it.

```
└── root  O O
    ├── about  O O
    │   ├── intro
    │   │   └── page.html
    │   └── team
    │       └── page.html
    └── contact  I
        └── page.html
```

---

### Example 3 — `.html_stops_here` on a mid-level folder

Nothing below `about` propagates to root.

```
└── root  O
    ├── about  X  O O
    │   ├── intro
    │   │   └── page.html
    │   └── team
    │       └── page.html
    └── contact
        └── page.html
```

---

### Example 4 — `.html_only_here` on a mid-level folder with children

`about` keeps its accumulated content (own + children) but doesn't send it up.

```
└── root  O
    ├── about  I  O O O
    │   ├── intro
    │   │   └── page.html
    │   └── team
    │       └── page.html
    │       └── bio.html
    └── contact
        └── page.html
```

---

### Example 5 — Multiple `.html_only_here` at same level

Each sibling is isolated from the parent independently.

```
└── root  (no dots)
    ├── chapter1  I
    │   └── page.html
    ├── chapter2  I
    │   └── page.html
    └── chapter3  I
        └── page.html
```

---

### Example 6 — `.html_stops_here` at root level

Nothing propagates at all. Each folder only shows its own subtree when clicked.

```
└── root  X
    ├── about  O O
    │   ├── intro
    │   │   └── page.html
    │   └── team
    │       └── page.html
    └── contact  O
        └── page.html
```

---

### Example 7 — Nested `.html_stops_here`

Each boundary is independent. `team` blocks its children from reaching `about`, and `about` blocks everything from reaching `root`.

```
└── root  O
    ├── about  X  O
    │   ├── intro
    │   │   └── page.html
    │   └── team  X  O O
    │       ├── member1
    │       │   └── bio.html
    │       └── member2
    │           └── bio.html
    └── contact
        └── page.html
```

---

### Example 8 — `.html_only_here` inside a `.html_stops_here` subtree

`team` has `.html_stops_here` so nothing reaches `about`. Inside, `member1` has `.html_only_here` so its HTML doesn't reach `team` either.

```
└── root  (no dots)
    └── about  X
        └── team  X  O
            ├── member1  I  O
            │   └── bio.html
            └── member2  O
                └── bio.html
```

---

### Example 9 — Mixed content (HTML + images)

Dotfiles only affect HTML propagation. Images always propagate regardless.

```
└── root  O O  (2 HTML files, images also present but not shown as dots)
    ├── gallery  I  O
    │   ├── description.html
    │   └── photo1.jpg         (image propagates normally to root)
    └── docs
        └── readme.html
```

---

### Example 10 — Deep nesting with both dotfiles

```
└── root  O
    └── project  O
        ├── phase1  X  O O
        │   ├── planning
        │   │   └── notes.html
        │   └── research
        │       └── findings.html
        ├── phase2  O
        │   └── draft
        │       └── report.html
        └── appendix  I  O O
            ├── refs
            │   └── sources.html
            └── data
                └── tables.html
```

- `root` gets 1 dot: only from `phase2/draft/report.html`
- `phase1` has `.html_stops_here`: its 2 HTML files stay within, none reach `project`
- `phase2` propagates normally: `report.html` bubbles up through `project` to `root`
- `appendix` has `.html_only_here`: its 2 accumulated HTML files are visible when clicking `appendix`, but don't reach `project`