#!/usr/bin/env python3
"""storymap.py - stories.yaml -> a lean report, HTML viewer, and native-resolution diagrams.

Usage (DIR defaults to this script's folder, docs/story-map, or the current folder):
    python3 storymap.py build [DIR] [--profile lean|full] [--formats LIST] [--clean]
    python3 storymap.py build [DIR] --formats +csv,flows   # add optional outputs
    python3 storymap.py build [DIR] --formats -onepager   # remove a default output
    python3 storymap.py validate [DIR] [--strict]         # warnings include AGENTS_MISSING
    python3 storymap.py status [DIR]
    python3 storymap.py set-status US-03 built --dir DIR --verified "app, 2026-10-15"
    python3 storymap.py init [DIR] [--vendor] [--agents [FILE]]  # install repo instructions too

Lean defaults: generated/REPORT.md, architecture.png, one-pager.png, story-map.html.
Full includes every optional format; --formats replaces a profile, or +name/-name modifies it.
Only stdlib is required. Optional: Pillow (images/PDF/previews), PyYAML (full YAML),
Graphviz (diagram fallback), fontTools+brotli (opt-in subset fonts). Nothing is uploaded; the generated
viewer makes no requests. The only network request the tool can make is the optional Google Fonts
download when theme.google_font is true (off by default).
Thumbnails are cached in DIR/.cache/thumbs/ only when needed by DOT.
"""
import argparse, base64, collections, csv, html, io, json, math, os, re, shlex, shutil, subprocess, sys, textwrap

try:
    if os.environ.get("STORYMAP_NO_PIL"):  # test hook: pretend Pillow is not installed
        raise ImportError
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
    HAVE_PIL = True
except ImportError:  # the text outputs still work
    HAVE_PIL = False

if HAVE_PIL:
    Image.MAX_IMAGE_PIXELS = None   # native-resolution maps are large on purpose (see "Resolution" in SKILL.md); we only open our own files

__version__ = "1.2.0"

# --------------------------------------------------------------------------- vocabulary
STATUS = collections.OrderedDict([
    ("built",      dict(label="Built",        color="#2E9E6B", bg="#E3F5EC", emoji="\U0001F7E2")),
    ("partly",     dict(label="Partly built", color="#E8A33D", bg="#FDF0DC", emoji="\U0001F7E0")),
    ("unverified", dict(label="Unverified",   color="#6C7BD9", bg="#E9ECFB", emoji="\U0001F7E3")),
    ("missing",    dict(label="Missing",      color="#8A8F98", bg="#F1F3F4", emoji="\u26AA")),
])
TOPIC_PALETTE = ["#0EA5E9", "#8B5CF6", "#14B8A6", "#D946EF", "#64748B", "#E11D48", "#78716C", "#0891B2", "#A16207"]
DEFAULT_TOPIC = "general"
SEVERITIES = ["high", "medium", "low"]
PLATFORMS = ["ios", "android", "web"]
DEVICE_MODELS = ("iphone-island", "iphone-notch", "iphone-home-button", "android-generic", "browser-window", "tablet", "none")
DEVICE_STYLES = ("auto", "black", "titanium", "light")
HTML_BUDGET = 1_500_000   # progressive HTML previews; exported diagrams retain native screenshot resolution
SOURCE_NAMES = ("stories.yaml", "stories.yml", "stories.json")
FORMATS = ("html", "arch", "onepager", "report", "csv", "mermaid", "dot", "flows", "flow-map", "overview", "pdf", "crops", "legacy-md")
LEAN_FORMATS = set(("html", "arch", "onepager", "report"))
ONLY_FORMATS = dict(docs={"report", "csv", "legacy-md"}, mermaid={"mermaid"},
                    diagrams={"arch", "crops", "flows", "flow-map", "overview"}, html={"html"}, pdf={"onepager", "pdf"})


class SourceError(Exception):
    pass


# --------------------------------------------------------------------------- tiny YAML subset
class YamlSubsetError(SourceError):
    pass


def _strip_comment(line):
    q = None
    i = 0
    while i < len(line):
        ch = line[i]
        if q:
            if q == '"' and ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        else:
            if ch in "\"'" and (i == 0 or line[i - 1] in " [,:{-"):
                q = ch
            elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
                return line[:i]
        i += 1
    return line


def _split_key(s):
    q = None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'" and i == 0:
            q = ch
        elif ch == ":" and (i + 1 == len(s) or s[i + 1] == " "):
            return s[:i].strip().strip("\"'"), s[i + 1:].strip()
    return None


def _inline_list(s):
    inner = s[1:-1].strip()
    if not inner:
        return []
    parts, cur, q = [], "", None
    for ch in inner:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur += ch
        elif ch == ",":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [_scalar(p) for p in parts if p.strip() != ""]


def _scalar(s):
    s = s.strip()
    if s == "":
        return ""
    if s[0] == '"':
        if len(s) < 2 or not s.endswith('"'):
            raise YamlSubsetError("unterminated double-quoted string: " + s[:40])
        try:
            return json.loads(s)
        except ValueError:
            return s[1:-1]
    if s[0] == "'":
        if len(s) < 2 or not s.endswith("'"):
            raise YamlSubsetError("unterminated single-quoted string: " + s[:40])
        return s[1:-1].replace("''", "'")
    if s[0] == "[":
        if not s.endswith("]"):
            raise YamlSubsetError("inline list must close on the same line: " + s[:40])
        return _inline_list(s)
    if s[0] in "|>{":
        raise YamlSubsetError("multi-line / flow-map YAML is not supported by the built-in parser "
                              "(keep each value on one line, or `pip install pyyaml`)")
    return s


def parse_yaml_subset(text):
    """Parse the small YAML subset used by stories.yaml. Every scalar is returned as a string."""
    L = []
    for n, raw in enumerate(text.expandtabs(2).splitlines(), 1):
        s = _strip_comment(raw).rstrip()
        if not s.strip() or s.strip() == "---":
            continue
        L.append([len(s) - len(s.lstrip(" ")), s.strip(), n])
    if not L:
        return {}
    pos = [0]

    def is_dash(c):
        return c == "-" or c.startswith("- ")

    def node(indent):
        return parse_list(L[pos[0]][0]) if is_dash(L[pos[0]][1]) else parse_map(L[pos[0]][0])

    def parse_list(ind):
        out = []
        while pos[0] < len(L) and L[pos[0]][0] == ind and is_dash(L[pos[0]][1]):
            i, c, n = L[pos[0]]
            rest = c[1:].lstrip(" ")
            if rest == "":
                pos[0] += 1
                out.append(node(0) if pos[0] < len(L) and L[pos[0]][0] > ind else "")
                continue
            offset = len(c) - len(rest)
            if rest[0] not in "\"'[" and _split_key(rest) is not None:
                L[pos[0]] = [ind + offset, rest, n]
                out.append(parse_map(ind + offset))
            else:
                out.append(_scalar(rest))
                pos[0] += 1
        return out

    def parse_map(ind):
        out = {}
        while pos[0] < len(L) and L[pos[0]][0] == ind and not is_dash(L[pos[0]][1]):
            i, c, n = L[pos[0]]
            kv = _split_key(c)
            if kv is None:
                raise YamlSubsetError('line %d: expected "key: value", got: %s' % (n, c[:60]))
            k, v = kv
            pos[0] += 1
            if v == "":
                nxt = L[pos[0]] if pos[0] < len(L) else None
                if nxt and (nxt[0] > ind or (nxt[0] == ind and is_dash(nxt[1]))):
                    out[k] = node(0)
                else:
                    out[k] = ""
            else:
                out[k] = _scalar(v)
        return out

    root = node(0)
    if pos[0] != len(L):
        raise YamlSubsetError("line %d: unexpected indentation or multi-line value: %s"
                              % (L[pos[0]][2], L[pos[0]][1][:60]))
    return root


def load_raw(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml  # optional
        return yaml.load(text, Loader=yaml.BaseLoader) or {}  # BaseLoader: every scalar stays a string
    except ImportError:
        return parse_yaml_subset(text)


# --------------------------------------------------------------------------- model
def find_source(d):
    for n in SOURCE_NAMES:
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return p
    raise SourceError("no stories.yaml found in %s (run `init` first?)" % d)


def repo_root(path, fallback=True):
    """Nearest existing ancestor with a .git directory/file; optionally fall back to cwd."""
    path = os.path.abspath(path)
    while not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    while True:
        git = os.path.join(path, ".git")
        if os.path.isdir(git) or os.path.isfile(git):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return os.getcwd() if fallback else None
        path = parent


def repo_mentions_story_map(root):
    """Check only the repository's instruction files and direct Cursor rules."""
    paths = [os.path.join(root, name) for name in ("AGENTS.md", "CLAUDE.md")]
    rules = os.path.join(root, ".cursor", "rules")
    if os.path.isdir(rules):
        paths += [os.path.join(rules, name) for name in sorted(os.listdir(rules))
                  if name.endswith((".mdc", ".md"))]
    for path in paths:
        try:
            # A linked instruction outside the repo must not extend this check above it.
            if os.path.commonpath((os.path.realpath(root), os.path.realpath(path))) != os.path.realpath(root):
                continue
            with open(path, encoding="utf-8") as f:
                if re.search(r"user-story-maps|story-map|stories\.yaml", f.read(), re.I):
                    return True
        except (OSError, UnicodeError, ValueError):
            continue
    return False


def _s(d, k, default=""):
    v = d.get(k, default) if isinstance(d, dict) else default
    return str(v).strip() if v is not None else default


def _list(v):
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v).split(",") if x.strip()]


def _dicts(v, name):
    if v in (None, ""):
        return []
    if not isinstance(v, list) or any(not isinstance(x, dict) for x in v):
        raise SourceError("`%s:` must be a list of items, each starting with `- id: ...`" % name)
    return v


EDGE_RE = re.compile(r"^\s*(\S+?)\s*->\s*(\S+?)\s*(?::\s*(.*))?$")


def load_model(src_dir):
    path = find_source(src_dir)
    raw = load_raw(path)
    if not isinstance(raw, dict):
        raise SourceError("%s: top level must be a mapping (app, personas, flows, screens, stories, gaps)" % path)
    app = raw.get("app") or {}
    if not isinstance(app, dict):
        raise SourceError("`app:` must be a mapping")
    m = dict(root=os.path.abspath(src_dir), source=path, raw=raw)
    m["app"] = dict(name=_s(app, "name", "My app"), platform=_s(app, "platform", "ios").lower(),
                    version=_s(app, "version"), checked=_s(app, "checked"), summary=_s(app, "summary"),
                    disclaimer=_s(app, "disclaimer"), device=_s(app, "device").lower(),
                    agents_check=_s(app, "agents_check").lower())
    m["personas"] = [dict(id=_s(p, "id"), name=_s(p, "name") or _s(p, "id"),
                          as_a=_s(p, "as_a") or (_s(p, "name") or _s(p, "id")).lower(),
                          description=_s(p, "description")) for p in _dicts(raw.get("personas"), "personas")]
    topics = []
    for i, x in enumerate(_dicts(raw.get("topics"), "topics")):
        order = _s(x, "order")
        topics.append(dict(id=_s(x, "id"), title=_s(x, "title") or _s(x, "id"), description=_s(x, "description"),
                           color=_s(x, "color"),
                           order=float(order) if re.match(r"^-?\d+(\.\d+)?$", order) else float(i + 1), _i=i))
    m["topics_implicit"] = not topics
    if not topics:
        topics = [dict(id=DEFAULT_TOPIC, title="General", description="", color=TOPIC_PALETTE[2], order=1.0, _i=0)]
    m["topics"] = sorted(topics, key=lambda tp: (tp["order"], tp["_i"]))
    m["flows"], m["edges"] = [], []
    for f in _dicts(raw.get("flows"), "flows"):
        fl = dict(id=_s(f, "id"), title=_s(f, "title") or _s(f, "id"), description=_s(f, "description"),
                  topic=_s(f, "topic") or (DEFAULT_TOPIC if m["topics_implicit"] else ""))
        m["flows"].append(fl)
        for e in _list(f.get("edges")):
            mt = EDGE_RE.match(e)
            if not mt:
                m["edges"].append(dict(src=None, dst=None, label="", flow=fl["id"], raw=e))
                continue
            label = (mt.group(3) or "").strip().strip("\"'")
            m["edges"].append(dict(src=mt.group(1), dst=mt.group(2), label=label, flow=fl["id"], raw=e,
                                   dashed=label.startswith("(")))
    m["screens"] = [dict(id=_s(x, "id"), title=_s(x, "title") or _s(x, "id"), flow=_s(x, "flow"),
                         image=_s(x, "image"), not_captured=_s(x, "not_captured"), notes=_s(x, "notes"),
                         where=_s(x, "where"), verified=_s(x, "verified"),
                         status_override=_s(x, "status").lower(), topic=_s(x, "topic"),
                         device=_s(x, "device").lower())
                    for x in _dicts(raw.get("screens"), "screens")]
    m["stories"] = [dict(id=_s(x, "id"), persona=_s(x, "persona"), want=_s(x, "want"), so_that=_s(x, "so_that"),
                         story=_s(x, "story"), screens=_list(x.get("screens")),
                         status=(_s(x, "status") or "unverified").lower(), verified=_s(x, "verified"),
                         where=_s(x, "where"), notes=_s(x, "notes"), flow=_s(x, "flow"), topic=_s(x, "topic"))
                    for x in _dicts(raw.get("stories"), "stories")]
    m["gaps"] = [dict(id=_s(x, "id"), severity=(_s(x, "severity") or "medium").lower(), title=_s(x, "title"),
                      detail=_s(x, "detail"), where=_s(x, "where"), stories=_list(x.get("stories")))
                 for x in _dicts(raw.get("gaps"), "gaps")]
    index(m)
    apply_theme(m)
    return m


def index(m):
    m["T"] = {tp["id"]: tp for tp in m["topics"]}
    trank = {tp["id"]: i for i, tp in enumerate(m["topics"])}
    m["flows"] = sorted(m["flows"], key=lambda f: trank.get(f["topic"], 999))  # stable: keeps source order inside a topic
    m["P"] = {p["id"]: p for p in m["personas"]}
    m["F"] = {f["id"]: f for f in m["flows"]}
    m["S"] = {s["id"]: s for s in m["screens"]}
    m["U"] = {u["id"]: u for u in m["stories"]}
    used = collections.defaultdict(list)
    for u in m["stories"]:
        for sid in u["screens"]:
            used[sid].append(u["id"])
    m["used_by"] = used
    for s in m["screens"]:
        s["status"] = screen_status(m, s)
        s["topic_eff"] = s["topic"] or (m["F"][s["flow"]]["topic"] if s["flow"] in m["F"] else "")
    for u in m["stories"]:
        u["flow_eff"] = u["flow"] or next((m["S"][sid]["flow"] for sid in u["screens"]
                                           if sid in m["S"] and m["S"][sid]["flow"]), "")
        u["topic_eff"] = u["topic"] or (m["F"][u["flow_eff"]]["topic"] if u["flow_eff"] in m["F"] else "") or next(
            (m["S"][sid]["topic_eff"] for sid in u["screens"] if sid in m["S"] and m["S"][sid]["topic_eff"]), "")


def screen_status(m, s):
    """Screen status = explicit `status:` override, else aggregated from the stories that use it."""
    if s["status_override"] in STATUS:
        return s["status_override"]
    st = {m["U"][u]["status"] for u in m["used_by"].get(s["id"], []) if m["U"][u]["status"] in STATUS}
    if not st:
        return "unverified"
    if len(st) == 1:
        return next(iter(st))
    if st <= {"built", "unverified"}:
        return "unverified"  # honesty: not everything on this screen is confirmed
    return "partly"


def story_text(m, u):
    if u["story"]:
        return u["story"]
    p = m["P"].get(u["persona"])
    who = p["as_a"] if p else (u["persona"] or "user")
    art = "an" if who[:1].lower() in "aeiou" else "a"
    want = u["want"].rstrip(". ")
    if not re.match(r"(?i)^i\s+(want|need)", want):
        want = "I want " + want
    txt = "As %s %s, %s" % (art, who, want)
    if u["so_that"]:
        txt += " so that " + u["so_that"].rstrip(". ")
    return txt + "."


def persona_name(m, pid):
    p = m["P"].get(pid)
    return p["name"] if p else pid


def screen_titles(m, u):
    return [m["S"][s]["title"] if s in m["S"] else s for s in u["screens"]]


def image_path(m, s):
    return os.path.join(m["root"], s["image"]) if s["image"] else None


def image_exists(m, s):
    p = image_path(m, s)
    return bool(p) and os.path.isfile(p)


def counts(items, key="status"):
    c = collections.OrderedDict((k, 0) for k in STATUS)
    for i in items:
        if i[key] in c:
            c[i[key]] += 1
    return c


# --------------------------------------------------------------------------- validation
def validate(m):
    """Return (level, code, message) issues, including AGENTS_MISSING and text warnings."""
    out = []
    E = lambda c, msg: out.append(("error", c, msg))
    W = lambda c, msg: out.append(("warn", c, msg))
    if m["app"].get("agents_check", "").lower() not in ("off", "false", "no", "0"):
        root = repo_root(os.path.dirname(m["source"]), fallback=False)
        if root and not repo_mentions_story_map(root):
            directory = os.path.relpath(os.path.dirname(os.path.abspath(m["source"])), root).replace(os.sep, "/")
            W("AGENTS_MISSING", "no repo instruction file mentions the story map; run `storymap.py init %s --agents` "
              "or paste templates/AGENTS-snippet.md into AGENTS.md" % shlex.quote(directory))
    for kind, items in (("persona", m["personas"]), ("topic", m["topics"]), ("flow", m["flows"]), ("screen", m["screens"]),
                        ("story", m["stories"]), ("gap", m["gaps"])):
        seen = collections.Counter(i["id"] for i in items)
        for i in items:
            if not i["id"]:
                E("MISSING_ID", "a %s has no `id`" % kind)
        for k, n in seen.items():
            if k and n > 1:
                E("DUPLICATE_ID", "%s id '%s' is used %d times" % (kind, k, n))
    if m["topics_implicit"]:
        W("NO_TOPICS", "no `topics:` section - everything is filed under 'General'. Add topics (onboarding, access, "
          "main journey, content, settings, payments, support) so the architecture view is meaningful")
    for tp in m["topics"]:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", tp["color"]):
            W("BAD_COLOR", "topic %s: color '%s' should look like #RRGGBB" % (tp["id"], tp["color"]))
        if tp["id"] and not m["topics_implicit"] and not any(
                f["topic"] == tp["id"] for f in m["flows"]) and not any(s["topic"] == tp["id"] for s in m["screens"]):
            W("UNUSED_TOPIC", "topic %s has no flows or screens" % tp["id"])
    for f in m["flows"]:
        if not f["topic"]:
            E("MISSING_TOPIC", "flow %s has no `topic:` (one of: %s)" % (f["id"], ", ".join(m["T"])))
        elif f["topic"] not in m["T"]:
            E("UNKNOWN_TOPIC", "flow %s: topic '%s' is not defined under `topics:`" % (f["id"], f["topic"]))
    for s in m["screens"]:
        if s["topic"] and s["topic"] not in m["T"]:
            E("UNKNOWN_TOPIC", "screen %s: topic '%s' is not defined under `topics:`" % (s["id"], s["topic"]))
        elif not s["topic_eff"]:
            E("MISSING_TOPIC", "screen %s has no topic (give its flow a `topic:` or set `topic:` on the screen)" % s["id"])
    for u in m["stories"]:
        if u["topic"] and u["topic"] not in m["T"]:
            E("UNKNOWN_TOPIC", "story %s: topic '%s' is not defined under `topics:`" % (u["id"], u["topic"]))
    if m["app"]["platform"] not in PLATFORMS:
        W("PLATFORM", "app.platform '%s' is not one of %s" % (m["app"]["platform"], "/".join(PLATFORMS)))
    for u in m["stories"]:
        i = u["id"] or "(no id)"
        if u["status"] not in STATUS:
            E("BAD_STATUS", "story %s: status '%s' is not one of %s" % (i, u["status"], "/".join(STATUS)))
        if not u["story"] and not u["want"]:
            E("NO_TEXT", "story %s: needs `want:` (and `so_that:`) or a full `story:` sentence" % i)
        if u["persona"] and u["persona"] not in m["P"]:
            E("UNKNOWN_PERSONA", "story %s: persona '%s' is not defined under `personas:`" % (i, u["persona"]))
        if not u["persona"]:
            E("UNKNOWN_PERSONA", "story %s: has no `persona:`" % i)
        for sid in u["screens"]:
            if sid not in m["S"]:
                E("UNKNOWN_SCREEN", "story %s points at screen '%s' which does not exist" % (i, sid))
        if u["flow"] and u["flow"] not in m["F"]:
            E("UNKNOWN_FLOW", "story %s: flow '%s' does not exist" % (i, u["flow"]))
        if not u["screens"] and u["status"] != "missing":
            W("NO_SCREENS", "story %s has no screens (add `screens: [...]`; ok only for backend/missing stories)" % i)
        if u["status"] == "built" and not u["verified"]:
            E("BUILT_NOT_VERIFIED", "story %s is 'built' but has no `verified:` (how/when you checked it). "
              "Honesty rule: use status 'unverified' until you have checked it in code or on a running app." % i)
        if u["status"] == "built" and not u["where"]:
            W("NO_WHERE", "story %s is 'built' but has no `where:` (file / PR / endpoint)" % i)
    known_dev = set(DEVICE_MODELS) | set(load_frames(m)["frames"])
    for what, dv in [("app.device", m["app"]["device"]), ("theme.device.model", TH["device"]["model"])] + [
            ("screen %s: device" % (s["id"] or "(no id)"), s["device"]) for s in m["screens"]]:
        if dv and dv not in known_dev:
            E("UNKNOWN_DEVICE", "%s '%s' is not one of %s (or a frame name from frames.json)" % (what, dv, ", ".join(DEVICE_MODELS)))
    if TH["device"]["style"] not in DEVICE_STYLES:
        W("BAD_DEVICE_STYLE", "theme.device.style '%s' is not one of %s; using 'auto'" % (TH["device"]["style"], "/".join(DEVICE_STYLES)))
    for s in m["screens"]:
        i = s["id"] or "(no id)"
        if s["flow"] and s["flow"] not in m["F"]:
            E("UNKNOWN_FLOW", "screen %s: flow '%s' does not exist" % (i, s["flow"]))
        if not s["flow"]:
            W("NO_FLOW", "screen %s has no `flow:` (it will not appear in any flow diagram)" % i)
        if s["status_override"] and s["status_override"] not in STATUS:
            E("BAD_STATUS", "screen %s: status '%s' is not one of %s" % (i, s["status_override"], "/".join(STATUS)))
        if s["image"]:
            if os.path.isabs(s["image"]) or ".." in s["image"].replace("\\", "/").split("/"):
                E("IMAGE_PATH", "screen %s: image path must be relative and inside this folder (got '%s')" % (i, s["image"]))
            elif not os.path.isfile(os.path.join(m["root"], s["image"])):
                if s["not_captured"]:
                    pass
                else:
                    W("MISSING_IMAGE", "screen %s: screenshot '%s' not found (capture it, or set `not_captured: reason`)" % (i, s["image"]))
        elif not s["not_captured"]:
            W("MISSING_IMAGE", "screen %s has no `image:` (capture it, or set `not_captured: reason`)" % i)
        if s["id"] and not m["used_by"].get(s["id"]):
            W("UNUSED_SCREEN", "screen %s ('%s') is used by no story" % (i, s["title"]))
    for e in m["edges"]:
        if e["src"] is None:
            E("EDGE_SYNTAX", "flow %s: edge '%s' must look like `from_id -> to_id: label`" % (e["flow"], e["raw"]))
            continue
        for end in (e["src"], e["dst"]):
            if end not in m["S"]:
                E("UNKNOWN_SCREEN", "flow %s: edge '%s' uses unknown screen '%s'" % (e["flow"], e["raw"], end))
    for f in m["flows"]:
        if f["id"] and not any(s["flow"] == f["id"] for s in m["screens"]):
            W("EMPTY_FLOW", "flow %s has no screens" % f["id"])
    for p in m["personas"]:
        if p["id"] and not any(u["persona"] == p["id"] for u in m["stories"]):
            W("UNUSED_PERSONA", "persona %s has no stories" % p["id"])
    for g in m["gaps"]:
        if g["severity"] not in SEVERITIES:
            E("BAD_SEVERITY", "gap %s: severity '%s' is not one of %s" % (g["id"], g["severity"], "/".join(SEVERITIES)))
        for uid in g["stories"]:
            if uid not in m["U"]:
                E("UNKNOWN_STORY", "gap %s refers to unknown story '%s'" % (g["id"], uid))
    field_limits = (
        ("story", m["stories"], (("want", 160), ("so_that", 160), ("story", 160),
                                 ("notes", 200), ("where", 200), ("verified", 200))),
        ("screen", m["screens"], (("notes", 200), ("where", 200), ("verified", 200))),
        ("gap", m["gaps"], (("title", 100), ("detail", 400), ("where", 120))),
    )
    for kind, items, limits in field_limits:
        for item in items:
            for field, limit in limits:
                size = len(item.get(field, ""))
                if size > limit:
                    W("long-field", "%s %s: `%s` is %d characters (limit %d); "
                      "shorten or move detail to the code/docs" % (kind, item["id"] or "(no id)", field, size, limit))
    for kind, items, fields in (("story", m["stories"], ("verified", "where", "notes")),
                                ("screen", m["screens"], ("where", "notes")),
                                ("gap", m["gaps"], ("where",))):
        for field in fields:
            repeated = collections.OrderedDict()
            for item in items:
                value = item.get(field, "").strip()
                if len(value) >= 40:
                    repeated.setdefault(value.casefold(), []).append(item["id"] or "(no id)")
            for ids in repeated.values():
                if len(ids) >= 3:
                    first_ids = ", ".join(ids[:5]) + (", ..." if len(ids) > 5 else "")
                    W("repeated-text", "%s `%s`: the same text appears in %d items (%s); "
                      "say it once (e.g. in app.summary or a gap) or shorten it" % (kind, field, len(ids), first_ids))
    return out


def report(issues, quiet_ok=False):
    for lvl, code, msg in issues:
        print("  %s %-18s %s" % ("ERROR" if lvl == "error" else "warn ", code, msg))
    ne = sum(1 for i in issues if i[0] == "error")
    nw = len(issues) - ne
    if not issues and not quiet_ok:
        print("  OK - no problems found")
    return ne, nw


# --------------------------------------------------------------------------- graph helpers
def flow_screens(m, fid):
    """Screens of a flow in reading order (breadth-first along the edges)."""
    ss = [s["id"] for s in m["screens"] if s["flow"] == fid]
    if not ss:
        return []
    inset = set(ss)
    nxt = collections.defaultdict(list)
    indeg = collections.Counter()
    for e in m["edges"]:
        if e["src"] in inset and e["dst"] in inset and e["src"] != e["dst"]:
            nxt[e["src"]].append(e["dst"])
            indeg[e["dst"]] += 1
    roots = [s for s in ss if indeg[s] == 0] or [ss[0]]
    order, seen = [], set()
    for r in roots + ss:  # remaining (cyclic / unlinked) screens keep their source order
        if r in seen:
            continue
        queue = [r]
        seen.add(r)
        while queue:
            c = queue.pop(0)
            order.append(c)
            for n in nxt[c]:
                if n not in seen:
                    seen.add(n)
                    queue.append(n)
    return order


def flow_graph(m, fid):
    """Nodes and edges for one flow. Links to/from other flows become 'portal' nodes."""
    mine = set(flow_screens(m, fid))
    nodes = [dict(key=s, kind="screen", screen=m["S"][s]) for s in flow_screens(m, fid)]
    edges, portals = [], {}
    fl = lambda sid: m["F"][m["S"][sid]["flow"]]["title"] if m["S"][sid]["flow"] in m["F"] else "other"
    for e in m["edges"]:
        if e["src"] not in m["S"] or e["dst"] not in m["S"]:
            continue
        a, b = e["src"] in mine, e["dst"] in mine
        if a and b:
            edges.append((e["src"], e["dst"], e["label"], e["dashed"]))
        elif a or b:
            other = e["dst"] if a else e["src"]
            kind = "out" if a else "in"
            k = "%s:%s" % (kind, other)
            if k not in portals:
                portals[k] = True
                nodes.append(dict(key=k, kind="portal_" + kind, screen=m["S"][other],
                                  label=("Go to " if a else "From ") + fl(other) + ": " + m["S"][other]["title"]))
            edges.append((e["src"], k, e["label"], e["dashed"]) if a else (k, e["dst"], e["label"], e["dashed"]))
    return nodes, edges


def cross_flow_edges(m):
    seen = collections.OrderedDict()
    for e in m["edges"]:
        if e["src"] in m["S"] and e["dst"] in m["S"]:
            fa, fb = m["S"][e["src"]]["flow"], m["S"][e["dst"]]["flow"]
            if fa and fb and fa != fb and (fa, fb) not in seen:
                seen[(fa, fb)] = e["label"]
    return seen


def tint(hexcolor, a=0.88):
    """Mix a colour with the page background (a = how much background): a light tint on a light theme, a dark tint on a dark one."""
    r, g, b = (int(hexcolor.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    bg = TH["bg"].lstrip("#") if TH.get("dark") else "FFFFFF"
    br, bgg, bb = (int(bg[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % tuple(int(c + (t - c) * a) for c, t in zip((r, g, b), (br, bgg, bb)))


def on_color():
    """Text colour for labels drawn on a status-coloured chip: white on a light theme, the page background on a dark one."""
    return TH["bg"] if TH.get("dark") else "white"


def topic_title(m, tid):
    return m["T"][tid]["title"] if tid in m["T"] else "Unassigned"


def topic_summary(m):
    """One row per topic: screens, stories, status counts, flows."""
    rows = []
    for tp in m["topics"]:
        ss = [s for s in m["screens"] if s["topic_eff"] == tp["id"]]
        us = [u for u in m["stories"] if u["topic_eff"] == tp["id"]]
        rows.append(dict(topic=tp, screens=ss, stories=us, counts=counts(us),
                         flows=[f for f in m["flows"] if f["topic"] == tp["id"]]))
    return rows


def cross_topic_edges(m):
    """[(topic_a, topic_b, label, [edges])] for arrows that leave a topic, one entry per topic pair."""
    seen = collections.OrderedDict()
    for e in m["edges"]:
        if e["src"] in m["S"] and e["dst"] in m["S"]:
            a, b = m["S"][e["src"]]["topic_eff"], m["S"][e["dst"]]["topic_eff"]
            if a and b and a != b:
                seen.setdefault((a, b), []).append(e)
    return seen


def story_flow_title(m, u):
    f = u["flow_eff"]
    return m["F"][f]["title"] if f in m["F"] else "Unassigned"


def esc_md(t):
    return str(t).replace("|", "\\|").replace("\n", " ").strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def header_line(m):
    a = m["app"]
    bits = [b for b in (a["platform"], a["version"], ("checked " + a["checked"]) if a["checked"] else "") if b]
    return " · ".join(bits)


def legend_md():
    return " · ".join("%s %s" % (v["emoji"], k) for k, v in STATUS.items())


# --------------------------------------------------------------------------- markdown / csv
def report_text(value):
    """Prose with only Markdown table and line-breaking characters escaped."""
    return str(value).replace("<", "&lt;").replace("|", "\\|").replace("\r\n", " ").replace("\r", " ").replace("\n", " ")


def report_code(value):
    value = str(value).replace("|", "\\|").replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    ticks = "`" * (max([len(t) for t in re.findall(r"`+", value)] or [0]) + 1)
    pad = " " if "`" in value else ""
    return ticks + pad + value + pad + ticks


def gen_report(m, gen, expected):
    text = report_text
    L = ["# %s - story map report" % text(m["app"]["name"]), "",
         "_Generated from `stories.yaml` by storymap.py - edit the source, not this file._", ""]
    if header_line(m):
        L += [text(header_line(m)), ""]
    if m["app"]["summary"]:
        L += [text(m["app"]["summary"]), ""]
    if m["app"]["disclaimer"]:
        L += ["> " + text(m["app"]["disclaimer"]), ""]
    L += ["**%d stories:** " % len(m["stories"]) + " · ".join("%s %d %s" % (STATUS[k]["emoji"], n, k) for k, n in counts(m["stories"]).items() if n),
          "Built = checked in code/running app (see Verified); unverified = not checked yet.", ""]
    links = []
    for path in ("architecture.png", "one-pager.png", "one-pager.pdf", "story-map.html", "flows/", "overview.png", "mermaid/"):
        requested = path in expected or (path.endswith("/") and any(p.startswith(path) for p in expected))
        if requested and os.path.exists(os.path.join(gen, path)):
            links.append("[%s](%s)" % (path, path))
    if links:
        L += [" · ".join(links), ""]
    L += ["## Topics", "", "| Topic | Screens | Stories | Status counts | Flows |", "|---|---|---|---|---|"]
    for r in topic_summary(m):
        L.append("| %s | %d | %d | %s | %s |" % (
            text(r["topic"]["title"]), len(r["screens"]), len(r["stories"]),
            " · ".join("%s %d" % (STATUS[k]["emoji"], n) for k, n in r["counts"].items() if n) or "-",
            text(", ".join(f["title"] for f in r["flows"]))))
    connections = cross_topic_edges(m)
    if connections:
        L.append("")
    for (a, b), edges in connections.items():
        labels = list(collections.OrderedDict.fromkeys(e["label"] for e in edges if e["label"]))[:4]
        L.append("- %s -> %s%s" % (text(topic_title(m, a)), text(topic_title(m, b)), ": " + text(", ".join(labels)) if labels else ""))
    L += ["", "## Stories", ""]
    for tp, us in stories_by_topic(m):
        L += ["### " + text(tp["title"] if tp else "Unassigned"), ""]
        if tp and tp["description"]:
            L += [text(tp["description"]), ""]
        L += ["| ID | Story | Screens | Status | Evidence |", "|---|---|---|---|---|"]
        for u in us:
            shots = []
            for sid in u["screens"]:
                s = m["S"].get(sid)
                title = text(s["title"] if s else sid)
                if s and image_exists(m, s):
                    label = title.replace("[", "\\[").replace("]", "\\]")
                    shots.append("[%s](../%s)" % (label, urllib.parse.quote(s["image"].replace("\\", "/"), safe="/")))
                else:
                    shots.append(title)
            evidence = []
            for field, label in (("verified", "verified"), ("where", "where"), ("notes", "note")):
                if u[field]:
                    evidence.append(label + ": " + (report_code(u[field]) if field == "where" else text(u[field])))
            L.append("| %s | %s | %s | %s %s | %s |" % (text(u["id"]), text(story_text(m, u)), ", ".join(shots),
                     STATUS.get(u["status"], {}).get("emoji", "?"), text(u["status"]), "; ".join(evidence)))
        L.append("")
    L += ["## Gaps and risks", ""]
    for severity in SEVERITIES:
        gaps = [g for g in m["gaps"] if g["severity"] == severity]
        if not gaps:
            continue
        L += ["### " + severity.title(), ""]
        for g in gaps:
            line = "- **%s - %s**" % (text(g["id"]), text(g["title"]))
            if g["detail"]:
                line += " - " + text(g["detail"]).rstrip(". ") + "."
            if g["where"]:
                line += " Where: " + report_code(g["where"]) + "."
            if g["stories"]:
                line += " Stories: " + ", ".join(text(uid) for uid in g["stories"]) + "."
            L.append(line)
        L.append("")
    if not m["gaps"]:
        L += ["No gaps or risks recorded.", ""]
    write(os.path.join(gen, "REPORT.md"), "\n".join(L))


def stories_by_topic(m):
    """[(topic or None, [stories])] in topic order; stories without a known topic go last."""
    out = [(tp, [u for u in m["stories"] if u["topic_eff"] == tp["id"]]) for tp in m["topics"]]
    out = [(tp, us) for tp, us in out if us]
    rest = [u for u in m["stories"] if u["topic_eff"] not in m["T"]]
    return out + ([(None, rest)] if rest else [])


def topic_table_md(m):
    L = ["| Topic | Screens | Stories | " + " | ".join("%s %s" % (v["emoji"], k) for k, v in STATUS.items()) + " | Flows |",
         "|---|---|---|" + "---|" * len(STATUS) + "---|"]
    for r in topic_summary(m):
        L.append("| **%s** | %d | %d | %s | %s |" % (
            esc_md(r["topic"]["title"]), len(r["screens"]), len(r["stories"]),
            " | ".join(str(n) for n in r["counts"].values()), esc_md(", ".join(f["title"] for f in r["flows"]))))
    return "\n".join(L)


def story_row(m, u):
    shots = []
    for sid in u["screens"]:
        s = m["S"].get(sid)
        if s and s["image"] and image_exists(m, s):
            shots.append("[%s](../%s)" % (esc_md(s["title"]), s["image"]))
        else:
            shots.append(esc_md(s["title"] if s else sid))
    return "| %s | %s | %s | %s | %s | %s %s | %s | %s | %s |" % (
        esc_md(u["id"]), esc_md(topic_title(m, u["topic_eff"])), esc_md(persona_name(m, u["persona"])),
        esc_md(story_text(m, u)), ", ".join(shots), STATUS.get(u["status"], {}).get("emoji", "?"), u["status"],
        esc_md(u["where"]), esc_md(u["verified"]), esc_md(u["notes"]))


def gen_stories_md(m, gen):
    c = counts(m["stories"])
    L = ["# %s - user stories" % m["app"]["name"], "",
         "_Generated from `stories.yaml` - do not edit this file, edit the source and re-run the build._", ""]
    if header_line(m):
        L += ["**%s**" % header_line(m), ""]
    if m["app"]["summary"]:
        L += [m["app"]["summary"], ""]
    if m["app"]["disclaimer"]:
        L += ["> " + m["app"]["disclaimer"], ""]
    L += ["**%d stories:** " % len(m["stories"]) + " · ".join("%s %d %s" % (STATUS[k]["emoji"], n, k) for k, n in c.items()), "",
          "Status: " + legend_md() + ". *Built* means checked in code or on a running app (see the Verified column); "
          "*unverified* means not checked yet.", "", "## Topics", "", topic_table_md(m), ""]
    head = ["| ID | Topic | Persona | User story | Screen(s) | Status | Where it lives | Verified | Notes |",
            "|---|---|---|---|---|---|---|---|---|"]
    for tp, us in stories_by_topic(m):
        L += ["## %s" % (tp["title"] if tp else "Unassigned"), ""]
        if tp and tp["description"]:
            L += [tp["description"], ""]
        L += head + [story_row(m, u) for u in us] + [""]
    write(os.path.join(gen, "user-stories.md"), "\n".join(L))


def gen_stories_csv(m, gen):
    path = os.path.join(gen, "user-stories.csv")
    os.makedirs(gen, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ID", "Topic", "Persona", "User story", "Flow", "Screens", "Status", "Where it lives", "Verified", "Notes"])
        for tp, us in stories_by_topic(m):
            for u in us:
                w.writerow([u["id"], tp["title"] if tp else "", persona_name(m, u["persona"]), story_text(m, u),
                            story_flow_title(m, u), "; ".join(screen_titles(m, u)), u["status"], u["where"],
                            u["verified"], u["notes"]])


def gen_gaps_md(m, gen):
    L = ["# %s - gaps and risks" % m["app"]["name"], "",
         "_Generated from `stories.yaml` (`gaps:`). Ordered by severity._", ""]
    if m["app"]["disclaimer"]:
        L += ["> " + m["app"]["disclaimer"], ""]
    if not m["gaps"]:
        L += ["No gaps recorded yet. Add them under `gaps:` in the source.", ""]
    for sev in SEVERITIES:
        gs = [g for g in m["gaps"] if g["severity"] == sev]
        if not gs:
            continue
        L += ["## %s severity" % sev.capitalize(), ""]
        for g in gs:
            L.append("### %s - %s" % (g["id"], g["title"]))
            if g["detail"]:
                L += ["", g["detail"]]
            if g["where"]:
                L += ["", "Where: `%s`" % g["where"]]
            if g["stories"]:
                L += ["", "Related stories: " + ", ".join(g["stories"])]
            L.append("")
    write(os.path.join(gen, "gaps-and-risks.md"), "\n".join(L))


# --------------------------------------------------------------------------- mermaid
def mid(s):
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", s)


def mq(t):
    return str(t).replace('"', "'").replace("\n", " ")


def mermaid_classes():
    L = []
    for k, v in STATUS.items():
        dash = {"built": "", "partly": "", "unverified": ",stroke-dasharray:4 3", "missing": ",stroke-dasharray:5 4"}[k]
        L.append("  classDef %s fill:%s,stroke:%s,stroke-width:%dpx%s,color:%s;" % (
            k, v["bg"], v["color"], 3 if k in ("built", "partly") else 2, dash, TH["ink"]))
    L.append("  classDef portal fill:%s,stroke:%s,color:%s;" % (TH["portal_out"], TH["secondary"], TH["ink"]))
    return L


def mermaid_init():
    return ('%%{init: {"theme":"base","themeVariables":{"fontFamily":"' + (TH["font"] or "Helvetica") + '","fontSize":"16px",'
            '"primaryColor":"' + TH["bg"] + '","primaryTextColor":"' + TH["ink"] + '","primaryBorderColor":"' + TH["primary"] +
            '","lineColor":"' + TH["primary"] + '","secondaryColor":"' + TH["surface"] + '","tertiaryColor":"' + TH["surface2"] + '"}}}%%')




def mermaid_flow(m, fid):
    nodes, edges = flow_graph(m, fid)
    L = ["flowchart LR"]
    for n in nodes:
        if n["kind"] == "screen":
            s = n["screen"]
            L.append('  %s["%s<br/><i>%s</i>"]:::%s' % (mid(n["key"]), mq(s["title"]), STATUS[s["status"]]["label"], s["status"]))
        else:
            L.append('  %s(["%s"]):::portal' % (mid(n["key"]), mq(n["label"])))
    for a, b, lab, dashed in edges:
        arrow = "-.->" if dashed else "-->"
        L.append('  %s %s|"%s"| %s' % (mid(a), arrow, mq(lab), mid(b)) if lab else "  %s %s %s" % (mid(a), arrow, mid(b)))
    return mermaid_init() + "\n" + "\n".join(L + mermaid_classes()) + "\n"


def mermaid_overview(m):
    L = [mermaid_init(), "flowchart LR"]
    for f in m["flows"]:
        ss = [s for s in m["screens"] if s["flow"] == f["id"]]
        us = [u for u in m["stories"] if u["flow_eff"] == f["id"]]
        c = counts(us)
        L.append('  %s["<b>%s</b><br/>%d screens · %d stories<br/>%s"]:::flow' % (
            mid(f["id"]), mq(f["title"]), len(ss), len(us),
            " · ".join("%d %s" % (n, k) for k, n in c.items() if n) or "no stories"))
    for (fa, fb), lab in cross_flow_edges(m).items():
        L.append('  %s -->|"%s"| %s' % (mid(fa), mq(lab), mid(fb)))
    L.append("  classDef flow fill:%s,stroke:%s,stroke-width:3px,color:%s;" % (TH["bg"], TH["primary"], TH["ink"]))
    return "\n".join(L) + "\n"


def mermaid_topics(m):
    """Topic-level graph: one box per topic, arrows where users cross from one topic to another."""
    L = [mermaid_init(), "flowchart LR"]
    for r in topic_summary(m):
        tp = r["topic"]
        L.append('  %s["<b>%s</b><br/>%d screens · %d stories<br/>%s"]' % (
            mid("t_" + tp["id"]), mq(tp["title"]), len(r["screens"]), len(r["stories"]),
            " · ".join("%d %s" % (n, k) for k, n in r["counts"].items() if n) or "no stories"))
    for (a, b), es in cross_topic_edges(m).items():
        L.append('  %s ==>|"%s"| %s' % (mid("t_" + a), mq(es[0]["label"] + (" +%d more" % (len(es) - 1) if len(es) > 1 else "")), mid("t_" + b)))
    for r in topic_summary(m):
        tp = r["topic"]
        L.append("  style %s fill:%s,stroke:%s,stroke-width:3px,color:%s" % (mid("t_" + tp["id"]), tint(tp["color"], 0.9), tp["color"], TH["ink"]))
    return "\n".join(L) + "\n"


def mermaid_architecture(m):
    """Screens grouped in one subgraph per topic; edges that cross topics are labelled."""
    L = [mermaid_init(), "flowchart LR"]
    for r in topic_summary(m):
        tp = r["topic"]
        if not r["screens"]:
            continue
        L.append('  subgraph %s["%s"]' % (mid("sg_" + tp["id"]), mq(tp["title"])))
        L.append("    direction TB")
        for s in r["screens"]:
            L.append('    %s["%s<br/><i>%s</i>"]:::%s' % (mid(s["id"]), mq(s["title"]), STATUS[s["status"]]["label"], s["status"]))
        L.append("  end")
    for e in m["edges"]:
        if e["src"] in m["S"] and e["dst"] in m["S"]:
            cross = m["S"][e["src"]]["topic_eff"] != m["S"][e["dst"]]["topic_eff"]
            arrow = "-.->" if e["dashed"] else ("==>" if cross else "-->")
            lab = e["label"] if cross and e["label"] else ""
            L.append('  %s %s%s %s' % (mid(e["src"]), arrow, ('|"%s"|' % mq(lab)) if lab else "", mid(e["dst"])))
    for r in topic_summary(m):
        tp = r["topic"]
        if r["screens"]:
            L.append("  style %s fill:%s,stroke:%s,stroke-width:2px" % (mid("sg_" + tp["id"]), tint(tp["color"], 0.92), tp["color"]))
    return "\n".join(L + mermaid_classes()) + "\n"


def story_map_table(m):
    """Backbone: personas (rows) x flows (columns), each cell lists story ids with a status dot."""
    cols = [(f["id"], f["title"]) for f in m["flows"]]
    if any(u["flow_eff"] not in m["F"] for u in m["stories"]):
        cols.append(("", "Unassigned"))
    L = ["| Persona | " + " | ".join(esc_md(t) for _, t in cols) + " |", "|---|" + "---|" * len(cols)]
    for p in m["personas"]:
        row = []
        for fid, _ in cols:
            us = [u for u in m["stories"] if u["persona"] == p["id"] and (u["flow_eff"] if u["flow_eff"] in m["F"] else "") == fid]
            row.append("<br/>".join("%s %s" % (STATUS.get(u["status"], {}).get("emoji", "?"), esc_md(u["id"])) for u in us))
        L.append("| **%s** | %s |" % (esc_md(p["name"]), " | ".join(row)))
    return "\n".join(L)


def gen_mermaid(m, gen, render=True, sources=True, legacy=True):
    files = []
    md = ["# %s - story map" % m["app"]["name"], "",
          "_Generated from `stories.yaml`. The diagrams below render on GitHub. Screens with real screenshots are in "
          "`flows/` (PNG) and `story-map.html`._", ""]
    if header_line(m):
        md += ["**%s**" % header_line(m), ""]
    if m["app"]["disclaimer"]:
        md += ["> " + m["app"]["disclaimer"], ""]
    md += ["Status: " + legend_md(), "", "## Architecture by topic", "",
           "Each box is a topic area; arrows show how users move between them.", "", topic_table_md(m), "",
           "```mermaid", mermaid_topics(m).rstrip(), "```", "", "### Screens grouped by topic", "",
           "```mermaid", mermaid_architecture(m).rstrip(), "```", "",
           "## Story map (personas x flows)", "", story_map_table(m), "",
           "## Flows overview", "", "```mermaid", mermaid_overview(m).rstrip(), "```", ""]
    if sources:
        write(os.path.join(gen, "mermaid", "architecture.mmd"), mermaid_architecture(m))
        write(os.path.join(gen, "mermaid", "topics.mmd"), mermaid_topics(m))
        write(os.path.join(gen, "mermaid", "00-overview.mmd"), mermaid_overview(m))
    for i, f in enumerate(m["flows"], 1):
        txt = mermaid_flow(m, f["id"])
        if sources:
            write(os.path.join(gen, "mermaid", "%02d-%s.mmd" % (i, f["id"])), txt)
        md += ["## %s" % f["title"], ""]
        if f["description"]:
            md += [f["description"], ""]
        md += ["```mermaid", txt.rstrip(), "```", ""]
    if legacy:
        write(os.path.join(gen, "story-map.md"), "\n".join(md))
    if sources and render and shutil.which("mmdc"):
        for fn in sorted(os.listdir(os.path.join(gen, "mermaid"))):
            if fn.endswith(".mmd"):
                src = os.path.join(gen, "mermaid", fn)
                subprocess.run(["mmdc", "-i", src, "-o", src[:-4] + ".png", "-b", TH["bg"]],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return files


# --------------------------------------------------------------------------- images
PORTRAIT_H, LANDSCAPE_W = 520, 560   # size of a screen inside diagrams (points); thumbs are made at 2x
_img_cache = {}


def img_size(path):
    """(width, height) of a PNG/JPEG without needing Pillow."""
    if HAVE_PIL:
        with Image.open(path) as im:
            return im.size
    with open(path, "rb") as f:
        b = f.read(65536)
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    i = 2
    while b[:2] == b"\xff\xd8" and i + 9 < len(b):  # JPEG: find a SOF marker
        if b[i] != 0xFF:
            i += 1
            continue
        mk = b[i + 1]
        if mk in range(0xC0, 0xD0) and mk not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(b[i + 2:i + 4], "big")
    return 390, 844


def contain(w, h, bw, bh):
    """Largest (w', h') with the aspect ratio of (w, h) that fits inside (bw, bh): scale to fit, never crop or stretch."""
    if w <= 0 or h <= 0:
        return max(1, int(bw)), max(1, int(bh))
    k = min(bw / w, bh / h)
    return max(1, int(w * k + 0.5)), max(1, int(h * k + 0.5))


def fit_pt(w, h):
    """Size (points) of a screen inside a diagram node. Derived from the image's real aspect ratio, so a phone
    (portrait), a landscape or square screen, a tablet or a web page each get a node of their own shape:
    the image is scaled to fit a LANDSCAPE_W x PORTRAIT_H box (contain), never cropped or stretched."""
    return contain(w, h, LANDSCAPE_W, PORTRAIT_H)


def paste_contain(canvas, im, box, resample=None):
    """Paste `im` scaled to fit inside box=(x0, y0, x1, y1), centred, aspect preserved. Returns the pasted rectangle."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    w, h = contain(im.width, im.height, bw, bh)
    x, y = box[0] + (bw - w) // 2, box[1] + (bh - h) // 2
    canvas.paste(im.resize((w, h), resample or Image.LANCZOS), (x, y))
    return (x, y, x + w, y + h)


def load_img(m, s):
    if not HAVE_PIL or not image_exists(m, s):
        return None
    p = image_path(m, s)
    if p not in _img_cache:
        try:
            im = Image.open(p)
            im.load()
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.split()[-1])
                im = bg
            _img_cache[p] = im.convert("RGB")
        except Exception as ex:  # corrupt screenshot: treat as missing
            print("  warn  cannot read %s: %s" % (p, ex))
            _img_cache[p] = None
    return _img_cache[p]


# --------------------------------------------------------------------------- device frames
# Every screenshot is shown inside a device mockup: bezel, rounded corners, camera cut-out, side buttons, soft shadow.
# The frames are drawn procedurally with Pillow (supersampled, then downsampled) - no third-party artwork is bundled.
# Optionally a user can drop in their own licensed frame PNG through `frames.json` (see THIRD-PARTY-NOTICES.md).
PHONE_LIKE = ("iphone-island", "iphone-notch", "iphone-home-button", "android-generic", "tablet")
SS = 3  # supersampling factor for drawing

# per-model proportions, all as a fraction of the screen width
_GEOM = {
    "iphone-island":      dict(bez=0.026, band=0.014, top=0.0,   bot=0.0,   rs=0.140),
    "iphone-notch":       dict(bez=0.030, band=0.014, top=0.0,   bot=0.0,   rs=0.125),
    "iphone-home-button": dict(bez=0.050, band=0.010, top=0.150, bot=0.160, rs=0.012),
    "android-generic":    dict(bez=0.024, band=0.007, top=0.0,   bot=0.0,   rs=0.080),
    "tablet":             dict(bez=0.045, band=0.008, top=0.0,   bot=0.0,   rs=0.030),
    "browser-window":     dict(bez=0.0,   band=0.003, top=0.0,   bot=0.0,   rs=0.0),
    "none":               dict(bez=0.0,   band=0.0,   top=0.0,   bot=0.0,   rs=0.0),
}
_STYLES = {  # frame band, rim highlight, bezel glass, buttons, browser chrome, chrome text
    "black":    dict(band=(52, 52, 56), rim=(96, 96, 104), glass=(7, 7, 9), btn=(40, 40, 44), chrome=(46, 47, 52), chrome2=(70, 72, 80)),
    "titanium": dict(band=(150, 146, 140), rim=(206, 202, 196), glass=(9, 9, 11), btn=(128, 124, 119), chrome=(222, 221, 218), chrome2=(244, 243, 241)),
    "light":    dict(band=(232, 230, 226), rim=(255, 255, 255), glass=(14, 14, 16), btn=(214, 212, 208), chrome=(240, 240, 242), chrome2=(255, 255, 255)),
}
# pixel sizes of notch iPhones (X ... 14); other tall iPhone screenshots are treated as Dynamic Island devices
_NOTCH_SIZES = {(1125, 2436), (828, 1792), (1242, 2688), (1170, 2532), (1284, 2778), (1080, 2340)}
_DEV_CACHE = {}


def load_frames(m):
    """User-supplied frames from frames.json -> {'frames': {name: spec}, 'defaults': {model: name}, 'dir': folder}.
    Looked up in: theme.device.frames (relative path inside the folder), $STORYMAP_FRAMES, <folder>/frames.json,
    ~/.cache/storymap/frames/frames.json. Nothing is bundled and nothing is downloaded."""
    if "_frames" in m:
        return m["_frames"]
    out = dict(frames={}, defaults={}, dir="")
    cands = []
    rel = TH["device"].get("frames", "") if TH.get("device") else ""
    if rel:
        if os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/"):
            print("  note  theme.device.frames must be a relative path inside the folder; ignoring '%s'" % rel)
        else:
            cands.append(os.path.join(m["root"], rel))
    if os.environ.get("STORYMAP_FRAMES"):
        cands.append(os.environ["STORYMAP_FRAMES"])
    cands += [os.path.join(m["root"], "frames.json"), os.path.join(FRAME_CACHE, "frames.json")]
    for c in cands:
        if os.path.isfile(c):
            try:
                with open(c, encoding="utf-8") as f:
                    j = json.load(f)
                out["dir"] = os.path.dirname(os.path.abspath(c))
                for name, spec in (j.get("frames") or {}).items():
                    sc = spec.get("screen") or {}
                    if spec.get("image") and all(k in sc for k in ("x", "y", "width", "height")):
                        out["frames"][name.lower()] = spec
                out["defaults"] = {k: v.lower() for k, v in (j.get("defaults") or {}).items()}
                break
            except Exception as ex:
                print("  note  cannot read %s (%s); using the built-in frames" % (c, ex.__class__.__name__))
    m["_frames"] = out
    return out


FRAME_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "storymap", "frames")


def detect_model(m, s, w, h):
    """Device for a screen: screen `device:` > app `device:` > theme.device.model > guess from platform and screenshot size."""
    for v in (s.get("device"), m["app"].get("device"), TH["device"]["model"]):
        if v:
            return v
    plat, a = m["app"]["platform"], (w / h if h else 1.0)
    if plat == "web":
        return "browser-window"
    p = min(a, 1 / a) if a else 1
    if 0.40 <= p <= 0.50:
        if plat == "android":
            return "android-generic"
        return "iphone-notch" if (min(w, h), max(w, h)) in _NOTCH_SIZES else "iphone-island"
    if 0.50 < p <= 0.60:
        return "android-generic" if plat == "android" else "iphone-home-button"
    if 0.60 < p <= 0.80:
        return "tablet"
    return "browser-window"


def _frame_for(m, name_or_model):
    fr = load_frames(m)
    name = (name_or_model or "").lower()
    if name in fr["frames"]:
        return name
    return fr["defaults"].get(name)


def device_geom(model, imw, imh, bw, bh, shadow=True):
    """Pixel geometry of a device whose screen shows an imw x imh screenshot (aspect preserved, nothing cropped),
    scaled to fit inside the box bw x bh. Landscape phones/tablets use a rotated frame."""
    g = _GEOM.get(model, _GEOM["none"])
    rot = model in PHONE_LIKE and imw > imh
    if rot:
        imw, imh, bw, bh = imh, imw, bh, bw

    def dims(sw):
        sh = max(1, int(round(sw * imh / imw)))
        e = int(round((g["bez"] + g["band"]) * sw))
        tb = max(26, int(round(0.045 * sw))) if model == "browser-window" else 0
        t, b = e + int(round(g["top"] * sw)) + tb, e + int(round(g["bot"] * sw))
        M = 0 if (model == "none" or not shadow) else max(3, int(round(0.04 * sw)))
        if model == "browser-window":
            rout = max(8, int(round(0.012 * sw)))
            rin = max(0, rout - e)
        else:
            rin = int(round(g["rs"] * sw))
            rout = rin + e
        return dict(sw=sw, sh=sh, e=e, t=t, b=b, tb=tb, M=M, W=sw + 2 * e, H=sh + t + b, rin=rin, rout=rout)
    lo, hi, best = 4, max(4, int(bw)), dims(4)
    while lo <= hi:
        mid = (lo + hi) // 2
        d = dims(mid)
        if d["W"] + 2 * d["M"] <= bw and d["H"] + 2 * d["M"] <= bh:
            best, lo = d, mid + 1
        else:
            hi = mid - 1
    best.update(model=model, rot=rot, TW=best["W"] + 2 * best["M"], TH=best["H"] + 2 * best["M"])
    x, y = best["M"] + best["e"], best["M"] + best["t"]
    if rot:  # rotate 90 deg counter-clockwise: (x, y, w, h) -> (y, TW - x - w, h, w)
        best["size"] = (best["TH"], best["TW"])
        best["rect"] = (y, best["TW"] - x - best["sw"], best["sh"], best["sw"])
    else:
        best["size"] = (best["TW"], best["TH"])
        best["rect"] = (x, y, best["sw"], best["sh"])
    return best


def _rrect(d, box, r, **kw):
    d.rounded_rectangle(box, max(0, r), **kw)


def _overlay(geo, style, S=SS):
    """Frame with a transparent screen hole, portrait orientation (rotated afterwards for landscape)."""
    st = _STYLES.get(style, _STYLES["black"])
    model, sw, sh, e, t, b, M, W, H = (geo[k] for k in ("model", "sw", "sh", "e", "t", "b", "M", "W", "H"))
    TW, TH = geo["TW"], geo["TH"]
    big = Image.new("RGBA", (TW * S, TH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    ox, oy, ow, oh = M * S, M * S, W * S, H * S
    outer = (ox, oy, ox + ow - 1, oy + oh - 1)
    rout, rin = geo["rout"] * S, geo["rin"] * S
    if model == "none":
        return big
    # side buttons (drawn first; the body overlaps their inner half)
    p = max(1, int(round(0.010 * sw))) * S
    btn = st["btn"] + (255,)

    def button(side, y0, ln):
        y0, ln = oy + int(oh * y0), int(oh * ln)
        if side == "l":
            _rrect(d, (ox - p, y0, ox + p, y0 + ln), p // 2, fill=btn)
        else:
            _rrect(d, (ox + ow - 1 - p, y0, ox + ow - 1 + p, y0 + ln), p // 2, fill=btn)
    if model in ("iphone-island", "iphone-notch"):
        for y0, ln in ((0.115, 0.032), (0.17, 0.062), (0.25, 0.062)):
            button("l", y0, ln)
        button("r", 0.205, 0.095)
    elif model == "iphone-home-button":
        button("l", 0.105, 0.026)
        for y0, ln in ((0.16, 0.05), (0.225, 0.05)):
            button("l", y0, ln)
        button("r", 0.17, 0.075)
    elif model == "android-generic":
        button("r", 0.17, 0.05)
        button("r", 0.26, 0.10)
    elif model == "tablet":
        button("r", 0.012, 0.03)
    if model == "browser-window":
        _rrect(d, outer, rout, fill=st["chrome"] + (255,), outline=st["band"] + (255,), width=max(1, S))
    else:
        _rrect(d, outer, rout, fill=st["band"] + (255,))
        _rrect(d, outer, rout, outline=st["rim"] + (255,), width=max(1, S))
        bnd = int(round(0.013 * sw * S)) if model != "tablet" else int(round(0.008 * sw * S))
        _rrect(d, (ox + bnd, oy + bnd, ox + ow - 1 - bnd, oy + oh - 1 - bnd), rout - bnd, fill=st["glass"] + (255,))
    # punch the screen hole
    sx, sy = (M + e) * S, (M + t) * S
    hole = Image.new("L", big.size, 0)
    _rrect(ImageDraw.Draw(hole), (sx, sy, sx + sw * S - 1, sy + sh * S - 1), rin, fill=255)
    big.putalpha(ImageChops.subtract(big.getchannel("A"), hole))
    d = ImageDraw.Draw(big)
    black, cx = (0, 0, 0, 255), sx + sw * S // 2
    if model == "iphone-island":
        iw, ih = int(0.300 * sw * S), int(0.087 * sw * S)
        iy = sy + int(0.026 * sw * S)
        _rrect(d, (cx - iw // 2, iy, cx + iw // 2, iy + ih), ih // 2, fill=black)
        lr = int(0.017 * sw * S)
        d.ellipse((cx + iw // 2 - ih // 2 - lr, iy + ih // 2 - lr, cx + iw // 2 - ih // 2 + lr, iy + ih // 2 + lr), fill=(16, 20, 34, 255))
    elif model == "iphone-notch":
        nw, nh = int(0.50 * sw * S), int(0.066 * sw * S)
        d.rounded_rectangle((cx - nw // 2, sy - 2, cx + nw // 2, sy + nh), int(nh * 0.55), fill=black, corners=(False, False, True, True))
        d.rounded_rectangle((cx - int(0.085 * sw * S), sy + int(nh * 0.30), cx + int(0.085 * sw * S), sy + int(nh * 0.30) + max(2, int(0.011 * sw * S))),
                            max(1, int(0.005 * sw * S)), fill=(34, 34, 38, 255))
    elif model == "iphone-home-button":
        ty = oy + (t * S) // 2 - int(0.01 * sw * S)
        d.rounded_rectangle((cx - int(0.09 * sw * S), ty, cx + int(0.09 * sw * S), ty + int(0.016 * sw * S)), int(0.008 * sw * S), fill=(36, 36, 40, 255))
        cr = int(0.012 * sw * S)
        d.ellipse((cx - int(0.17 * sw * S) - cr, ty + int(0.008 * sw * S) - cr, cx - int(0.17 * sw * S) + cr, ty + int(0.008 * sw * S) + cr), fill=(30, 34, 46, 255))
        by = sy + sh * S + (b * S - int(0.012 * sw * S)) // 2 - int(0.008 * sw * S)
        hr = int(0.052 * sw * S)
        d.ellipse((cx - hr, by - hr + int(0.01 * sw * S), cx + hr, by + hr + int(0.01 * sw * S)), outline=(70, 70, 76, 255), width=max(2, S))
    elif model == "android-generic":
        r = int(0.019 * sw * S)
        d.ellipse((cx - r, sy + int(0.034 * sw * S) - r, cx + r, sy + int(0.034 * sw * S) + r), fill=black)
    elif model == "tablet":
        r = max(1, int(0.007 * sw * S))
        d.ellipse((cx - r, oy + (e * S) // 2 - r, cx + r, oy + (e * S) // 2 + r), fill=(40, 42, 50, 255))
    elif model == "browser-window":
        tb = geo["tb"] * S
        for i, c in enumerate(((236, 106, 94), (244, 190, 80), (98, 197, 84))):
            r = int(tb * 0.17)
            x = ox + int(tb * 0.55) + i * int(tb * 0.48)
            d.ellipse((x - r, oy + tb // 2 - r, x + r, oy + tb // 2 + r), fill=c + (255,))
        pw, ph = int(min(W * 0.46, W - 6 * tb) * S), int(tb * 0.56)
        if pw > tb * 2:
            _rrect(d, (ox + ow // 2 - pw // 2, oy + (tb - ph) // 2, ox + ow // 2 + pw // 2, oy + (tb + ph) // 2), ph // 2, fill=st["chrome2"] + (255,))
        d.line((ox + S, oy + tb, ox + ow - 1 - S, oy + tb), fill=st["band"] + (255,), width=max(1, S // 2))
    return big.convert("RGBa").resize((TW, TH), Image.LANCZOS).convert("RGBA")


def _shadow(geo, S=SS):
    """Soft drop shadow under the device outline."""
    M, W, H = geo["M"], geo["W"], geo["H"]
    if not M:
        return Image.new("RGBA", (geo["TW"], geo["TH"]), (0, 0, 0, 0))
    mask = Image.new("L", (geo["TW"], geo["TH"]), 0)
    dy = max(1, int(M * 0.35))
    ImageDraw.Draw(mask).rounded_rectangle((M, M + dy, M + W - 1, M + H - 1 + dy), geo["rout"], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(1.0, M * 0.45))).point(lambda v: int(v * 0.42))
    sh = Image.new("RGBA", mask.size, (10, 12, 20, 0))
    sh.putalpha(mask)
    return sh


def _user_frame(m, name):
    fr = load_frames(m)
    spec = fr["frames"].get(name)
    if not spec:
        return None
    key = ("uframe", fr["dir"], name)
    if key not in _DEV_CACHE:
        p = os.path.join(fr["dir"], spec["image"])
        try:
            _DEV_CACHE[key] = Image.open(p).convert("RGBA")
        except Exception as ex:
            print("  note  cannot open frame image %s (%s); using the built-in frame" % (p, ex.__class__.__name__))
            _DEV_CACHE[key] = None
    return _DEV_CACHE[key]


def render_device(m, s, im, model, box, scale=1, shadow=True):
    """Screenshot (PIL RGB) inside a device frame fitted to box (w, h) in points -> dict(img, ov, rect, size, model).
    img = RGBA device with shadow; ov = frame only (transparent screen); rect = screen rectangle (x, y, w, h) inside img."""
    style = TH["device"]["style"] if TH["device"]["style"] in DEVICE_STYLES else "auto"
    if style == "auto":      # a dark frame vanishes on a dark page: use the light titanium frame there
        style = "titanium" if TH.get("dark") else "black"
    bw, bh = int(box[0] * scale), int(box[1] * scale)
    fname = _frame_for(m, s.get("device") or "") or _frame_for(m, m["app"].get("device") or TH["device"]["model"]) or (
        _frame_for(m, model) if not (s.get("device") or m["app"].get("device") or TH["device"]["model"]) else None)
    uf = _user_frame(m, fname) if fname else None
    key = (id(im), im.size, model, style, bw, bh, bool(shadow), fname if uf is not None else "")
    if key in _DEV_CACHE:
        return _DEV_CACHE[key]
    if uf is not None:
        out = _render_user_frame(m, im, uf, load_frames(m)["frames"][fname], bw, bh, shadow)
    else:
        geo = device_geom(model, im.width, im.height, bw, bh, shadow)
        ov = _overlay(geo, style)
        shot = im.rotate(-90, expand=True) if geo["rot"] else im
        canvas = _shadow(geo)
        scr = shot.resize((geo["sw"], geo["sh"]), Image.LANCZOS).convert("RGBA")
        if geo["rin"] > 0:  # the screen has rounded corners: clip the (square) screenshot to them
            k3 = Image.new("L", (geo["sw"] * 3, geo["sh"] * 3), 0)
            ImageDraw.Draw(k3).rounded_rectangle((0, 0, geo["sw"] * 3 - 1, geo["sh"] * 3 - 1), geo["rin"] * 3, fill=255)
            scr.putalpha(k3.resize(scr.size, Image.LANCZOS))
        canvas.alpha_composite(scr, (geo["M"] + geo["e"], geo["M"] + geo["t"]))
        canvas.alpha_composite(ov)
        if geo["rot"]:
            canvas, ov = canvas.rotate(90, expand=True), ov.rotate(90, expand=True)
        out = dict(img=canvas, ov=ov, rect=geo["rect"], size=geo["size"], model=model, style=style, rin=geo["rin"])
    _DEV_CACHE[key] = out
    return out


def _render_user_frame(m, im, frame, spec, bw, bh, shadow):
    sc = spec["screen"]
    sx, sy, swd, sht = (int(float(sc[k])) for k in ("x", "y", "width", "height"))
    rad = int(float(sc.get("radius", 0)))
    FW, FH = frame.size
    if im.width > im.height and FH > FW:  # landscape screenshot, portrait frame: rotate the frame (counter-clockwise)
        frame = frame.rotate(90, expand=True)
        sx, sy, swd, sht = sy, FW - sx - swd, sht, swd
        FW, FH = frame.size
    M0 = max(3, int(0.04 * min(FW, FH) * 0.35)) if shadow else 0
    k = min((bw - 2 * (M0 and 4)) / FW, (bh - 2 * (M0 and 4)) / FH)
    M = max(3, int(round(0.04 * FW * k))) if shadow else 0
    k = min((bw - 2 * M) / FW, (bh - 2 * M) / FH)
    nw, nh = max(1, int(FW * k)), max(1, int(FH * k))
    ov = frame.convert("RGBa").resize((nw, nh), Image.LANCZOS).convert("RGBA")
    rx, ry, rw, rh = (int(round(v * k)) for v in (sx, sy, swd, sht))
    TW, TH = nw + 2 * M, nh + 2 * M
    canvas = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    if M:
        mask = Image.new("L", (TW, TH), 0)
        mask.paste(ov.getchannel("A"), (M, M + max(1, int(M * 0.35))))
        mask = mask.filter(ImageFilter.GaussianBlur(max(1.0, M * 0.45))).point(lambda v: int(v * 0.42))
        sh = Image.new("RGBA", (TW, TH), (10, 12, 20, 0))
        sh.putalpha(mask)
        canvas.alpha_composite(sh)
    scr = Image.new("RGBA", (rw, rh), (0, 0, 0, 255))
    w2, h2 = contain(im.width, im.height, rw, rh)  # whole screenshot inside the screen area, aspect preserved
    scr.alpha_composite(im.resize((w2, h2), Image.LANCZOS).convert("RGBA"), ((rw - w2) // 2, (rh - h2) // 2))
    m_ = Image.new("L", (rw * 3, rh * 3), 0)
    ImageDraw.Draw(m_).rounded_rectangle((0, 0, rw * 3 - 1, rh * 3 - 1), int(rad * k * 3), fill=255)
    scr.putalpha(m_.resize((rw, rh), Image.LANCZOS))
    canvas.alpha_composite(scr, (M + rx, M + ry))
    full_ov = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    full_ov.alpha_composite(ov, (M, M))
    canvas.alpha_composite(full_ov)
    return dict(img=canvas, ov=full_ov, rect=(M + rx, M + ry, rw, rh), size=(TW, TH), model="frame", style="user", rin=int(rad * k))


def device_box_width(m, s, im, th):
    """Width of the device (frame and margins) that shows screen s at height th."""
    if im is None:
        model = s.get("device") or m["app"].get("device") or TH["device"]["model"]
        plat = m["app"]["platform"]
        if model not in DEVICE_MODELS or not model:
            model = "browser-window" if plat == "web" else ("android-generic" if plat == "android" else "iphone-island")
        iw, ih = (1440, 900) if model == "browser-window" else ((1640, 2360) if model == "tablet" else (1206, 2622))
        return device_geom(model, iw, ih, 10 ** 5, th, True)["size"][0]
    fname = _frame_for(m, s.get("device") or m["app"].get("device") or TH["device"]["model"])
    if fname and _user_frame(m, fname) is not None:
        fw, fh = _user_frame(m, fname).size
        k = th / fh if not (im.width > im.height and fh > fw) else th / fw
        return int((fw if k == th / fh else fh) * k)
    return device_geom(detect_model(m, s, im.width, im.height), im.width, im.height, 10 ** 5, th, True)["size"][0]


def badge_img(status, scale=1, label=True):
    """Small pill: coloured dot + status label (no coloured border around the device)."""
    stv = STATUS[status]
    S2 = 3
    f = font(int(15 * scale * S2 / 1.0), True)
    txt = stv["label"]
    tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    pad, dot = int(9 * scale * S2), int(8 * scale * S2)
    tw_ = int(tw(tmp, txt, f)) if label else 0
    w = pad * 2 + dot * 2 + (int(7 * scale * S2) + tw_ if label else 0)
    h = int(26 * scale * S2)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=None, outline=hexrgb(TH["border"]) + (255,), width=max(1, S2 // 2 + 1))   # outline only: no fill, the pill sits on the lane
    cy = h // 2
    d.ellipse((pad, cy - dot, pad + dot * 2, cy + dot), fill=hexrgb(stv["color"]) + (255,))
    if label:
        d.text((pad + dot * 2 + int(7 * scale * S2), cy), txt, font=f, fill=hexrgb(TH["ink2"]) + (255,), anchor="lm")
    return im.resize((max(1, w // S2), max(1, h // S2)), Image.LANCZOS)


def _dashed_path(d, pts, color, width, dash, gap):
    import math
    pos, on = 0.0, True
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        L = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < L:
            seg = min(dash if on else gap, L - t) if True else 0
            if on:
                d.line((x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L, x0 + (x1 - x0) * (t + seg) / L, y0 + (y1 - y0) * (t + seg) / L), fill=color, width=width)
            t += seg
            if seg >= (dash if on else gap) - 1e-6:
                on = not on


def _rrect_pts(x0, y0, x1, y1, r, step=6):
    import math
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        n = max(2, int(r * math.pi / 2 / step))
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def placeholder_device(m, s, box, scale=1):
    """Not-captured screen: an empty, dashed device outline with the reason inside."""
    reason = s["not_captured"] or "screenshot missing"
    plat = m["app"]["platform"]
    model = (s.get("device") or m["app"].get("device") or TH["device"]["model"] or "")
    if model not in DEVICE_MODELS:
        model = ""
    if not model:
        model = "browser-window" if plat == "web" else ("android-generic" if plat == "android" else "iphone-island")
    iw, ih = (1440, 900) if model == "browser-window" else ((1640, 2360) if model == "tablet" else (1206, 2622))
    geo = device_geom(model, iw, ih, int(box[0] * scale), int(box[1] * scale), True)
    S = 3
    TW, TH_ = geo["TW"], geo["TH"]
    big = Image.new("RGBA", (TW * S, TH_ * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    M, W, H = geo["M"], geo["W"], geo["H"]
    col = hexrgb(TH["gray"]) + (255,)
    dash = max(10, int(0.035 * geo["sw"] * S))
    wd = max(2, int(0.008 * geo["sw"] * S))
    _dashed_path(d, _rrect_pts(M * S, M * S, (M + W) * S, (M + H) * S, geo["rout"] * S), col, wd, dash, dash)
    x, y = (M + geo["e"]) * S, (M + geo["t"]) * S
    _dashed_path(d, _rrect_pts(x, y, x + geo["sw"] * S, y + geo["sh"] * S, max(4, geo["rin"] * S)), hexrgb(TH["border"]) + (255,), max(1, wd // 2), dash // 2, dash // 2)
    img = big.convert("RGBa").resize((TW, TH_), Image.LANCZOS).convert("RGBA")
    if geo["rot"]:
        pass
    d2 = ImageDraw.Draw(img)
    rx, ry, rw, rh = geo["sw"] and (M + geo["e"], M + geo["t"], geo["sw"], geo["sh"])
    fz = max(9, int(rw * 0.085))
    f1, f2 = font(fz, True), font(max(8, int(fz * 0.82)))
    d2.text((rx + rw // 2, ry + int(rh * 0.40)), "Not captured", font=f1, fill=hexrgb(TH["muted"]) + (255,), anchor="mm")
    lines = wrap_px(d2, reason, f2, int(rw * 0.84))[:7]
    for i, ln in enumerate(lines):
        d2.text((rx + rw // 2, ry + int(rh * 0.40) + int(fz * 1.5) + i * int(fz * 1.1)), ln, font=f2, fill=hexrgb(TH["muted2"]) + (255,), anchor="mm")
    if geo["rot"]:
        img = img.rotate(90, expand=True)
    return dict(img=img, ov=None, rect=geo["rect"], size=geo["size"], model=model, style="placeholder", rin=0)


def screen_device(m, s, box, scale=1, shadow=True):
    """Framed device image for a screen (real screenshot or dashed placeholder); None without Pillow."""
    if not HAVE_PIL:
        return None
    im = load_img(m, s) if image_exists(m, s) else None
    if im is None:
        return placeholder_device(m, s, box, scale)
    dv = render_device(m, s, im, detect_model(m, s, im.width, im.height), box, scale, shadow)
    RES_LOG.append((_CTX["diagram"], s["id"], dv["rect"][2], dv["rect"][3], im.width, im.height))
    return dv


# --------------------------------------------------------------------------- resolution rule
# Every screenshot in every generated diagram is drawn at >= its native pixels (scale >= 1.0), so zooming in reads all its text.
# The diagram renderers therefore take a zoom factor `z` (1.0 = the compact design size) chosen by native_zoom().
RES_LOG = []                 # (diagram, screen id, rendered screen w, h, source w, h) for every framed screenshot drawn
_CTX = {"diagram": "other"}


def set_diagram(name):
    _CTX["diagram"] = name


def resolution_report():
    """{diagram: min scale} over the screenshots drawn in it (scale = rendered screen width / source width)."""
    out = {}
    for dg, sid, rw, rh, iw, ih in RES_LOG:
        if dg == "other" or not iw or not ih:
            continue
        k = min(rw / iw, rh / ih)
        out[dg] = min(out.get(dg, 9e9), k)
    return out


def _scale_at(m, s, im, bw, bh):
    """Scale (rendered screen width / source width) of screen s in a device fitted to the box bw x bh pixels."""
    model = detect_model(m, s, im.width, im.height)
    fname = _frame_for(m, s.get("device") or m["app"].get("device") or TH["device"]["model"])
    if fname and _user_frame(m, fname) is not None:
        r = render_device(m, s, im, model, (bw, bh), 1, True)["rect"]
        return r[2] / im.width
    geo = device_geom(model, im.width, im.height, int(bw), int(bh), True)
    return min(geo["sw"] / (im.height if geo["rot"] else im.width), geo["sh"] / (im.width if geo["rot"] else im.height))


def native_zoom(m, box, zmin=1.0):
    """Smallest zoom z >= zmin such that every captured screenshot, drawn in a device fitted to box*z pixels, shows
    its screen at >= 1.0x of its source pixels."""
    if not HAVE_PIL:
        return zmin
    shots = [im for im in (load_img(m, s) if image_exists(m, s) else None for s in m["screens"]) if im is not None]
    if not shots:
        return zmin
    pairs = [(s, load_img(m, s)) for s in m["screens"] if image_exists(m, s) and load_img(m, s) is not None]
    z = zmin
    for _ in range(40):
        worst = min(_scale_at(m, s, im, box[0] * z, box[1] * z) for s, im in pairs)
        if worst >= 1.004:      # a hair above 1.0 so pixel rounding never leaves a screenshot just under native
            return round(z, 3)
        z *= max(1.01, 1.0 / max(worst, 1e-3)) ** 0.98 if worst < 0.9 else 1.01
    return round(z, 3)


def ensure_gitignore(root, patterns=(".cache/",)):
    """Append missing local-only patterns without replacing the caller's ignore rules."""
    path = os.path.join(root, ".gitignore")
    original = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            original = f.read()
    lines = original.splitlines()
    missing = [pattern for pattern in patterns if pattern not in lines]
    if missing:
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            if original and not original.endswith(("\n", "\r")):
                f.write("\n")
            f.write("\n".join(missing) + "\n")


def make_thumbs(m, gen):
    """Framed DOT node images in DIR/.cache/thumbs/; paths are relative to generated/dot.
    The transparent PNG is drawn at 2x; the cache is created only for DOT/Graphviz."""
    out = {}
    tdir = os.path.join(m["root"], ".cache", "thumbs")
    if HAVE_PIL and m["screens"]:
        os.makedirs(tdir, exist_ok=True)
        ensure_gitignore(m["root"])
    for s in m["screens"]:
        if HAVE_PIL:
            dv = screen_device(m, s, (LANDSCAPE_W, PORTRAIT_H), 2)
            tp = os.path.join(tdir, s["id"] + ".png")
            dv["img"].save(tp, optimize=True)
            out[s["id"]] = (os.path.relpath(tp, os.path.join(gen, "dot")).replace("\\", "/"), dv["size"][0] // 2, dv["size"][1] // 2, True)
        elif image_exists(m, s):
            try:
                w, h = img_size(image_path(m, s))
            except Exception:
                continue
            wpt, hpt = fit_pt(w, h)
            out[s["id"]] = (os.path.relpath(image_path(m, s), os.path.join(gen, "dot")).replace("\\", "/"), wpt, hpt, False)
    return out


# --------------------------------------------------------------------------- graphviz
def dq(t):
    return html.escape(str(t), quote=True)


def dwrap(t, n):
    return "<BR/>".join(dq(x) for x in textwrap.wrap(str(t), n)) if t else ""


def dot_badge_row(s, cw):
    """Status badge under a device: a coloured dot plus the label (no coloured border)."""
    stv = STATUS[s["status"]]
    lab = ' <FONT POINT-SIZE="15" COLOR="#3C4043"><B>%s</B></FONT>' % dq(stv["label"]) if TH["device"]["badge"] == "label" else ""
    return '<TR><TD WIDTH="%d"><FONT POINT-SIZE="17" COLOR="%s">&#9679;</FONT>%s</TD></TR>' % (cw, stv["color"], lab)


def dot_node(s, th, key=None):
    if th and len(th) > 3 and th[3]:  # framed device: title, device picture (the node image), status badge
        w, h = th[1], th[2]
        cw = max(w, 240)
        name = '<TR><TD WIDTH="%d"><FONT POINT-SIZE="20"><B>%s</B></FONT></TD></TR>' % (cw, dwrap(s["title"], max(14, cw // 9)))
        pic = ('<TR><TD><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>'
               '<TD FIXEDSIZE="TRUE" WIDTH="%d" HEIGHT="%d"><IMG SCALE="TRUE" SRC="%s"/></TD></TR></TABLE></TD></TR>' % (w, h, dq(th[0])))
        sid = '<TR><TD><FONT POINT-SIZE="12" COLOR="#80868B">%s</FONT></TD></TR>' % dq(s["id"])
        tbl = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">%s%s%s%s</TABLE>>' % (name, pic, dot_badge_row(s, cw), sid)
        return '  "%s" [label=%s tooltip="%s"];' % (key or s["id"], tbl, dq(s["title"]))
    stv = STATUS[s["status"]]
    if th:
        w, h = th[1], th[2]
        # cell = picture + a 4pt margin each side, so the picture fills its content box exactly (no squeeze, no clipping)
        body = '<TD FIXEDSIZE="TRUE" WIDTH="%d" HEIGHT="%d" CELLPADDING="4"><IMG SCALE="TRUE" SRC="%s"/></TD>' % (w + 8, h + 8, dq(th[0]))
    else:
        w, h = 240, 150
        body = '<TD WIDTH="%d" HEIGHT="%d" BGCOLOR="#F1F3F4"><FONT POINT-SIZE="15" COLOR="#5F6368">%s</FONT></TD>' % (
            w, h, dwrap("Not captured: " + (s["not_captured"] or "screenshot missing"), 28))
    cw = max(w, 240)
    head = '<TR><TD WIDTH="%d" BGCOLOR="%s"><FONT COLOR="white" POINT-SIZE="15"><B>%s</B></FONT></TD></TR>' % (
        cw, stv["color"], dq(stv["label"].upper()))
    name = '<TR><TD BGCOLOR="white"><FONT POINT-SIZE="20"><B>%s</B></FONT></TD></TR>' % dwrap(s["title"], max(14, cw // 9))
    sid = '<TR><TD BGCOLOR="white"><FONT POINT-SIZE="12" COLOR="#80868B">%s</FONT></TD></TR>' % dq(s["id"])
    style = "rounded" if th else "dashed"
    tbl = '<<TABLE BORDER="3" COLOR="%s" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" STYLE="%s">%s%s<TR>%s</TR>%s</TABLE>>' % (
        stv["color"], style, head, name, body, sid)
    return '  "%s" [label=%s tooltip="%s"];' % (key or s["id"], tbl, dq(s["title"]))


def dot_text(text):
    """Apply theme colours and font to generated Graphviz source."""
    text = themeify(text)
    return text.replace('fontname="Helvetica"', 'fontname="%s"' % (TH["font"] or "Helvetica"))


def dot_header(title, sub="", rankdir="LR"):
    face = ' FACE="%s"' % dq(TH["heading_font"]) if TH["heading_font"] else ""
    lab = '<FONT POINT-SIZE="40"%s><B>%s</B></FONT>' % (face, dq(title))
    if sub:
        lab += '<BR/><FONT POINT-SIZE="18" COLOR="#5F6368">%s</FONT><BR/> ' % dq(sub)
    return ['digraph G {',
            '  graph [rankdir=%s bgcolor="#FFFFFF" fontcolor="#202124" fontname="Helvetica" nodesep=0.5 ranksep=1.0 pad=0.5 '
            'labelloc=t labeljust=l label=<%s>];' % (rankdir, lab),
            '  node [shape=plain fontname="Helvetica" fontcolor="#202124"];',
            '  edge [fontname="Helvetica" fontsize=19 color="#2D7A5C" fontcolor="#1F5A43" penwidth=2.6 arrowsize=1.3];']


def dot_edge(a, b, lab, dashed):
    st = ' style=dashed color="#9AA0A6" fontcolor="#5F6368"' if dashed else ""
    l = ' label=<<B>%s</B>>' % dwrap(lab, 22) if lab else ""
    return '  "%s" -> "%s" [%s%s];' % (a, b, l.strip(), st)


def dot_portal(key, text, kind):
    col = TC("#FFE9DD") if kind == "out" else TC("#DDF1E8")
    return ('  "%s" [shape=box style="rounded,filled" fillcolor="%s" color="#2D7A5C" penwidth=2 fontsize=20 '
            'margin="0.25,0.15" label=<%s>];' % (key, col, dwrap(text, 26)))


def dot_flow(m, fid, thumbs):
    f = m["F"][fid]
    nodes, edges = flow_graph(m, fid)
    keys = [n["key"] for n in nodes]
    widest = max([len(c) for c in layer_columns(keys, edges, 99)] or [1])
    # a fan-out (one screen leading to many) is far more compact top-to-bottom than left-to-right
    L = dot_header(f["title"], f["description"], "TB" if widest >= 5 else "LR")
    for n in nodes:
        L.append(dot_node(n["screen"], thumbs.get(n["screen"]["id"]), n["key"]) if n["kind"] == "screen"
                 else dot_portal(n["key"], n["label"], n["kind"][7:]))
    L += [dot_edge(*e) for e in edges]
    return "\n".join(L + ["}"]) + "\n"


def dot_full(m, thumbs):
    L = dot_header(m["app"]["name"] + " - every screen and how you get there", header_line(m))
    for f in m["flows"]:
        ss = [s for s in m["screens"] if s["flow"] == f["id"]]
        if not ss:
            continue
        tc = m["T"][f["topic"]]["color"] if f["topic"] in m["T"] else TH["border_accent"]
        L.append('  subgraph "cluster_%s" { label=<<FONT POINT-SIZE="30"><B>%s</B></FONT>> style="rounded,filled" '
                 'fillcolor="%s" color="%s" penwidth=3 margin=22;' % (f["id"], dq(f["title"]), tint(tc, 0.93), tc))
        L += [dot_node(s, thumbs.get(s["id"])) for s in ss]
        L.append("  }")
    for e in m["edges"]:
        if e["src"] in m["S"] and e["dst"] in m["S"]:
            L.append(dot_edge(e["src"], e["dst"], e["label"], e["dashed"]))
    return "\n".join(L + ["}"]) + "\n"


def dot_overview(m, thumbs=None):
    L = dot_header(m["app"]["name"] + " - flows overview", header_line(m))
    for f in m["flows"]:
        us = [u for u in m["stories"] if u["flow_eff"] == f["id"]]
        ns = sum(1 for s in m["screens"] if s["flow"] == f["id"])
        c = counts(us)
        chips = "".join('<TD BGCOLOR="%s" CELLPADDING="5"><FONT COLOR="white" POINT-SIZE="18"><B>%d %s</B></FONT></TD>' % (
            STATUS[k]["color"], n, k) for k, n in c.items() if n) or '<TD><FONT POINT-SIZE="16">no stories</FONT></TD>'
        minis = ""
        fs = [x for x in m["screens"] if x["flow"] == f["id"] and thumbs and thumbs.get(x["id"]) and thumbs[x["id"]][3]][:4]
        if fs:  # a few of the flow's screens, each inside its device frame
            cells = "".join('<TD FIXEDSIZE="TRUE" WIDTH="%d" HEIGHT="%d"><IMG SCALE="TRUE" SRC="%s"/></TD>' % (
                max(1, round(thumbs[x["id"]][1] * 0.3)), max(1, round(thumbs[x["id"]][2] * 0.3)), dq(thumbs[x["id"]][0])) for x in fs)
            minis = '<TR><TD COLSPAN="4"><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="0"><TR>%s</TR></TABLE></TD></TR>' % cells
        lab = ('<<TABLE BORDER="3" COLOR="#2D7A5C" CELLBORDER="0" CELLSPACING="4" CELLPADDING="8" STYLE="rounded">'
               '<TR><TD COLSPAN="4"><FONT POINT-SIZE="26"><B>%s</B></FONT></TD></TR>'
               '<TR><TD COLSPAN="4"><FONT POINT-SIZE="17" COLOR="#5F6368">%d screens · %d stories</FONT></TD></TR>'
               '%s<TR>%s</TR></TABLE>>' % (dq(f["title"]), ns, len(us), minis, chips))
        L.append('  "%s" [label=%s];' % (f["id"], lab))
    for (fa, fb), lab in cross_flow_edges(m).items():
        L.append(dot_edge(fa, fb, lab, lab.startswith("(")))
    return "\n".join(L + ["}"]) + "\n"


def run_dot(dotfile, outpng, dpi):
    if not shutil.which("dot"):
        return False
    d = os.path.dirname(dotfile)
    try:
        r = subprocess.run(["dot", "-Tpng", "-Gdpi=%d" % dpi, os.path.basename(dotfile), "-o",
                            os.path.relpath(outpng, d)], cwd=d, capture_output=True, text=True, timeout=600, env=fontconfig_env())
    except Exception as ex:
        print("  warn  graphviz failed: %s" % ex)
        return False
    if r.returncode != 0:
        print("  warn  graphviz error: %s" % r.stderr.strip()[:200])
        return False
    return True


# --------------------------------------------------------------------------- Pillow fallback renderer
_FONTS = {}


def font(size, bold=False, heading=False):
    spec = TH["font_files"].get("head" if heading else "body")
    key = (size, bold, heading, spec[1 if bold else 0] if spec else None)
    if key in _FONTS:
        return _FONTS[key]
    if spec:
        try:
            _FONTS[key] = ImageFont.truetype(spec[1 if bold else 0], size)
            return _FONTS[key]
        except Exception:
            pass
    names = (["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
              "C:\\Windows\\Fonts\\arialbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
             if bold else
             ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
              "C:\\Windows\\Fonts\\arial.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"])
    f = None
    for n in names:
        try:
            f = ImageFont.truetype(n, size)
            break
        except Exception:
            continue
    if f is None:
        try:
            f = ImageFont.load_default(size)
        except TypeError:
            f = ImageFont.load_default()
    _FONTS[key] = f
    return f


def tw(draw, text, f):
    return draw.textlength(text, font=f)


def wrap_px(draw, text, f, maxw):
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split():
            t = (cur + " " + word).strip()
            if tw(draw, t, f) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def dashed_rect(d, box, color, width=3, dash=14):
    x0, y0, x1, y1 = box
    for x in range(int(x0), int(x1), dash * 2):
        d.line((x, y0, min(x + dash, x1), y0), fill=color, width=width)
        d.line((x, y1, min(x + dash, x1), y1), fill=color, width=width)
    for y in range(int(y0), int(y1), dash * 2):
        d.line((x0, y, x0, min(y + dash, y1)), fill=color, width=width)
        d.line((x1, y, x1, min(y + dash, y1)), fill=color, width=width)


def paste_rgba(card, im, xy):
    """Paste with the image's own transparency (works for RGB targets and for transparent RGBA cards)."""
    xy = (int(xy[0]), int(xy[1]))
    if im.mode != "RGBA":
        card.paste(im, xy)
    elif card.mode == "RGBA":
        card.alpha_composite(im, xy)
    else:
        card.paste(im, xy, im)


def card_screen(m, s, sc=1):
    """Diagram card: title, the screen inside its device frame, a status badge (dot + label) and the id. No coloured border.
    sc = output scale (the tree flow diagrams are drawn at 2x)."""
    dv = screen_device(m, s, (LANDSCAPE_W, PORTRAIT_H), sc)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    fT = font(int(22 * sc), True)
    badge = badge_img(s["status"], sc, TH["device"]["badge"] == "label")
    CW = max(dv["size"][0], int(240 * sc), badge.width) + int(16 * sc)
    tl = wrap_px(tmp, s["title"], fT, CW - int(16 * sc))
    CW = int(max(CW, max([tw(tmp, t, fT) for t in tl] or [0]) + 16 * sc))  # a long word must never be cut off
    H0 = dv["size"][1]
    lh = int(28 * sc)
    H = int(8 * sc) + lh * len(tl) + int(6 * sc) + H0 + int(4 * sc) + badge.height + int(8 * sc) + int(20 * sc) + int(6 * sc)
    card = Image.new("RGBA", (CW, H), (0, 0, 0, 0))     # transparent: no card behind the device
    d = ImageDraw.Draw(card)
    y = int(8 * sc)
    for ln in tl:
        d.text((CW // 2, y), ln, font=fT, fill=TC("#202124"), anchor="ma")
        y += lh
    y += int(6 * sc)
    paste_rgba(card, dv["img"], ((CW - dv["size"][0]) // 2, y))
    y += H0 + int(4 * sc)
    paste_rgba(card, badge, ((CW - badge.width) // 2, y))
    d.text((CW // 2, y + badge.height + int(8 * sc)), s["id"], font=font(int(14 * sc)), fill=TC("#80868B"), anchor="ma")
    return card


def card_portal(text, kind, sc=1):
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f = font(int(20 * sc))
    lines = wrap_px(tmp, text, f, int(260 * sc))
    H = int((24 + 26 * len(lines)) * sc)
    c = Image.new("RGB", (int(300 * sc), H), TC("#FFE9DD") if kind == "out" else TC("#DDF1E8"))
    d = ImageDraw.Draw(c)
    for i, ln in enumerate(lines):
        d.text((int(20 * sc), int(12 * sc) + i * int(26 * sc)), ln, font=f, fill=TC("#202124"))
    d.rectangle((0, 0, c.width - 1, H - 1), outline=TC("#2D7A5C"), width=max(1, int(3 * sc)))
    return c


def card_flow(m, f, z=1.0, zt=None):
    """Overview card of one flow: title, up to four of its screens in device frames, status chips. z = zoom of the
    screens (native resolution); zt = zoom of the text and spacing (default z; smaller keeps the overview compact)."""
    zt = z if zt is None else zt
    Z = lambda v: max(1, int(round(v * zt)))
    us = [u for u in m["stories"] if u["flow_eff"] == f["id"]]
    ns = sum(1 for s in m["screens"] if s["flow"] == f["id"])
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tl = wrap_px(tmp, f["title"], font(Z(28), True), Z(380))
    fs = [x for x in m["screens"] if x["flow"] == f["id"]][:4]
    minis = [screen_device(m, x, OVERVIEW_BOX, z) for x in fs]   # a few screens, each inside its device frame
    MH = (max(v["size"][1] for v in minis) + Z(6)) if minis else 0
    CWD = max(Z(420), sum(v["size"][0] + Z(2) for v in minis) + Z(32))
    H = Z(16) + Z(36) * len(tl) + Z(30) + MH + Z(44) + Z(14)
    c = Image.new("RGB", (CWD, H), TH["bg"])
    d = ImageDraw.Draw(c)
    y = Z(16)
    for ln in tl:
        d.text((Z(20), y), ln, font=font(Z(28), True), fill=TC("#202124"))
        y += Z(36)
    d.text((Z(20), y + Z(2)), "%d screens · %d stories" % (ns, len(us)), font=font(Z(19)), fill=TC("#5F6368"))
    mx = Z(16)
    for v in minis:
        paste_rgba(c, v["img"], (mx, y + Z(30)))
        mx += v["size"][0] + Z(2)
    y += MH
    x = Z(20)
    for k, n in counts(us).items():
        if n:
            lab = "%d %s" % (n, k)
            wd = tw(d, lab, font(Z(18), True)) + Z(20)
            d.rounded_rectangle((x, y + Z(38), x + wd, y + Z(70)), Z(6), fill=STATUS[k]["color"])
            d.text((x + Z(10), y + Z(43)), lab, font=font(Z(18), True), fill=on_color())
            x += wd + Z(8)
    d.rounded_rectangle((0, 0, CWD - 1, H - 1), Z(14), outline=TC("#2D7A5C"), width=Z(4))
    return c


OVERVIEW_BOX = (84, 150)      # a mini screen in an overview card at zoom 1 (points)


def layer_columns(keys, edges, maxrows):
    nxt = collections.defaultdict(list)
    indeg = collections.Counter()
    for e in edges:
        if e[0] != e[1] and e[0] in keys and e[1] in keys:
            nxt[e[0]].append(e[1])
            indeg[e[1]] += 1
    roots = [k for k in keys if indeg[k] == 0] or keys[:1]
    depth, queue = {}, []
    for r in roots:
        depth[r] = 0
        queue.append(r)
    while queue:
        c = queue.pop(0)
        for n in nxt[c]:
            if n not in depth:
                depth[n] = depth[c] + 1
                queue.append(n)
    cols = collections.defaultdict(list)
    for k in keys:
        cols[depth.get(k, 0)].append(k)
    final = []
    for dpt in sorted(cols):
        ks = cols[dpt]
        for i in range(0, len(ks), maxrows):
            final.append(ks[i:i + maxrows])
    return final


def arrow_head(d, p0, p1, color, size=16):
    import math
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    pts = [p1, (p1[0] - size * math.cos(ang - 0.4), p1[1] - size * math.sin(ang - 0.4)),
           (p1[0] - size * math.cos(ang + 0.4), p1[1] - size * math.sin(ang + 0.4))]
    d.polygon(pts, fill=color)


def render_cards(cards, edges, title, sub, out, maxrows=3, z=1.0):
    """Simple left-to-right layout of pre-rendered card images joined by labelled arrows."""
    Z = lambda v: max(1, int(round(v * z)))
    keys = list(cards)
    cols = layer_columns(keys, edges, maxrows)
    GAPX, GAPY, M, TOP = Z(190), Z(70), Z(60), Z(170)
    colw = [max(cards[k].width for k in c) for c in cols]
    colh = [sum(cards[k].height for k in c) + GAPY * (len(c) - 1) for c in cols]
    H = max(colh) + TOP + M
    W = sum(colw) + GAPX * (len(cols) - 1) + 2 * M
    img = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(img)
    d.text((M, Z(36)), title, font=font(Z(44), True, True), fill=TC("#202124"))
    if sub:
        d.text((M, Z(100)), sub, font=font(Z(22)), fill=TC("#5F6368"))
    pos, x = {}, M
    for ci, c in enumerate(cols):
        y = TOP + (max(colh) - colh[ci]) // 2
        for k in c:
            pos[k] = (x + (colw[ci] - cards[k].width) // 2, y, ci)
            y += cards[k].height + GAPY
        x += colw[ci] + GAPX
    labels = []
    used_from = collections.Counter()
    ecol = hexrgb(TC("#2D7A5C"))
    for a, b, lab, dashed in edges:
        if a not in pos or b not in pos or a == b:
            continue
        (ax, ay, ca), (bx, by, cb) = pos[a], pos[b]
        ca_, cb_ = cards[a], cards[b]
        if cb > ca:
            pts = [(ax + ca_.width, ay + ca_.height // 2), (bx, by + cb_.height // 2)]
        elif cb == ca:
            if by > ay:
                pts = [(ax + ca_.width // 2, ay + ca_.height), (bx + cb_.width // 2, by)]
            else:
                pts = [(ax + ca_.width // 2, ay), (bx + cb_.width // 2, by + cb_.height)]
        else:
            top = TOP - Z(40)
            pts = [(ax + ca_.width // 2, ay), (ax + ca_.width // 2, top), (bx + cb_.width // 2, top), (bx + cb_.width // 2, by)]
        col = hexrgb(TC("#9AA0A6")) if dashed else ecol
        for p, q in zip(pts, pts[1:]):
            if dashed:
                n = max(1, int(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5 // Z(18)))
                for i in range(0, n, 2):
                    d.line((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n,
                            p[0] + (q[0] - p[0]) * (i + 1) / n, p[1] + (q[1] - p[1]) * (i + 1) / n), fill=col, width=Z(4))
            else:
                d.line((p, q), fill=col, width=Z(4))
        arrow_head(d, pts[-2], pts[-1], col, Z(16))
        if lab:
            k = used_from[a]
            used_from[a] += 1
            f_ = 0.3 + 0.17 * (k % 4) if len(pts) == 2 else 0.5
            labels.append((pts[0][0] + (pts[-1][0] - pts[0][0]) * f_, pts[0][1] + (pts[-1][1] - pts[0][1]) * f_, lab))
    for k, (x0, y0, _) in pos.items():
        paste_rgba(img, cards[k], (x0, y0))
    f = font(Z(18), True)
    for cx, cy, lab in labels:
        lines = wrap_px(d, lab, f, Z(170))
        w = max(tw(d, l, f) for l in lines) + Z(14)
        h = Z(24) * len(lines) + Z(8)
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Z(6), fill=TH["bg"], outline=TC("#B7DCCB"), width=Z(2))
        for i, l in enumerate(lines):
            d.text((cx - w / 2 + Z(7), cy - h / 2 + Z(4) + i * Z(24)), l, font=f, fill=TC("#1F5A43"))
    img.save(out, optimize=True)


# --------------------------------------------------------------------------- tree layout for flows
# A screen with 2+ outgoing edges is drawn as a TREE: one trunk leaves the parent, a bus splits it with orthogonal elbows,
# and the children sit on one aligned row (flow runs top -> bottom) or in one aligned column (flow runs left -> right),
# centred on the parent. Linear steps (one outgoing edge) stay straight arrows.
def flow_tree(keys, edges):
    """Spanning forest of a flow graph by breadth-first search. Returns (children, depth, roots, extra):
    children[key] = ordered tree children; extra = edges that are not tree edges (merges, back-links, skips)."""
    out = collections.OrderedDict((k, []) for k in keys)
    indeg = collections.Counter()
    for a, b, lab, dashed in edges:
        if a in out and b in out and a != b:
            out[a].append(b)
            indeg[b] += 1
    roots = [k for k in keys if not indeg[k]] or keys[:1]
    depth, parent, queue = {r: 0 for r in roots}, {}, collections.deque(roots)
    while True:
        while queue:
            a = queue.popleft()
            for b in out[a]:
                if b not in depth:
                    depth[b], parent[b] = depth[a] + 1, a
                    queue.append(b)
        rest = [k for k in keys if k not in depth]          # only reachable through a cycle: start a new root there
        if not rest:
            break
        roots.append(rest[0])
        depth[rest[0]] = 0
        queue.append(rest[0])
    children = collections.OrderedDict((k, []) for k in keys)
    for k in keys:
        if k in parent:
            children[parent[k]].append(k)
    extra, seen = [], set()
    for a, b, lab, dashed in edges:
        if a in out and b in out and a != b and (a, b) not in seen:
            seen.add((a, b))
            if parent.get(b) != a:
                extra.append((a, b, lab, dashed))
    return children, depth, roots, extra


def tree_layout(keys, edges, sizes, orient, label_ext, vgap=70, base_gap=90):
    """Positions for every card. sizes[key] = (w, h) in px; orient 'TB' or 'LR'.
    Returns dict(pos={key: (x, y)}, layers={depth: (u0, u_end)}, bus={depth: u}, ...) in canvas coordinates (no margin)."""
    children, depth, roots, extra = flow_tree(keys, edges)
    tb = orient == "TB"
    du = {k: (sizes[k][1] if tb else sizes[k][0]) for k in keys}      # extent along the flow
    dv = {k: (sizes[k][0] if tb else sizes[k][1]) for k in keys}      # extent across the flow
    nl = max(depth.values()) + 1
    lay = [max(du[k] for k in keys if depth[k] == d) for d in range(nl)]
    elab = {}                                                         # label extent along the flow, per source layer
    for a, b, lab, dashed in edges:
        if a in depth and b in depth and lab:
            elab[depth[a]] = max(elab.get(depth[a], 0), label_ext(lab)[0 if not tb else 1])
    need = dict(dv)                                                   # room across the flow: a card, or the label above it
    for a, b, lab, dashed in edges:
        if a in depth and b in depth and lab:
            need[b] = max(need[b], label_ext(lab)[1 if not tb else 0] + 14)
    nx = collections.Counter(depth[a] for a, b, l, d in extra)
    na = collections.Counter(depth[b] for a, b, l, d in extra)
    gap = [max(base_gap, 36 + elab.get(d, 0) + 44) + 24 * (nx[d] + na[d + 1]) for d in range(nl)]
    U = [0.0]
    for d in range(nl):
        U.append(U[d] + lay[d] + gap[d])
    ext = {}

    def measure(k):
        cs = children[k]
        span = sum(measure(c) for c in cs) + vgap * max(0, len(cs) - 1)
        ext[k] = max(need[k], span)
        return ext[k]
    for r in roots:
        measure(r)
    cv = {}                                                           # centre across the flow

    def place(k, v0):
        cs = children[k]
        span = sum(ext[c] for c in cs) + vgap * max(0, len(cs) - 1)
        v = v0 + (ext[k] - span) / 2
        for c in cs:
            place(c, v)
            v += ext[c] + vgap
        if cs:
            cv[k] = (cv[cs[0]] + cv[cs[-1]]) / 2                         # centred over its children (single child: straight line)
        else:
            cv[k] = v0 + ext[k] / 2
    v0 = 0.0
    for r in roots:
        place(r, v0)
        v0 += ext[r] + vgap * 2
    vmin = min(cv[k] - dv[k] / 2 for k in keys)
    vmax = max(cv[k] + dv[k] / 2 for k in keys)
    pos, cen = {}, {}
    for k in keys:
        u, v = U[depth[k]], cv[k] - vmin
        cen[k] = v
        pos[k] = (v - dv[k] / 2, u) if tb else (u, v - dv[k] / 2)
    total_u = U[nl - 1] + lay[nl - 1]
    return dict(pos=pos, cen=cen, depth=depth, children=children, extra=extra, roots=roots, U=U, lay=lay, gap=gap,
                size=((vmax - vmin, total_u) if tb else (total_u, vmax - vmin)), tb=tb, du=du, dv=dv)


def render_tree(cards, edges, title, sub, out, sc=2):
    """Draw a flow as a tree (see above). cards = {key: PIL card}; edges = [(a, b, label, dashed)]."""
    keys = list(cards)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    fL = font(int(18 * sc), True)
    wl = int(170 * sc)

    def label_lines(lab):
        return wrap_px(tmp, lab, fL, wl)

    def label_ext(lab):
        ls = label_lines(lab)
        return (max(tw(tmp, l, fL) for l in ls) + 14 * sc, int(24 * sc) * len(ls) + 8 * sc)
    sizes = {k: cards[k].size for k in keys}
    best = None
    for orient in ("TB", "LR"):
        L = tree_layout(keys, edges, sizes, orient, label_ext, vgap=int(60 * sc), base_gap=int(46 * sc))
        w, h = L["size"]
        score = abs(math.log(max(w, 1) / max(h, 1)) - math.log(1.7))
        if best is None or score < best[0]:
            best = (score, L)
    L = best[1]
    tb = L["tb"]
    M, TOP = int(60 * sc), int(140 * sc)
    chan = 28 * sc * (len(L["extra"]) + 1)
    W = int(L["size"][0] + 2 * M + (chan if tb else 0))
    H = int(L["size"][1] + TOP + M + (0 if tb else chan))
    img = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(img)
    d.text((M, int(30 * sc)), title, font=font(int(44 * sc), True, True), fill=TC("#202124"))
    if sub:
        d.text((M, int(30 * sc) + int(76 * sc)), sub, font=font(int(22 * sc)), fill=TC("#5F6368"))
    ox, oy = M, TOP
    P = {k: (L["pos"][k][0] + ox, L["pos"][k][1] + oy) for k in keys}
    for k in keys:
        paste_rgba(img, cards[k], (P[k][0], P[k][1]))

    def xy(u, v):                 # abstract (along, across) -> canvas
        return (v + ox, u + oy) if tb else (u + ox, v + oy)
    ecol, gcol, wd = hexrgb(TC("#2D7A5C")), hexrgb(TC("#9AA0A6")), max(2, int(4 * sc))
    labels = []

    def line(pts, dashed, arrow=True):
        col = gcol if dashed else ecol
        cv_ = [xy(*p) for p in pts]
        for p, q in zip(cv_, cv_[1:]):
            if dashed:
                n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) // (18 * sc)))
                for i in range(0, n, 2):
                    d.line((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n,
                            p[0] + (q[0] - p[0]) * (i + 1) / n, p[1] + (q[1] - p[1]) * (i + 1) / n), fill=col, width=wd)
            else:
                d.line((p, q), fill=col, width=wd)
        if arrow:
            arrow_head(d, cv_[-2], cv_[-1], col, size=int(16 * sc))

    def dim(k):
        return L["du"][k], L["dv"][k]
    U, lay, gap, cen, depth = L["U"], L["lay"], L["gap"], L["cen"], L["depth"]
    labmap = {(a, b): (lab, dashed) for a, b, lab, dashed in edges}

    nxe = collections.Counter(depth[e[0]] for e in L["extra"])

    def bus_u(dp):                # junction line of the gap below layer dp (extra edges run between the cards and the bus)
        return U[dp] + lay[dp] + (18 + 12 * nxe[dp]) * sc
    for a in keys:
        cs = L["children"][a]
        dp = depth[a]
        u_end = U[dp] + dim(a)[0]
        va = cen[a]
        outs = len(cs) + sum(1 for e in L["extra"] if e[0] == a)
        if not cs:
            continue
        if outs == 1:                                            # linear step: one straight arrow
            c = cs[0]
            lab, dashed = labmap[(a, c)][0], labmap[(a, c)][1]
            line([(u_end, va), (U[depth[c]], cen[c])], dashed)
            if lab:
                labels.append((xy((u_end + U[depth[c]]) / 2, (va + cen[c]) / 2), lab))
        else:                                                    # branch: trunk, bus, aligned drops
            ub = bus_u(dp)
            line([(u_end, va), (ub, va)], False, arrow=False)
            vs = [cen[c] for c in cs] + [va]
            line([(ub, min(vs)), (ub, max(vs))], False, arrow=False)
            for c in cs:
                lab, dashed = labmap[(a, c)]
                line([(ub, cen[c]), (U[depth[c]], cen[c])], dashed)
                if lab:
                    ext_u = label_ext(lab)[1 if tb else 0]
                    labels.append((xy(ub + 12 * sc + ext_u / 2, cen[c]), lab))
    # extra edges (merges, back-links, skips): orthogonal route through a side channel
    vmax = L["size"][0 if tb else 1]
    for i, (a, b, lab, dashed) in enumerate(L["extra"]):
        dp, dt = depth[a], depth[b]
        k = sum(1 for e in L["extra"][:i] if depth[e[0]] == dp)
        ub = bus_u(dp)
        ux = U[dp] + lay[dp] + 12 * sc * (k + 1)
        vch = vmax + 22 * sc * (i + 1)
        ja = sum(1 for e in L["extra"][:i] if depth[e[1]] == dt)
        uy = U[dt] - 12 * sc * (ja + 1) if dt > 0 else U[0] - 14 * sc
        if dt == dp + 1:                      # a merge into the next layer: stay inside the gap between the two layers
            pts = [(U[dp] + dim(a)[0], cen[a]), (ux, cen[a]), (ux, cen[b]), (U[dt], cen[b])]
            lab_at = xy(ux, (cen[a] + cen[b]) / 2)
        else:
            pts = [(U[dp] + dim(a)[0], cen[a]), (ux, cen[a]), (ux, vch), (uy, vch), (uy, cen[b]), (U[dt], cen[b])]
            lab_at = xy((ux + uy) / 2, vch)
        line(pts, dashed or lab.startswith("("))
        if lab:
            labels.append((lab_at, lab))
    for (cx, cy), lab in labels:
        ls = label_lines(lab)
        w, h = label_ext(lab)
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), int(6 * sc), fill=TH["bg"], outline=TC("#B7DCCB"), width=max(1, int(sc)))
        for i, l in enumerate(ls):
            d.text((cx - w / 2 + 7 * sc, cy - h / 2 + 4 * sc + i * int(24 * sc)), l, font=fL, fill=TC("#1F5A43"))
    img.save(out, optimize=True)
    return L, P


def pil_flow(m, fid, out, tree=True):
    nodes, edges = flow_graph(m, fid)
    sc = max(2.0, m.get("_zoom_flow", 2.0)) if tree else 1
    cards = collections.OrderedDict()
    for n in nodes:
        cards[n["key"]] = card_screen(m, n["screen"], sc) if n["kind"] == "screen" else card_portal(n["label"], n["kind"][7:], sc)
    f = m["F"][fid]
    if tree:
        return render_tree(cards, edges, f["title"], f["description"], out, sc)
    render_cards(cards, edges, f["title"], f["description"], out)


def pil_overview(m, out, z=1.0):
    zt = min(z, 4.0)      # text 4x is already ~100 px tall; the screens stay at native resolution
    cards = collections.OrderedDict((f["id"], card_flow(m, f, z, zt)) for f in m["flows"])
    edges = [(a, b, lab, lab.startswith("(")) for (a, b), lab in cross_flow_edges(m).items()]
    render_cards(cards, edges, m["app"]["name"] + " - flows overview", header_line(m), out, maxrows=4, z=zt)


def pil_full(m, out, flow_dir=None):
    """Fallback for the all-in-one map: every flow image stacked vertically."""
    tmp = []
    for f in m["flows"]:
        p = os.path.join(flow_dir or os.path.join(os.path.dirname(out), "flows"), "%s.png" % f["id"])
        if os.path.isfile(p):
            tmp.append(Image.open(p).convert("RGB"))
    if not tmp:
        return False
    W = max(i.width for i in tmp)
    if W * (sum(i.height for i in tmp) + 40 * len(tmp)) > 300_000_000:    # absurdly large: the flows/ images already hold it all
        print("  note  flow-map.png skipped (would exceed 300 megapixels at native resolution); see flows/*.png")
        return False
    img = Image.new("RGB", (W, sum(i.height for i in tmp) + 40 * len(tmp)), TH["bg"])
    y = 0
    for i in tmp:
        img.paste(i, (0, y))
        y += i.height + 40
    img.save(out, optimize=True)
    return True


# --------------------------------------------------------------------------- architecture (topic swimlanes)
ARCH_SCALE = 0.36


def topic_label_html(m, r, size=30, idx=None):
    tp = r["topic"]
    cs = " · ".join("%d %s" % (n, k) for k, n in r["counts"].items() if n)
    face = ' FACE="%s"' % dq(TH["heading_font"]) if TH["heading_font"] else ""
    return ('<FONT POINT-SIZE="%d" COLOR="%s"%s><B>%s</B></FONT><BR/><FONT POINT-SIZE="%d" COLOR="%s">%d screens · %d stories%s</FONT>' % (
        size, tp["color"], face, dq(tp["title"]), size // 2 + 2, TH["muted"], len(r["screens"]), len(r["stories"]),
        (" · " + cs) if cs else ""))


def dot_arch_node(s, th):
    if th and len(th) > 3 and th[3]:  # framed device: small title, device picture, status badge
        stv = STATUS[s["status"]]
        w, h = max(1, round(th[1] * ARCH_SCALE)), max(1, round(th[2] * ARCH_SCALE))  # same ratio as the thumbnail
        cw = max(w, 120)
        name = '<TR><TD WIDTH="%d"><FONT POINT-SIZE="14"><B>%s</B></FONT></TD></TR>' % (cw, dwrap(s["title"], max(12, cw // 7)))
        pic = ('<TR><TD><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>'
               '<TD FIXEDSIZE="TRUE" WIDTH="%d" HEIGHT="%d"><IMG SCALE="TRUE" SRC="%s"/></TD></TR></TABLE></TD></TR>' % (w, h, dq(th[0])))
        lab = ' <FONT POINT-SIZE="12" COLOR="#3C4043"><B>%s</B></FONT>' % dq(stv["label"]) if TH["device"]["badge"] == "label" else ""
        badge = '<TR><TD><FONT POINT-SIZE="13" COLOR="%s">&#9679;</FONT>%s</TD></TR>' % (stv["color"], lab)
        tbl = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2">%s%s%s</TABLE>>' % (name, pic, badge)
        return '  "%s" [label=%s tooltip="%s"];' % (s["id"], tbl, dq(s["title"]))
    stv = STATUS[s["status"]]
    if th:
        w, h = max(1, round(th[1] * ARCH_SCALE)), max(1, round(th[2] * ARCH_SCALE))  # same ratio as the thumbnail
        body = '<TD FIXEDSIZE="TRUE" WIDTH="%d" HEIGHT="%d" CELLPADDING="4"><IMG SCALE="TRUE" SRC="%s"/></TD>' % (w + 8, h + 8, dq(th[0]))
    else:
        w, h = 110, 70
        body = '<TD WIDTH="%d" HEIGHT="%d" BGCOLOR="#F1F3F4"><FONT POINT-SIZE="11" COLOR="#5F6368">not captured</FONT></TD>' % (w, h)
    cw = max(w, 120)
    name = '<TR><TD WIDTH="%d" BGCOLOR="white"><FONT POINT-SIZE="14"><B>%s</B></FONT></TD></TR>' % (cw, dwrap(s["title"], max(12, cw // 7)))
    tbl = '<<TABLE BORDER="3" COLOR="%s" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="%s">%s<TR>%s</TR></TABLE>>' % (
        stv["color"], "rounded" if th else "dashed", name, body)
    return '  "%s" [label=%s tooltip="%s"];' % (s["id"], tbl, dq(s["title"]))


def dot_architecture(m, thumbs):
    L = dot_header(m["app"]["name"] + " - architecture by topic", header_line(m), "LR")
    L[1] = L[1].replace("nodesep=0.5 ranksep=1.0", "nodesep=0.35 ranksep=1.4")
    rows = [r for r in topic_summary(m) if r["screens"]]
    for r in rows:
        tp = r["topic"]
        L.append('  subgraph "cluster_%s" { label=<%s> labeljust=l style="rounded,filled" fillcolor="%s" color="%s" penwidth=3.5 margin=22;'
                 % (tp["id"], topic_label_html(m, r), tint(tp["color"], 0.93), tp["color"]))
        L += [dot_arch_node(s, thumbs.get(s["id"])) for s in r["screens"]]
        L.append("  }")
    cross_pairs = set()
    for e in m["edges"]:
        if e["src"] in m["S"] and e["dst"] in m["S"]:
            a, b = m["S"][e["src"]], m["S"][e["dst"]]
            if a["topic_eff"] != b["topic_eff"]:
                col = m["T"][a["topic_eff"]]["color"] if a["topic_eff"] in m["T"] else TH["primary"]
                cross_pairs.add((a["topic_eff"], b["topic_eff"]))
                L.append('  "%s" -> "%s" [color="%s" fontcolor="%s" penwidth=4.2 arrowsize=1.4 fontsize=15 label=<<B>%s</B>>%s];' % (
                    e["src"], e["dst"], col, col, dwrap(e["label"], 20),
                    ' style=dashed' if e["dashed"] else ""))
            else:
                L.append('  "%s" -> "%s" [color="%s" penwidth=1.6 arrowsize=0.8%s];' % (
                    e["src"], e["dst"], TH["gray"], ' style=dashed' if e["dashed"] else ""))
    for r1, r2 in zip(rows, rows[1:]):  # keep the swimlane order even where nothing links the topics
        if (r1["topic"]["id"], r2["topic"]["id"]) not in cross_pairs:
            L.append('  "%s" -> "%s" [style=invis weight=0.3];' % (r1["screens"][0]["id"], r2["screens"][0]["id"]))
    return "\n".join(L + ["}"]) + "\n"


ARCH_BOX = (LANDSCAPE_W * ARCH_SCALE * 1.6, PORTRAIT_H * ARCH_SCALE * 1.6)   # device box at zoom 1 (points)


def card_compact(m, s, z=1.0):
    """Small architecture card: title, device frame, status badge (no coloured border). z = zoom (native resolution)."""
    Z = lambda v: max(1, int(round(v * z)))
    dv = screen_device(m, s, ARCH_BOX, z)
    w, h = dv["size"]
    badge = badge_img(s["status"], 0.8 * z, TH["device"]["badge"] == "label")
    CW = max(w, Z(150), badge.width) + Z(16)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    fT = font(Z(17), True)
    tl = wrap_px(tmp, s["title"], fT, CW - Z(16))
    CW = int(max(CW, max([tw(tmp, t, fT) for t in tl] or [0]) + Z(16)))  # a long word must never be cut off
    H = Z(8) + Z(22) * len(tl) + Z(6) + h + Z(4) + badge.height + Z(8)
    card = Image.new("RGBA", (CW, H), (0, 0, 0, 0))     # transparent: title, device and badge sit on the lane colour
    d = ImageDraw.Draw(card)
    y = Z(8)
    for ln in tl:
        d.text((CW // 2, y), ln, font=fT, fill=TC("#202124"), anchor="ma")
        y += Z(22)
    y += Z(6)
    paste_rgba(card, dv["img"], ((CW - w) // 2, y))
    paste_rgba(card, badge, ((CW - badge.width) // 2, y + h + Z(4)))
    return card


def _arch_layout(rows, cards, rn, z, dtmp, m):
    """Place the topic bands left to right; inside a band the screens fill a grid of `rn` rows. Returns the layout."""
    Z = lambda v: max(1, int(round(v * z)))
    GAP, BANDGAP, PAD, HEAD, TOP = Z(26), Z(170), Z(28), Z(110), Z(150)

    def _band_sub(r):
        cs = " · ".join("%d %s" % (n, k) for k, n in r["counts"].items() if n)
        return "%d screens · %d stories%s" % (len(r["screens"]), len(r["stories"]), (" · " + cs) if cs else "")
    pos, bands, x, maxh = {}, [], Z(60), 0
    for r in rows:
        ss = r["screens"]
        cols = [ss[i:i + rn] for i in range(0, len(ss), rn)]
        cw = [max(cards[s["id"]].width for s in c) for c in cols]
        bw = sum(cw) + GAP * (len(cols) - 1) + 2 * PAD
        sub = _band_sub(r)
        bw = int(max(bw, tw(dtmp, r["topic"]["title"], font(Z(30), True, True)) + 2 * PAD,   # a band is never narrower than its heading,
                     tw(dtmp, sub, font(Z(16))) + 2 * PAD))                                  # so no title is cut off at the edge
        bh = max(sum(cards[s["id"]].height for s in c) + GAP * (len(c) - 1) for c in cols) + HEAD + PAD
        cx = x + PAD
        for c, w in zip(cols, cw):
            y = TOP + HEAD
            for s in c:
                pos[s["id"]] = (cx + (w - cards[s["id"]].width) // 2, y)
                y += cards[s["id"]].height + GAP
            cx += w + GAP
        bands.append((r, x, bw, bh, sub))
        x += bw + BANDGAP
        maxh = max(maxh, bh)
    W, H = x - BANDGAP + Z(60), TOP + maxh + Z(60)
    W = int(max(W, Z(120) + tw(dtmp, m["app"]["name"] + " - architecture by topic", font(Z(44), True, True)),
                Z(120) + tw(dtmp, header_line(m), font(Z(22)))))   # the heading is never cut off either
    return dict(pos=pos, bands=bands, W=W, H=H, TOP=TOP, PAD=PAD)


def pil_architecture(m, out, z=1.0, crops=True, save=True):
    """Topic swimlanes left to right, compact screen cards inside, cross-topic arrows on top. Drawn at zoom z, so every
    screenshot is at >= its native pixels (z from native_zoom). The number of grid rows per lane is chosen for a
    page that is neither very wide nor very tall. Also writes one full-resolution crop per topic next to `out`."""
    rows = [r for r in topic_summary(m) if r["screens"]]
    if not rows:
        return
    Z = lambda v: max(1, int(round(v * z)))
    cards = {s["id"]: card_compact(m, s, z) for r in rows for s in r["screens"]}
    dtmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    best = None
    for rn in range(2, 9):                         # how many rows of screens in a lane: aim for a page about 2.1 : 1
        L = _arch_layout(rows, cards, rn, z, dtmp, m)
        sc_ = abs(math.log(L["W"] / L["H"]) - math.log(2.1))
        if best is None or sc_ < best[0]:
            best = (sc_, L)
    L = best[1]
    pos, bands, W, H, TOP, PAD = L["pos"], L["bands"], L["W"], L["H"], L["TOP"], L["PAD"]
    img = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(img)
    d.text((Z(60), Z(36)), m["app"]["name"] + " - architecture by topic", font=font(Z(44), True, True), fill=TC("#202124"))
    d.text((Z(60), Z(96)), header_line(m), font=font(Z(22)), fill=TC("#5F6368"))
    for r, bx, bw, bh, sub in bands:
        tp = r["topic"]
        d.rounded_rectangle((bx, TOP, bx + bw, TOP + bh), Z(28), fill=tint(tp["color"], 0.93), outline=tp["color"], width=Z(5))
        d.text((bx + PAD, TOP + Z(16)), tp["title"], font=font(Z(30), True, True), fill=tp["color"])
        d.text((bx + PAD, TOP + Z(62)), sub, font=font(Z(16)), fill=TC("#5F6368"))

    def anchor(a, b):
        (ax, ay), (bx_, by_) = pos[a], pos[b]
        ca, cb = cards[a], cards[b]
        if bx_ >= ax + ca.width:
            return (ax + ca.width, ay + ca.height // 2), (bx_, by_ + cb.height // 2)
        if bx_ + cb.width <= ax:
            return (ax, ay + ca.height // 2), (bx_ + cb.width, by_ + cb.height // 2)
        if by_ >= ay:
            return (ax + ca.width // 2, ay + ca.height), (bx_ + cb.width // 2, by_)
        return (ax + ca.width // 2, ay), (bx_ + cb.width // 2, by_ + cb.height)
    rects = {sid: (x, y, x + cards[sid].width, y + cards[sid].height) for sid, (x, y) in pos.items()}
    lines, cross = [], []
    for e in m["edges"]:
        if e["src"] in pos and e["dst"] in pos and e["src"] != e["dst"]:
            a, b = m["S"][e["src"]], m["S"][e["dst"]]
            p, q = anchor(e["src"], e["dst"])
            if a["topic_eff"] != b["topic_eff"]:
                cross.append((p, q, e, m["T"][a["topic_eff"]]["color"] if a["topic_eff"] in m["T"] else TH["primary"]))
            else:
                lines.append((p, q, e))
    for p, q, e in lines:  # inside a topic: thin grey, drawn behind the cards
        d.line((p, q), fill=TC("#9AA0A6"), width=Z(3))
    for p, q, e, col in cross:  # between topics: thick, topic coloured, also behind the cards (visible in the gaps)
        d.line((p, q), fill=hexrgb(col), width=Z(6))
    for sid, (cx, cy) in pos.items():
        paste_rgba(img, cards[sid], (cx, cy))
    for p, q, e in lines:
        arrow_head(d, p, q, TC("#9AA0A6"), Z(12))
    f = font(Z(16), True)
    placed = []

    def free(pt, w, h):
        box = (pt[0] - w / 2, pt[1] - h / 2, pt[0] + w / 2, pt[1] + h / 2)
        for r in list(rects.values()) + placed:
            if not (box[2] < r[0] or box[0] > r[2] or box[3] < r[1] or box[1] > r[3]):
                return False
        return True
    for p, q, e, col in cross:
        c = hexrgb(col)
        arrow_head(d, p, q, c, Z(22))
        if e["label"]:
            lines_ = wrap_px(d, e["label"], f, Z(180))[:2]
            w = max(tw(d, l, f) for l in lines_) + Z(14)
            h = Z(22) * len(lines_) + Z(8)
            spot = None
            for tpos in (0.5, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74, 0.18, 0.82, 0.5):
                pt = (p[0] + (q[0] - p[0]) * tpos, p[1] + (q[1] - p[1]) * tpos)
                if free(pt, w, h):
                    spot = pt
                    break
            if spot is None:
                spot = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            mx, my = spot
            placed.append((mx - w / 2, my - h / 2, mx + w / 2, my + h / 2))
            d.rounded_rectangle((mx - w / 2, my - h / 2, mx + w / 2, my + h / 2), Z(6), fill=TH["bg"], outline=col, width=Z(2))
            for i, l in enumerate(lines_):
                d.text((mx - w / 2 + Z(7), my - h / 2 + Z(4) + i * Z(22)), l, font=f, fill=col)
    if save:
        img.save(out, optimize=True)
    if crops:
        tdir = os.path.splitext(out)[0]            # full-resolution crops per topic lane
        os.makedirs(tdir, exist_ok=True)
        for r, bx, bw, bh, sub in bands:
            pad = Z(20)
            img.crop((max(0, bx - pad), max(0, TOP - pad), min(W, bx + bw + pad), min(H, TOP + bh + pad))).save(
                os.path.join(tdir, r["topic"]["id"] + ".png"), optimize=True)
    return dict(cards={sid: pos[sid] + cards[sid].size for sid in pos},
                bands=[(r["topic"]["id"], bx, TOP, bw, bh) for r, bx, bw, bh, sub in bands])


def gen_diagrams(m, gen, use_graphviz=True, formats=None):
    """Render requested diagrams, preserving native screenshot resolution with Pillow."""
    formats = set(formats) if formats is not None else {"arch", "crops", "flows", "flow-map", "overview"}
    notes = []
    os.makedirs(gen, exist_ok=True)
    gv = use_graphviz and shutil.which("dot") and not HAVE_PIL
    dotdir = os.path.join(gen, "dot")
    thumbs = {}
    if gv or "dot" in formats:
        set_diagram("thumbs")
        thumbs = make_thumbs(m, gen)
    jobs = [("overview", "overview", lambda: dot_overview(m, thumbs), "overview.png", 130),
            ("flow-map", "flow-map", lambda: dot_full(m, thumbs), "flow-map.png", 96),
            ("arch", "architecture", lambda: dot_architecture(m, thumbs), "architecture.png", 110)]
    jobs += [("flows", f["id"], lambda fid=f["id"]: dot_flow(m, fid, thumbs),
              "flows/" + f["id"] + ".png", 144) for f in m["flows"]]
    for kind, name, source, output, dpi in jobs:
        if "dot" in formats or (gv and kind in formats):
            path = os.path.join(dotdir, name + ".dot")
            write(path, dot_text(source()))
            if gv and kind in formats:
                os.makedirs(os.path.dirname(os.path.join(gen, output)), exist_ok=True)
                if not run_dot(path, os.path.join(gen, output), dpi):
                    notes.append("graphviz failed on " + name)
    if HAVE_PIL:
        del RES_LOG[:]
        if "flows" in formats or "flow-map" in formats:
            m["_zoom_flow"] = native_zoom(m, (LANDSCAPE_W, PORTRAIT_H), 2.0)
        if "overview" in formats:
            set_diagram("overview")
            pil_overview(m, os.path.join(gen, "overview.png"), native_zoom(m, OVERVIEW_BOX))
            _DEV_CACHE.clear()
        if "flows" in formats:
            os.makedirs(os.path.join(gen, "flows"), exist_ok=True)
            for f in m["flows"]:
                set_diagram("flows/" + f["id"])
                pil_flow(m, f["id"], os.path.join(gen, "flows", f["id"] + ".png"))
                _DEV_CACHE.clear()
        if "flow-map" in formats:
            set_diagram("flow-map")
            if "flows" in formats:
                rendered = pil_full(m, os.path.join(gen, "flow-map.png"))
            else:
                with tempfile.TemporaryDirectory(prefix="storymap-flows-") as work:
                    for f in m["flows"]:
                        set_diagram("flows/" + f["id"])
                        pil_flow(m, f["id"], os.path.join(work, f["id"] + ".png"))
                        _DEV_CACHE.clear()
                    set_diagram("flow-map")
                    rendered = pil_full(m, os.path.join(gen, "flow-map.png"), flow_dir=work)
            if not rendered:
                notes.append("flow-map.png skipped (no flows or exceeds 300 megapixels)")
            _DEV_CACHE.clear()
        if "arch" in formats or "crops" in formats:
            set_diagram("architecture")
            pil_architecture(m, os.path.join(gen, "architecture.png"), native_zoom(m, ARCH_BOX),
                             crops="crops" in formats, save="arch" in formats)
            _DEV_CACHE.clear()
    elif gv:
        notes.append("Graphviz without Pillow: screenshots are not at native resolution (install Pillow)")
    elif formats - {"dot"}:
        notes.append("skipped diagrams (need Pillow or Graphviz)")
    set_diagram("other")
    return notes


# --------------------------------------------------------------------------- single-file HTML viewer
def screen_aspect(m, s):
    """width / height of the screenshot (None when there is none)."""
    try:
        w, h = img_size(image_path(m, s)) if image_exists(m, s) else (0, 0)
    except Exception:
        return None
    return round(w / h, 4) if w and h else None


def embed_image(m, s, max_h=1040, max_w=480, quality=72):
    """Screenshot as a data: URI (downscaled when Pillow is available)."""
    p = image_path(m, s)
    if not p or not os.path.isfile(p):
        return ""
    im = load_img(m, s)
    if im is not None:
        if im.height > max_h or im.width > max_w:   # shrink to fit, same aspect ratio
            im = im.resize(contain(im.width, im.height, max_w, max_h), Image.LANCZOS)
        a = io.BytesIO()
        im.quantize(colors=128).save(a, "PNG", optimize=True)
        b = io.BytesIO()
        im.save(b, "JPEG", quality=quality, optimize=True)
        if len(b.getvalue()) < len(a.getvalue()):
            return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        return "data:image/png;base64," + base64.b64encode(a.getvalue()).decode()
    ext = os.path.splitext(p)[1].lower().lstrip(".")
    with open(p, "rb") as f:
        return "data:image/%s;base64,%s" % ("jpeg" if ext in ("jpg", "jpeg") else "png", base64.b64encode(f.read()).decode())


def embed_diagram(path, max_w=2400, quality=72):
    """A generated diagram as a data: URI; wide diagrams are downscaled (JPEG) so the viewer stays small."""
    if not os.path.isfile(path):
        return ""
    if HAVE_PIL:
        with Image.open(path) as source:
            im = source.convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, max(1, round(im.height * max_w / im.width))), Image.LANCZOS)
        b = io.BytesIO()
        im.save(b, "JPEG", quality=quality, optimize=True)
        a = io.BytesIO()
        im.save(a, "PNG", optimize=True)
        if len(b.getvalue()) < len(a.getvalue()):
            return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        return "data:image/png;base64," + base64.b64encode(a.getvalue()).decode()
    return embed_file(path)


def embed_file(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ - story map</title>
<style>
__FONTFACE__
:root{--ink:#202124;--mut:#5f6368;--line:#dadce0;--bg:#f7f8f9;--body:__BODYFONT__;--head:__HEADFONT__}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 var(--body);color:var(--ink);background:var(--bg)}h1,h2,h3{font-family:var(--head)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 20px;position:sticky;top:0;z-index:5}
h1{margin:0;font-size:20px}.sub{color:var(--mut);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.chip{border:2px solid;border-radius:999px;padding:2px 10px;font-size:13px;cursor:pointer;user-select:none;background:#fff}
.chs{display:contents}.chip.off{opacity:.35}.tabs button{border:0;background:none;font:inherit;color:inherit;padding:6px 12px;cursor:pointer;border-bottom:3px solid transparent}
.tabs button.on{border-color:#2d7a5c;font-weight:600}select,input{font:inherit;color:inherit;background:#fff;padding:4px 8px;border:1px solid var(--line);border-radius:6px}
main{padding:20px}section.flow{margin-bottom:34px}section.flow h2{margin:0 0 4px}.desc{color:var(--mut);margin:0 0 10px}
.row{display:flex;gap:18px;overflow-x:auto;padding-bottom:12px;align-items:flex-start}
.card{width:250px;flex:none;transition:opacity .2s}
.card.dim{opacity:.25}.card .ti{font-weight:700;padding:8px 12px 0;text-align:center}.card .id{color:#80868b;font-size:11px;padding:0 12px 4px;text-align:center}
.card.land{width:460px}.card.sq{width:340px}.card.tall{width:190px}
.dv{position:relative;display:block;margin:0 auto;aspect-ratio:var(--ar);width:100%;cursor:zoom-in;filter:drop-shadow(0 6px 9px rgba(10,12,20,.32))}
.dv>img{position:absolute;display:block;margin:0;border:0}.dv>img.f{inset:0;width:100%;height:100%}.dv>img.s{object-fit:contain;background:#000}
.dv.ph{filter:none;cursor:default}.card .dv{width:calc(100% - 24px);margin:8px 12px 2px}
.bd{display:flex;align-items:center;justify-content:center;gap:6px;font-size:12px;font-weight:600;color:var(--mut);padding:4px 10px 6px}.bd i{width:11px;height:11px;border-radius:50%;display:inline-block;flex:none}
.bd.nolabel span{display:none}
.ph:not(.dv){background:#f1f3f4;color:#5f6368;font-size:13px;padding:30px 12px;text-align:center;margin-top:6px}
.out{list-style:none;margin:0;padding:6px 10px;font-size:12.5px}.out a{color:#1f5a43;cursor:pointer;text-decoration:underline dotted}
.chips{padding:0 10px 10px;display:flex;flex-wrap:wrap;gap:4px}.mini{white-space:nowrap;font-size:11px;border-radius:4px;padding:1px 6px;color:#fff;cursor:pointer}
.flash{animation:fl 1.4s}@keyframes fl{0%,60%{box-shadow:0 0 0 6px #ffd54f}100%{box-shadow:none}}
table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid var(--line);padding:7px 9px;vertical-align:top;text-align:left}
th{background:#eef1f3;position:sticky;top:105px}tr.hide{display:none}td.st{white-space:nowrap}
.thumbs{white-space:nowrap}.thumbs .dv{display:inline-block;height:96px;width:auto;margin:2px 4px;filter:drop-shadow(0 2px 3px rgba(10,12,20,.3))}
.thumbs.small .dv{height:48px}.story-row{cursor:pointer}.story-row td:first-child{white-space:nowrap}.story-row:hover{background:#f1f3f4}.story-details td{padding:14px}.story-details p{margin:0 0 8px}.story-details .row{margin-top:12px}
.pill{color:#fff;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:600}
.grid{display:grid;gap:10px;align-items:start}.grid>div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px;min-height:44px}
.grid .h{background:#eef1f3;font-weight:700}.grid .mini{display:inline-block;margin:2px}
.gap{background:#fff;border:1px solid var(--line);border-left:6px solid;border-radius:8px;padding:10px 14px;margin-bottom:10px}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;align-items:center;justify-content:center;flex-direction:column;z-index:20}
#lbcontent{display:flex;gap:22px;align-items:center;max-width:92vw;max-height:84vh}#lb img#lbi{max-width:92vw;max-height:84vh;border-radius:8px}#lb #lbd .dv{height:76vh;width:auto;max-width:65vw;margin:0;cursor:default;filter:drop-shadow(0 10px 24px rgba(0,0,0,.6))}#lb .cap{color:#fefefe;margin-top:10px;text-align:center}#lb .cap a{color:inherit}
#lbdetails{width:310px;max-height:78vh;overflow:auto;background:var(--bg);color:var(--ink);padding:16px;border-radius:8px}#lbdetails h2{margin:0 0 8px}#lbdetails p{overflow-wrap:anywhere}#lbdetails a{color:inherit}#lbdetails ul{padding-left:20px}
#lb>button{position:absolute;top:50%;background:#fff3;color:#fefefe;border:0;font-size:34px;padding:8px 14px;cursor:pointer;border-radius:8px}#lb>button.close{top:10px;right:14px;font-size:24px}
/* Phones and touch screens (mobile friendly viewer): tap targets >= 44px, no sideways page scroll, detail view as a full-screen page */
@media(max-width:720px),(pointer:coarse){
button,.chip,.mini,.story-row,.dv,a{touch-action:manipulation}
.chip{display:inline-flex;align-items:center;min-height:44px;padding:0 14px}
.tabs button{min-height:44px;padding:0 14px}
select,input{min-height:44px;font-size:16px}
.mini{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;font-size:13px;padding:0 8px}
.chips{gap:6px}
.out li{display:flex;align-items:center;flex-wrap:wrap;gap:0 4px}.out a{display:inline-flex;align-items:center;min-height:44px;padding:0 2px}
.thumbs.small .dv{height:100px;margin:2px 6px 2px 0}
#lbdetails li{margin-bottom:4px}#lbdetails a{display:inline-flex;align-items:center;min-height:44px}
#lb .cap a{display:inline-flex;align-items:center;min-height:44px}
}
@media(max-width:720px){
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{font-size:16px}main{padding:14px 12px;overflow-wrap:anywhere}
header{position:static;padding:12px 14px}h1{font-size:18px}.sub{font-size:12.5px}
.bar{gap:6px}.chs{display:flex;flex:1 1 100%;gap:6px;overflow-x:auto;scrollbar-width:none}.chs::-webkit-scrollbar{display:none}.chip{flex:none}.bar select{flex:1 1 calc(50% - 6px);width:calc(50% - 3px);min-width:0}.bar input{flex:1 1 100%;min-width:0}
.tabs{display:flex;overflow-x:auto;white-space:nowrap;margin:6px -14px 0;padding:0 8px;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tabs button{flex:none}
.topic>h2.tb{font-size:18px;padding:8px 12px;border-left-width:6px}.topic>h2.tb small{display:block;margin:4px 0 0}.topic section.flow h2{font-size:17px}
.row{margin:0 -12px;padding:0 12px 12px;gap:12px;scroll-snap-type:x proximity;scroll-padding:0 12px;-webkit-overflow-scrolling:touch}.card{scroll-snap-align:start}
.card{width:min(250px,76vw)}.card.land{width:min(460px,88vw)}.card.sq{width:min(340px,82vw)}.card.tall{width:min(190px,66vw)}
.out{font-size:14px}.bd{font-size:13px}
.story-details .row{margin:12px 0 0;padding:0 0 12px}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
.arch>img,#main>img{max-width:100%;height:auto}
table,tbody,thead{display:block}thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.stb tr.story-row:not(.hide){display:grid;grid-template-columns:auto 1fr auto;gap:6px 10px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-top:10px}
.stb tr.story-row[aria-expanded=true]{border-radius:10px 10px 0 0;border-bottom:0}
.stb td{display:block;border:0;padding:0}.stb td:nth-child(1){grid-area:1/1}.stb td:nth-child(2){grid-area:1/2}.stb td:nth-child(5){grid-area:1/3}
.stb td:nth-child(3){grid-area:2/1/3/4}.stb td:nth-child(4){grid-area:3/1/4/4}.stb .thumbs{white-space:normal;display:flex;flex-wrap:wrap}.stb .thumbs .dv{margin:0 6px 6px 0}
.stb tr.story-details:not(.hidden){display:block;background:#fff;border:1px solid var(--line);border-top:0;border-radius:0 0 10px 10px}.stb tr.story-details td{display:block;padding:12px}
.atb tbody tr{display:grid;grid-template-columns:repeat(5,1fr);gap:8px 6px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:10px}
.atb td{display:block;border:0;padding:0}.atb td:nth-child(1),.atb td:nth-child(2){grid-column:1/-1}.atb td[data-l]::before{content:attr(data-l);display:block;font-size:11px;font-weight:400;color:var(--mut)}
.atb .thumbs{white-space:normal;display:flex;flex-wrap:wrap;margin-top:4px}.atb .thumbs .dv{margin:0 6px 6px 0}
.grid{grid-template-columns:112px repeat(var(--n),minmax(132px,1fr))!important;gap:6px;width:max-content;min-width:100%}.grid>div{overflow-wrap:break-word}.grid>.h:first-child,.grid>.h.pn{position:sticky;left:0;z-index:2}
#lb{justify-content:flex-start;align-items:stretch;overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;background:rgba(0,0,0,.92)}
#lbcontent{flex:none;flex-direction:column;align-items:center;gap:14px;width:100%;max-width:none;max-height:none;padding:64px 12px 16px;overflow-x:auto}
#lb #lbd .dv{height:auto;width:min(56vw,240px);max-width:none;margin:0 auto}
#lbdetails{width:100%;max-height:none;overflow:visible;flex:none}
#lb img#lbi{max-width:none;max-height:none;width:200vw;align-self:flex-start}
#lb .cap{margin:0;padding:0 16px 96px}
#lb>button{position:fixed;top:auto;bottom:16px;width:52px;height:52px;padding:0;font-size:30px;line-height:1;display:flex;align-items:center;justify-content:center;border-radius:50%;background:rgba(30,30,30,.9);border:1px solid #fff5;z-index:2}
#lb>button.close{top:10px;bottom:auto;right:10px;font-size:22px}
}
.hidden{display:none}
.tpc{font-size:11px;font-weight:700;padding:2px 10px;letter-spacing:.03em}
.tpill{border-radius:999px;padding:1px 9px;font-size:12px;font-weight:600;white-space:nowrap;border:2px solid}
.topic{margin:6px 0 26px}.topic>h2.tb{margin:0 0 10px;padding:8px 14px;border-left:10px solid;border-radius:8px;font-size:22px}
.topic>h2.tb small{font-size:13px;font-weight:400;color:var(--mut);margin-left:10px}
.topic section.flow h2{font-size:18px}
.arch>img{max-width:100%;background:#fff;border:1px solid var(--line);cursor:zoom-in;border-radius:8px}
.conn{margin:12px 0;padding:0;list-style:none}.conn li{margin:4px 0}
.arrow{font-weight:700}
</style></head><body>
<header><h1>__TITLE__ - story map</h1><div class="sub">__SUB__</div>
<div class="bar" id="bar"></div>
<div class="tabs" id="tabs"></div></header>
<main id="main"></main>
<div id="lb"><button class="close" aria-label="Close" onclick="closeLb()">&#10005;</button><button style="left:14px" aria-label="Previous screen" onclick="lbStep(-1,event)">&#8249;</button><div id="lbcontent" onclick="event.stopPropagation()"><img id="lbi" alt="Diagram preview"><div id="lbd" style="display:none"></div><aside id="lbdetails"></aside></div><div class="cap" id="lbc" onclick="event.stopPropagation()"></div><button style="right:14px" aria-label="Next screen" onclick="lbStep(1,event)">&#8250;</button></div>
<script>
const D=__DATA__, IMG=__IMGS__, OVL=__OVL__, PH=__PH__;
const S={st:new Set(Object.keys(D.statuses)),persona:'',topic:'',q:'',tab:'arch'}, OPEN=new Set();
const TOPICS=Object.fromEntries(D.topics.map(t=>[t.id,t]));const tc=id=>(TOPICS[id]||{color:'#999'}).color;const tt=id=>(TOPICS[id]||{title:id||'Unassigned'}).title;
const TABS=['arch','flows','stories','map','gaps',...(IMG.__overview?['overview']:[])];
const $=(h)=>{const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstChild};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const col=s=>(D.statuses[s]||{color:'#999'}).color;
function sm(u){if(!S.st.has(u.status))return false;if(S.persona&&u.persona!==S.persona)return false;if(S.topic&&u.topic!==S.topic)return false;
 if(S.q){const t=(u.id+' '+u.text+' '+u.where+' '+u.notes+' '+u.screens.map(x=>(D.screens[x]||{}).title).join(' ')).toLowerCase();if(!t.includes(S.q))return false}return true}
function scm(s){const us=s.stories.map(i=>D.stories.find(u=>u.id===i));
 if(S.topic&&s.topic!==S.topic)return false;if(us.length)return us.some(sm);return S.st.has(s.status)&&!S.persona&&!S.q}
function bar(){const b=document.getElementById('bar');b.innerHTML='';const cs=$('<div class="chs"></div>');b.append(cs);
 for(const [k,v] of Object.entries(D.statuses)){const c=$(`<span class="chip ${S.st.has(k)?'':'off'}" style="border-color:${v.color};color:${v.color}">${v.label} (${D.counts[k]})</span>`);
  c.onclick=()=>{S.st.has(k)?S.st.delete(k):S.st.add(k);render()};cs.append(c)}
 const sel=$(`<select><option value="">All personas</option>${D.personas.map(p=>`<option value="${esc(p.id)}" ${S.persona===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select>`);
 sel.onchange=e=>{S.persona=e.target.value;render()};b.append(sel);
 const ts=$(`<select title="Filter by topic"><option value="">All topics</option>${D.topics.map(p=>`<option value="${esc(p.id)}" ${S.topic===p.id?'selected':''}>${esc(p.title)}</option>`).join('')}</select>`);
 ts.onchange=e=>{S.topic=e.target.value;render()};b.append(ts);
 const q=$(`<input placeholder="Search stories..." value="${esc(S.q)}">`);q.oninput=e=>{S.q=e.target.value.toLowerCase();clearTimeout(window._t);window._t=setTimeout(render,200)};b.append(q);
 const t=document.getElementById('tabs');t.innerHTML='';
 for(const [k,l] of [['arch','Architecture'],['flows','Screens by topic'],['stories','Stories'],['map','Story map'],['gaps','Gaps & risks'],['overview','Flows overview']]){
  if(k==='overview'&&!IMG.__overview)continue;
  const x=$(`<button class="${S.tab===k?'on':''}">${l}</button>`);x.onclick=()=>{S.tab=k;render()};t.append(x)}}
const pc=v=>(v*100).toFixed(3)+'%';
function dev(id,click){const s=D.screens[id],f=s.frame,oc=click===false?'':` onclick="event.stopPropagation();lb('${id}')"`;
 if(f&&IMG[id]){const r=f.rect;return `<div class="dv" style="--ar:${f.w/f.h}"${oc}><img class="s" src="${IMG[id]}" alt="${esc(s.title)}" style="left:${pc(r[0]/f.w)};top:${pc(r[1]/f.h)};width:${pc(r[2]/f.w)};height:${pc(r[3]/f.h)};border-radius:${pc(f.rx)}/${pc(f.ry)}"><img class="f" src="${OVL[f.ov]}" alt=""></div>`}
 if(IMG[id])return `<div class="dv" style="--ar:${s.aspect||1}"${oc}><img class="s" src="${IMG[id]}" alt="${esc(s.title)}" style="inset:0;width:100%;height:100%"></div>`;
 if(PH[id])return `<div class="dv ph" style="--ar:${PH[id][1]/PH[id][2]}"><img class="f" src="${PH[id][0]}" alt="Not captured: ${esc(s.not_captured||'screenshot missing')}"></div>`;
 return `<div class="ph">Not captured:<br>${esc(s.not_captured||'screenshot missing')}</div>`}
const badge=s=>`<div class="bd${D.badge==='label'?'':' nolabel'}" title="${D.statuses[s].label}"><i style="background:${col(s)}"></i><span>${D.statuses[s].label}</span></div>`;
function card(id){const s=D.screens[id],c=col(s.status);
 const img=dev(id);
 const out=s.out.map(o=>`<li>${o.dashed?'(optional) ':''}<b>${esc(o.label||'go')}</b> &rarr; <a onclick="go('${o.to}')">${esc((D.screens[o.to]||{}).title||o.to)}</a></li>`).join('');
 const ch=s.stories.map(i=>{const u=D.stories.find(x=>x.id===i);return `<span class="mini" style="background:${col(u.status)}" title="${esc(u.text)}" onclick="goStory('${i}')">${esc(i)}</span>`}).join('');
 return `<div class="card ${s.aspect>=1.15?'land ':s.aspect>=0.85?'sq ':s.aspect&&s.aspect<0.3?'tall ':''}${scm(s)?'':'dim'}" id="scr-${esc(id)}"><div class="tpc" style="background:${tc(s.topic)}22;color:${tc(s.topic)}">${esc(tt(s.topic))}</div><div class="ti">${esc(s.title)}</div><div class="id">${esc(id)}</div>${img}${badge(s.status)}<ul class="out">${out}</ul><div class="chips">${ch}</div></div>`}
function vFlows(){return D.topics.filter(t=>!S.topic||S.topic===t.id).map(t=>{const fl=D.flows.filter(f=>f.topic===t.id);if(!fl.length)return '';
 return `<div class="topic"><h2 class="tb" style="border-color:${t.color};background:${t.color}1a;color:${t.color}">${esc(t.title)}<small>${esc(t.description)}</small></h2>${fl.map(f=>`<section class="flow"><h2>${esc(f.title)}</h2><p class="desc">${esc(f.description)}</p><div class="row">${f.screens.map(card).join('')||'<i>No screens</i>'}</div></section>`).join('')}</div>`}).join('')}
function vArch(){const rows=D.topics.map(t=>`<tr><td><span class="tpill" style="border-color:${t.color};color:${t.color}">${esc(t.title)}</span><div class="sub">${esc(t.description)}</div></td><td data-l="Screens">${t.nscreens}<div class="thumbs small">${Object.keys(D.screens).filter(id=>D.screens[id].topic===t.id&&IMG[id]).map(id=>dev(id)).join('')}</div></td><td data-l="Stories">${t.nstories}</td>${Object.keys(D.statuses).map(k=>`<td data-l="${D.statuses[k].label}" style="color:${col(k)};font-weight:600">${t.counts[k]||0}</td>`).join('')}</tr>`).join('');
 const conns=D.connections.map(c=>`<li><span class="tpill" style="border-color:${tc(c.from)};color:${tc(c.from)}">${esc(tt(c.from))}</span> <span class="arrow">&rarr;</span> <span class="tpill" style="border-color:${tc(c.to)};color:${tc(c.to)}">${esc(tt(c.to))}</span> <span class="sub">${c.labels.map(esc).join(' &middot; ')}</span></li>`).join('');
 return `<div class="arch"><p class="desc">How the app is organised: topic areas and the places users cross from one to another.</p>${IMG['__arch']?`<img src="${IMG['__arch']}" onclick="lb('__arch')" alt="Architecture diagram">`:'<i>Architecture diagram not generated.</i>'}
 <h3>Topics</h3><div class="tw"><table class="atb"><thead><tr><th>Topic</th><th>Screens</th><th>Stories</th>${Object.keys(D.statuses).map(k=>`<th style="color:${col(k)}">${D.statuses[k].label}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>
 <h3>Connections between topics</h3><ul class="conn">${conns||'<li><i>No cross-topic navigation recorded.</i></li>'}</ul></div>`}
function toggleStory(id){OPEN.has(id)?OPEN.delete(id):OPEN.add(id);const row=document.getElementById('st-'+id),details=document.getElementById('detail-'+id);row.setAttribute('aria-expanded',String(OPEN.has(id)));details.classList.toggle('hidden',!OPEN.has(id))}
function storyKey(e,id){if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleStory(id)}}
function vStories(){const rows=D.stories.map(u=>{const th=u.screens.map(s=>(D.screens[s]&&IMG[s])?dev(s):`<span class="mini" style="background:#8a8f98">${esc((D.screens[s]||{}).title||s)}</span>`).join('');
 const detail=[['Where it lives',u.where],['Verified',u.verified],['Notes',u.notes]].filter(([k,v])=>v).map(([k,v])=>`<p><b>${k}:</b> ${esc(v)}</p>`).join('');
 return `<tr id="st-${esc(u.id)}" class="story-row ${sm(u)?'':'hide'}" tabindex="0" aria-expanded="${OPEN.has(u.id)}" aria-controls="detail-${esc(u.id)}" onclick="toggleStory('${u.id}')" onkeydown="storyKey(event,'${u.id}')"><td>${esc(u.id)}</td><td><span class="tpill" style="border-color:${tc(u.topic)};color:${tc(u.topic)}">${esc(tt(u.topic))}</span></td><td>${esc(u.text)}</td><td class="thumbs small">${th}</td><td class="st"><span class="pill" style="background:${col(u.status)}">${D.statuses[u.status]?D.statuses[u.status].label:esc(u.status)}</span></td></tr><tr id="detail-${esc(u.id)}" class="story-details ${sm(u)&&OPEN.has(u.id)?'':'hidden'}"><td colspan="5">${detail||'<p>No evidence or notes recorded.</p>'}<div class="row">${u.screens.filter(id=>D.screens[id]).map(card).join('')}</div></td></tr>`}).join('');
 return `<div class="tw"><table class="stb"><thead><tr><th>ID</th><th>Topic</th><th>Story</th><th>Screens</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`}
function vMap(){const cols=D.flows.map(f=>({id:f.id,t:f.title,topic:f.topic}));if(D.stories.some(u=>!D.flows.find(f=>f.id===u.flow)))cols.push({id:'',t:'Unassigned'});
 let h=`<div class="tw"><div class="grid" style="--n:${cols.length};grid-template-columns:160px repeat(${cols.length},minmax(150px,1fr))"><div class="h"></div>${cols.map(c=>`<div class="h" style="border-top:5px solid ${tc(c.topic)}">${esc(c.t)}<div class="sub">${esc(tt(c.topic))}</div></div>`).join('')}`;
 for(const p of D.personas){h+=`<div class="h pn">${esc(p.name)}</div>`;for(const c of cols){
  h+='<div>'+D.stories.filter(u=>u.persona===p.id&&(D.flows.find(f=>f.id===u.flow)?u.flow:'')===c.id).map(u=>`<span class="mini" style="background:${col(u.status)};opacity:${sm(u)?1:.25}" title="${esc(u.text)}" onclick="goStory('${u.id}')">${esc(u.id)}</span>`).join('')+'</div>'}}
 return h+'</div></div>'}
function vGaps(){return D.gaps.map(g=>`<div class="gap" style="border-color:${D.sev[g.severity]||'#999'}"><b>${esc(g.id)} &middot; ${esc(g.title)}</b> <span class="sub">(${esc(g.severity)})</span><div>${esc(g.detail)}</div>${g.where?`<div class="sub">Where: ${esc(g.where)}</div>`:''}${g.stories.length?`<div class="sub">Stories: ${g.stories.map(esc).join(', ')}</div>`:''}</div>`).join('')||'<i>No gaps recorded.</i>'}
function vOver(){return (IMG['__overview']?`<img src="${IMG['__overview']}" style="max-width:100%;background:#fff;border:1px solid var(--line);cursor:zoom-in" onclick="lb('__overview')">`:'<i>Overview diagram not generated.</i>')}
function render(){bar();if(location.hash!=='#'+S.tab)history.replaceState(null,'','#'+S.tab);const m=document.getElementById('main');m.innerHTML={arch:vArch,flows:vFlows,stories:vStories,map:vMap,gaps:vGaps,overview:vOver}[S.tab]()}
function go(id){closeLb();S.tab='flows';render();const e=document.getElementById('scr-'+id);if(e){e.scrollIntoView({behavior:'smooth',inline:'center',block:'center'});e.classList.add('flash')}}
function goStory(id){closeLb();OPEN.add(id);S.tab='stories';render();const e=document.getElementById('st-'+id);if(e){e.scrollIntoView({behavior:'smooth',block:'center'});e.classList.add('flash')}}
let cur=null;const keys=()=>Object.keys(IMG).filter(k=>!k.startsWith('__')&&D.screens[k]);
function screenDetails(s){const out=s.out.map(o=>`<li>${o.dashed?'(optional) ':''}${esc(o.label||'go')} &rarr; <a href="#flows" onclick="go('${o.to}');return false">${esc((D.screens[o.to]||{}).title||o.to)}</a></li>`).join('');
 const stories=s.stories.map(id=>{const u=D.stories.find(u=>u.id===id);return `<li><a href="#stories" onclick="goStory('${id}');return false">${esc(id)}</a>: ${esc(u.text)}</li>`}).join('');
 return `<h2>${esc(s.title)}</h2>${badge(s.status)}${s.where?`<p><b>Where it lives:</b> ${esc(s.where)}</p>`:''}${s.notes?`<p><b>Notes:</b> ${esc(s.notes)}</p>`:''}<h3>Outgoing actions</h3>${out?`<ul>${out}</ul>`:'<p>No outgoing actions recorded.</p>'}<h3>Stories</h3>${stories?`<ul>${stories}</ul>`:'<p>No stories linked.</p>'}`}
function lb(id){if(!IMG[id])return;cur=id;const L=document.getElementById('lb'),screen=D.screens[id],details=document.getElementById('lbdetails');document.getElementById('lbi').style.display=screen?'none':'';document.getElementById('lbd').style.display=screen?'block':'none';details.style.display=screen?'block':'none';
 if(screen){document.getElementById('lbd').innerHTML=dev(id,false);details.innerHTML=screenDetails(screen)}else document.getElementById('lbi').src=IMG[id];
 const title=id==='__arch'?'Architecture by topic':screen?screen.title:'Flows overview',full=D.full[id];document.getElementById('lbc').innerHTML=esc(title)+(full?` &middot; <a href="${esc(full)}" target="_blank" rel="noopener">Open full resolution (${esc(full)})</a>`:'');L.style.display='flex';L.scrollTop=0;document.getElementById('lbcontent').scrollLeft=0}
function closeLb(){document.getElementById('lb').style.display='none'}
function lbStep(d,e){if(e)e.stopPropagation();const k=keys();if(!k.includes(cur))return;lb(k[(k.indexOf(cur)+d+k.length)%k.length])}
document.getElementById('lb').onclick=closeLb;
document.onkeydown=e=>{const L=document.getElementById('lb');if(L.style.display!=='flex')return;
 if(e.key==='Escape')closeLb();if(e.key==='ArrowRight')lbStep(1,e);if(e.key==='ArrowLeft')lbStep(-1,e)};
const h0=location.hash.slice(1);if(TABS.includes(h0))S.tab=h0;
window.onhashchange=()=>{const h=location.hash.slice(1);if(TABS.includes(h)){S.tab=h;render()}};
render();
</script></body></html>
"""


def gen_html(m, gen, available=None):
    flows = [dict(id=f["id"], title=f["title"], description=f["description"], topic=f["topic"],
                  screens=flow_screens(m, f["id"])) for f in m["flows"]]
    outs = collections.defaultdict(list)
    for e in m["edges"]:
        if e["src"] in m["S"] and e["dst"] in m["S"]:
            outs[e["src"]].append(dict(to=e["dst"], label=e["label"], dashed=e["dashed"]))
    screens = {s["id"]: dict(title=s["title"], status=s["status"], not_captured=s["not_captured"], notes=s["notes"], where=s["where"],
                             out=outs[s["id"]], stories=m["used_by"].get(s["id"], []), topic=s["topic_eff"],
                             aspect=screen_aspect(m, s)) for s in m["screens"]}
    stories = [dict(id=u["id"], persona=u["persona"], personaName=persona_name(m, u["persona"]), text=story_text(m, u),
                    screens=u["screens"], status=u["status"], where=u["where"], verified=u["verified"],
                    notes=u["notes"], flow=u["flow_eff"], topic=u["topic_eff"]) for _tp, _us in stories_by_topic(m) for u in _us]
    topics = [dict(id=r["topic"]["id"], title=r["topic"]["title"], color=r["topic"]["color"], description=r["topic"]["description"],
                   nscreens=len(r["screens"]), nstories=len(r["stories"]), counts=r["counts"]) for r in topic_summary(m)]
    connections = [dict({"from": a, "to": b}, labels=[e["label"] for e in es if e["label"]][:4]) for (a, b), es in cross_topic_edges(m).items()]
    data = dict(app=m["app"]["name"], statuses={k: dict(label=v["label"], color=v["color"]) for k, v in STATUS.items()},
                counts=counts(m["stories"]), personas=[dict(id=p["id"], name=p["name"]) for p in m["personas"]],
                flows=flows, screens=screens, stories=stories,
                gaps=[dict(g) for g in m["gaps"]], topics=topics, connections=connections, sev=dict(TH["sev"]))
    # device frames: the frame is a transparent PNG laid over the screenshot (stored once per distinct frame), so the
    # screenshot keeps its own pixels and aspect ratio; a status badge replaces the old coloured border
    ovl, phs, data["badge"] = {}, {}, TH["device"]["badge"]
    for s in m["screens"]:
        sd = data["screens"][s["id"]]
        sd["frame"] = None
        if not HAVE_PIL:
            continue
        if image_exists(m, s) and load_img(m, s) is not None:
            im = load_img(m, s)
            dv = render_device(m, s, im, detect_model(m, s, im.width, im.height), (560, 800), 1, shadow=False)
            if dv["ov"] is None:
                continue
            fw, fh = dv["size"]
            rx, ry, rw, rh = dv["rect"]
            okey = "%s-%s-%dx%d-%d.%d.%d.%d" % (dv["model"], dv["style"], fw, fh, rx, ry, rw, rh)
            if okey not in ovl:
                b = io.BytesIO()
                dv["ov"].save(b, "PNG", optimize=True)
                ovl[okey] = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
            sd["frame"] = dict(ov=okey, w=fw, h=fh, rect=[rx, ry, rw, rh], rx=dv["rin"] / max(1, rw), ry=dv["rin"] / max(1, rh))
        else:
            pd = placeholder_device(m, s, (360, 520), 1)
            b = io.BytesIO()
            pd["img"].save(b, "PNG", optimize=True)
            phs[s["id"]] = ["data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), pd["size"][0], pd["size"][1]]
    def js(o):
        return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")

    data["full"] = {key: name for key, name in (("__arch", "architecture.png"), ("__overview", "overview.png"))
                    if (available is None or name in available) and os.path.isfile(os.path.join(gen, name))}

    def text_values(obj):
        if isinstance(obj, dict):
            return " ".join(text_values(v) for v in obj.values())
        if isinstance(obj, list):
            return " ".join(text_values(v) for v in obj)
        return str(obj)

    sub = header_line(m) + ((" | " + m["app"]["disclaimer"]) if m["app"]["disclaimer"] else "")
    labels = ("Architecture Screens by topic Stories Story map Gaps & risks Flows overview All personas All topics "
              "Search stories ID Topic Story Screens Status Where it lives Verified Notes Outgoing actions Topics "
              "Connections between topics Not captured screenshot missing optional go Unassigned No screens No gaps recorded "
              "No evidence or notes recorded No outgoing actions recorded No stories linked Open full resolution "
              "How the app is organised: topic areas and the places users cross from one to another. "
              "No cross-topic navigation recorded. Architecture diagram not generated. Overview diagram not generated. "
              "Architecture by topic Flows overview → · ‹ › ✕")
    css = font_face_css(text_values(data) + " " + sub + " " + labels)
    base = (HTML_TEMPLATE.replace("__FONTFACE__", css).replace("__BODYFONT__", font_stack(TH["font"]))
            .replace("__HEADFONT__", heading_font_stack()).replace("__TITLE__", html.escape(m["app"]["name"]))
            .replace("__SUB__", html.escape(sub)).replace("__DATA__", js(data)).replace("__OVL__", js(ovl)).replace("__PH__", js(phs)))
    # Only these in-page previews shrink. The source cache and exported PNG/PDF diagrams keep their native pixels.
    for width, quality, arch_w, over_w in [(480, 72, 2400, 1800), (460, 68, 2200, 1700), (440, 64, 2000, 1600),
                                            (420, 60, 1900, 1500), (400, 56, 1800, 1400), (380, 52, 1700, 1300), (360, 48, 1600, 1200)]:
        imgs = {s["id"]: embed_image(m, s, 1040, width, quality) for s in m["screens"]}
        imgs = {k: v for k, v in imgs.items() if v}
        for key, name in data["full"].items():
            imgs[key] = embed_diagram(os.path.join(gen, name), arch_w if key == "__arch" else over_w, quality)
        page = base.replace("__IMGS__", js(imgs))
        if len(page.encode("utf-8")) < HTML_BUDGET:
            break
    write(os.path.join(gen, "story-map.html"), themeify(page))


# --------------------------------------------------------------------------- PDF one-pager
def topic_schematic(m, d, x0, y0, w, h, Z):
    """Screenshot-free topic map for the one-pager: one box per topic (swimlane order), arrows for cross-topic navigation
    with the number of links. Drawn inside (x0, y0, x0 + w, y0 + h) in design units, scaled by Z."""
    rows = [r for r in topic_summary(m) if r["screens"]]
    n = len(rows)
    if not n:
        return
    gap = 26
    bw = (w - gap * (n - 1)) / n
    arc_h = min(h - 120, 40 + 34 * max(1, n // 2))
    by = y0 + arc_h
    bh = h - arc_h
    centre = {}
    f1, f2 = font(Z(19), True), font(Z(15))
    for i, r in enumerate(rows):
        tp = r["topic"]
        x = x0 + i * (bw + gap)
        centre[tp["id"]] = x + bw / 2
        d.rounded_rectangle((Z(x), Z(by), Z(x + bw), Z(by + bh)), Z(14), fill=tint(tp["color"], 0.9), outline=tp["color"], width=Z(4))
        ls = wrap_px(d, tp["title"], f1, Z(bw - 20))[:3]
        for k, ln in enumerate(ls):
            d.text((Z(x + 12), Z(by + 10 + k * 24)), ln, font=f1, fill=TC("#202124"))
        d.text((Z(x + 12), Z(by + bh - 30)), "%d screens · %d stories" % (len(r["screens"]), len(r["stories"])), font=f2, fill=TC("#5F6368"))
        yy = by + 12 + 24 * len(ls)
        for k_, n_ in r["counts"].items():
            if n_ and yy < by + bh - 40:
                d.ellipse((Z(x + 12), Z(yy + 3), Z(x + 24), Z(yy + 15)), fill=STATUS[k_]["color"])
                d.text((Z(x + 32), Z(yy)), "%d %s" % (n_, STATUS[k_]["label"].lower()), font=f2, fill=TC("#3C4043"))
                yy += 22
    pairs = collections.Counter({k: len(v) for k, v in cross_topic_edges(m).items()})
    order = sorted(pairs, key=lambda k: abs(centre.get(k[0], 0) - centre.get(k[1], 0)))
    for lvl, (a, b) in enumerate(order):
        if a not in centre or b not in centre:
            continue
        col = hexrgb(m["T"][a]["color"]) if a in m["T"] else hexrgb(TH["primary"])
        off = (-1 if centre[b] < centre[a] else 1) * 10
        ya = by - (14 + (lvl % max(1, (arc_h - 20) // 18)) * 18)
        xa, xb = centre[a] + off, centre[b] + off
        for (p, q) in (((xa, by), (xa, ya)), ((xa, ya), (xb, ya)), ((xb, ya), (xb, by - 4))):
            d.line((Z(p[0]), Z(p[1]), Z(q[0]), Z(q[1])), fill=col, width=Z(4))
        arrow_head(d, (Z(xb), Z(ya)), (Z(xb), Z(by)), col, Z(14))
        if pairs[(a, b)] > 1:
            d.text((Z((xa + xb) / 2), Z(ya - 12)), "x%d" % pairs[(a, b)], font=f2, fill=col, anchor="mm")


def gen_onepager(m, gen, pdf=True):
    """One page: status counts, topic map, topic table, top gaps and a contact sheet of every screen. Drawn at a zoom Z
    chosen so that every screenshot in the contact sheet is at >= its native pixels; the page grows downwards as needed."""
    if not HAVE_PIL:
        return "skipped one-pager (needs Pillow)"
    _DEV_CACHE.clear()
    th = 300                                                        # design height of a screen on the sheet
    zz = native_zoom(m, (10 ** 5, th))                              # pixels per design unit
    Z = lambda v: max(1, int(round(v * zz)))
    W0, H0, M = 2480, 1754, 70                                      # A3 landscape at 150 dpi (design units), height grows
    set_diagram("one-pager")
    dm = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    top = 320
    RX = 1640
    blocks = [(r["topic"]["title"], list(r["screens"]), r["topic"]["color"]) for r in topic_summary(m) if r["screens"]]
    shots = {s["id"]: load_img(m, s) for _, ss, _ in blocks for s in ss}
    sheet_w = W0 - 2 * M
    SEG_MIN, GAPX, LABEL_H, TITLE_H = 210, 14, 56, 36   # a title needs some width; room for title above and label below

    def dev_w(s, im):   # device width (design units) of screen s at sheet height th
        return min(device_box_width(m, s, im, th * zz) / zz, sheet_w)

    def sheet_rows():
        """Lay the screens out at height th: each at its own aspect ratio, topics wrap onto new rows."""
        rows, x = [[]], 0
        for title, ss, tcol in blocks:
            seg = None
            for s in ss:
                w = dev_w(s, shots[s["id"]])
                need = (GAPX if seg and seg["ws"] else 0) + w
                if seg is None or x + need > sheet_w:
                    if seg is not None or x + 40 + max(w, SEG_MIN) > sheet_w:
                        if x > 0:
                            rows.append([])
                            x = 0
                    elif x > 0:
                        x += 40
                    seg = dict(title=title, tcol=tcol, x0=x, ss=[], ws=[], cont=any(sg["title"] == title for sg in rows[-1]) or any(
                        sg["title"] == title for rw in rows for sg in rw))
                    rows[-1].append(seg)
                    need = w
                seg["ss"].append(s)
                seg["ws"].append(w)
                x += need
            if seg is not None:
                x = max(x, seg["x0"] + SEG_MIN)
        return rows
    rows = sheet_rows()
    n_topics = len(topic_summary(m))
    right_min = 78 + n_topics * max(24, min(38, 270 // max(1, n_topics))) + 60 + (110 if m["gaps"] else 30)
    reg = max(420, right_min)                                        # height of the topic map / table block
    sy = top + 50 + reg + 40
    body_h = sy + 50 + len(rows) * (th + TITLE_H + LABEL_H)
    H = max(H0, body_h + 110)
    img = Image.new("RGB", (Z(W0), Z(H)), TH["bg"])
    d = ImageDraw.Draw(img)
    d.text((Z(M), Z(40)), m["app"]["name"] + " - story map", font=font(Z(64), True, True), fill=TC("#202124"))
    sub = header_line(m) + ("   |   " + m["app"]["summary"] if m["app"]["summary"] else "")
    while len(sub) > 3 and tw(d, sub, font(Z(26))) > Z(W0 - 2 * M):
        sub = sub[:-4].rstrip() + "..."
    d.text((Z(M), Z(120)), sub, font=font(Z(26)), fill=TC("#5F6368"))
    c = counts(m["stories"])
    total = max(1, len(m["stories"]))
    x, y = M, 180
    for k, n in c.items():
        d.rounded_rectangle((Z(x), Z(y), Z(x + 330), Z(y + 110)), Z(16), fill=STATUS[k]["color"])
        d.text((Z(x + 20), Z(y + 8)), str(n), font=font(Z(60), True), fill=on_color())
        d.text((Z(x + 120), Z(y + 22)), STATUS[k]["label"], font=font(Z(28), True), fill=on_color())
        d.text((Z(x + 120), Z(y + 62)), "%d%% of stories" % round(100 * n / total), font=font(Z(22)), fill=on_color())
        x += 350
    d.text((Z(x + 20), Z(y + 20)), "%d stories · %d screens · %d flows · %d personas" % (
        len(m["stories"]), len(m["screens"]), len(m["flows"]), len(m["personas"])), font=font(Z(28)), fill=TC("#202124"))
    d.text((Z(x + 20), Z(y + 64)), "Built = verified in code or on a running app. Unverified = not checked yet.", font=font(Z(22)), fill=TC("#5F6368"))
    d.text((Z(M), Z(top)), "Topics and how they connect (screens: see architecture.png)", font=font(Z(30), True, True), fill=TC("#202124"))
    topic_schematic(m, d, M, top + 50, RX - M - 50, reg, Z)
    tx = RX
    tbl_w = W0 - M - RX
    cols = [("Topic", 0), ("Scr.", 262), ("Stor.", 330)] + [(STATUS[k]["label"].replace("Unverified", "Unver.").replace("Partly built", "Partly"), 410 + 88 * i) for i, k in enumerate(STATUS)]
    d.text((Z(tx), Z(top)), "Topics", font=font(Z(30), True, True), fill=TC("#202124"))
    ty = top + 50
    for name, off in cols:
        d.text((Z(tx + 14 + off), Z(ty)), name, font=font(Z(16), True), fill=TC("#5F6368"))
    ty += 28
    rows_t = topic_summary(m)
    rh = max(24, min(38, 270 // max(1, len(rows_t))))
    for r in rows_t:
        tp = r["topic"]
        d.rounded_rectangle((Z(tx), Z(ty), Z(tx + tbl_w), Z(ty + rh - 4)), Z(8), fill=tint(tp["color"], 0.9))
        d.rectangle((Z(tx), Z(ty), Z(tx + 12), Z(ty + rh - 4)), fill=tp["color"])
        fz = 20 if rh >= 34 else 17
        yy = ty + (rh - fz) // 2 - 4
        title = tp["title"]
        while len(title) > 3 and tw(d, title, font(Z(fz), True)) > Z(235):
            title = title[:-4].rstrip() + "..."
        d.text((Z(tx + 26), Z(yy)), title, font=font(Z(fz), True), fill=TC("#202124"))
        d.text((Z(tx + 14 + 262), Z(yy)), str(len(r["screens"])), font=font(Z(fz)), fill=TC("#202124"))
        d.text((Z(tx + 14 + 330), Z(yy)), str(len(r["stories"])), font=font(Z(fz)), fill=TC("#202124"))
        for i, k in enumerate(STATUS):
            n = r["counts"].get(k, 0)
            d.text((Z(tx + 14 + 410 + 88 * i), Z(yy)), str(n), font=font(Z(fz), bool(n)), fill=STATUS[k]["color"] if n else TC("#9AA0A6"))
        ty += rh
    gy0 = ty + 40
    d.text((Z(tx), Z(gy0)), "Top gaps and risks", font=font(Z(30), True, True), fill=TC("#202124"))
    gy = gy0 + 50
    order = {s: i for i, s in enumerate(SEVERITIES)}
    for g in sorted(m["gaps"], key=lambda g: order.get(g["severity"], 9))[:8]:
        colr = TH["sev"].get(g["severity"], "#999999")
        lines = wrap_px(d, g["title"], font(Z(22), True), Z(tbl_w - 40))[:2]
        if gy + 50 + 28 * len(lines) > top + 50 + reg:
            break
        d.rounded_rectangle((Z(tx), Z(gy + 2), Z(tx + 12), Z(gy + 28 + 28 * len(lines))), Z(4), fill=colr)
        d.text((Z(tx + 26), Z(gy)), "%s  |  %s severity" % (g["id"], g["severity"]), font=font(Z(18)), fill=TC("#5F6368"))
        for i, ln in enumerate(lines):
            d.text((Z(tx + 26), Z(gy + 26 + i * 28)), ln, font=font(Z(22), True), fill=TC("#202124"))
        gy += 50 + 28 * len(lines)
    if not m["gaps"]:
        d.text((Z(tx), Z(gy)), "None recorded.", font=font(Z(24)), fill=TC("#5F6368"))
    d.text((Z(M), Z(sy)), "Screens by topic (device frames at native resolution; the dot under each shows its status)", font=font(Z(30), True, True), fill=TC("#202124"))
    sy += 50
    fl = font(Z(15))
    for ri, row in enumerate(rows):
        base_y = sy + ri * (th + TITLE_H + LABEL_H)
        for seg in row:
            ttl = seg["title"] + (" (cont.)" if seg["cont"] else "")
            nxt = [sg["x0"] for sg in row if sg["x0"] > seg["x0"]]
            span = (min(nxt) if nxt else sheet_w) - seg["x0"] - 14      # the title may use all the room up to the next block
            while len(ttl) > 3 and tw(d, ttl, font(Z(22), True)) > Z(span):
                ttl = ttl[:-4].rstrip() + "..."
            d.text((Z(M + seg["x0"]), Z(base_y)), ttl, font=font(Z(22), True), fill=seg["tcol"])
            cx = M + seg["x0"]
            for s, w in zip(seg["ss"], seg["ws"]):
                yy = base_y + TITLE_H
                dv = screen_device(m, s, (w, th), zz)           # the whole screenshot inside its device frame, aspect preserved
                px, py = Z(cx) + (Z(w) - dv["size"][0]) // 2, Z(yy) + (Z(th) - dv["size"][1]) // 2
                img.paste(dv["img"], (px, py), dv["img"])
                lab = s["title"]
                if tw(d, lab, fl) > Z(w + 10):
                    while len(lab) > 1 and tw(d, lab + "...", fl) > Z(w + 10):
                        lab = lab[:-1]
                    lab = lab.rstrip() + "..."
                d.text((Z(cx), Z(yy + th + 8)), lab, font=fl, fill=TC("#3C4043"))
                stv = STATUS[s["status"]]            # status badge: a dot (and a label) under the device, no coloured border
                d.ellipse((Z(cx), Z(yy + th + 32), Z(cx + 13), Z(yy + th + 45)), fill=stv["color"])
                if TH["device"]["badge"] == "label":
                    d.text((Z(cx + 20), Z(yy + th + 38)), stv["label"], font=fl, fill=TC("#5F6368"), anchor="lm")
                cx += w + GAPX
    if m["app"]["disclaimer"]:
        dis = m["app"]["disclaimer"]
        while len(dis) > 3 and tw(d, dis, font(Z(20))) > Z(W0 - 2 * M):
            dis = dis[:-4].rstrip() + "..."
        d.text((Z(M), Z(H - 80)), dis, font=font(Z(20)), fill=TC("#3C4043"))
    d.text((Z(M), Z(H - 44)), "Generated by storymap.py from stories.yaml - edit the source, not this file.", font=font(Z(18)), fill=TC("#80868B"))
    set_diagram("other")
    png = os.path.join(gen, "one-pager.png")
    img.save(png, optimize=True)
    if pdf:
        img.save(os.path.join(gen, "one-pager.pdf"), "PDF", resolution=150.0 * zz)
    _DEV_CACHE.clear()
    return ""


# --------------------------------------------------------------------------- theme (follow the documented app's design)
import colorsys, copy, tempfile, urllib.request, urllib.parse

STATUS_DEFAULT = copy.deepcopy(STATUS)
SEV_DEFAULT = {"high": "#D93025", "medium": "#E8A33D", "low": "#9AA0A6"}
DEFAULT_THEME = dict(dark=False, font="", heading_font="", fallback="sans-serif", bg="#FFFFFF", ink="#202124", ink2="#3C4043",
                     muted="#5F6368", muted2="#80868B", surface="#F7F8F9", surface2="#F1F3F4", border="#DADCE0",
                     primary="#2D7A5C", secondary="#C9733E", accent_dark="#1F5A43", gray="#9AA0A6",
                     portal_in="#DDF1E8", portal_out="#FFE9DD", border_accent="#B7DCCB",
                     embed_fonts=False, device=dict(style="auto", model="", badge="label", frames=""))
TH = dict(DEFAULT_THEME, sev=dict(SEV_DEFAULT), font_files={})
# default literal -> themed value, applied to generated text (dot / mermaid / html) and to PIL colours via TC()
_LITERALS = {"#202124": "ink", "#3C4043": "ink2", "#5F6368": "muted", "#80868B": "muted2", "#F1F3F4": "surface2",
             "#EEF1F3": "surface2", "#F7F8F9": "surface", "#DADCE0": "border", "#9AA0A6": "gray", "#2D7A5C": "primary",
             "#1F5A43": "accent_dark", "#B7DCCB": "border_accent", "#FFE9DD": "portal_out", "#DDF1E8": "portal_in",
             "#FFFFFF": "bg", "#FFF": "bg"}
_LIT_RE = re.compile("|".join(re.escape(k) + r"(?![0-9A-Fa-f])" for k in sorted(_LITERALS, key=len, reverse=True)), re.I)


def TC(color):
    """Themed value of a default colour literal (identity for anything else)."""
    k = _LITERALS.get(str(color).upper())
    return TH[k] if k else color


def themeify(text):
    """Replace default colour literals / font in generated text (Graphviz, Mermaid, HTML) with the theme."""
    text = _LIT_RE.sub(lambda mt: TH[_LITERALS[mt.group(0).upper()]], text)
    text = text.replace('BGCOLOR="white"', 'BGCOLOR="%s"' % TH["bg"])
    if TH.get("dark"):                     # labels on status chips: page-coloured text on a bright chip
        text = text.replace('COLOR="white"', 'COLOR="%s"' % TH["bg"])
    return text


def is_hex(x):
    return bool(re.match(r"^#[0-9A-Fa-f]{6}$", str(x)))


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _hsl(h):
    r, g, b = _rgb(h)
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    return hh * 360.0, s, l


def _from_hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, max(0, min(1, l)), max(0, min(1, s)))
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def _lum(h):
    r, g, b = _rgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(a, b, t):
    """Colour a moved a fraction t of the way to colour b."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(round((x + (y - x) * t) * 255) for x, y in zip(ra, rb))


def _lift(c, lmin=0.62):
    """Lighten a colour so it reads on a dark background (hue kept, saturation capped)."""
    h, s, l = _hsl(c)
    return _from_hsl(h, min(s, 0.85), max(l, lmin))


def _hue_toward(h, target, t):
    d = ((target - h + 540) % 360) - 180
    return h + d * t


def derive_theme(primary, secondary=None):
    """Harmonious UI/status/severity colours from one or two brand colours (same saturation/lightness family)."""
    h, s, l = _hsl(primary)
    sec = secondary if is_hex(secondary or "") else _from_hsl(h + 35, s, l)
    s0, l0 = max(0.35, min(0.70, s)), max(0.40, min(0.52, l))
    pull = lambda hue: _hue_toward(hue, h, 0.15)  # nudge semantic hues toward the brand hue
    t = dict(primary=primary, secondary=sec, accent_dark=_from_hsl(h, s, l * 0.55),
             ink=_from_hsl(h, min(s, 0.20), 0.13), ink2=_from_hsl(h, min(s, 0.15), 0.25),
             muted=_from_hsl(h, min(s, 0.12), 0.40), muted2=_from_hsl(h, min(s, 0.10), 0.55),
             border=_from_hsl(h, min(s, 0.15), 0.82), surface=_from_hsl(h, min(s, 0.25), 0.975),
             surface2=_from_hsl(h, min(s, 0.15), 0.95), gray=_from_hsl(h, 0.08, 0.62),
             border_accent=_from_hsl(h, s0, 0.80), portal_in=_from_hsl(h, s0, 0.92), portal_out=_from_hsl(_hsl(sec)[0], s0, 0.92))
    status = dict(built=_from_hsl(pull(150), s0, l0), partly=_from_hsl(pull(40), s0, max(l0, 0.50)),
                  unverified=_from_hsl(h + 45, s0, l0), missing=_from_hsl(h, 0.08, 0.58))
    sev = dict(high=_from_hsl(pull(355), s0, l0), medium=status["partly"], low=status["missing"])
    return t, status, sev


def derive_topic_colors(n, primary):
    h, s, l = _hsl(primary)
    s0, l0 = max(0.35, min(0.70, s)), max(0.40, min(0.52, l))
    # an analogous span around the brand hue (not the whole colour wheel) keeps the set harmonious
    span = min(160.0, 28.0 * max(n - 1, 1))
    return [_from_hsl(h - span * 0.45 + (span * i / max(n - 1, 1)), s0, l0 + (0.03 if i % 2 else -0.02)) for i in range(n)]


# ---- fonts
FONT_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "storymap", "fonts")


def _slug(f):
    return re.sub(r"[^a-z0-9]+", "-", f.lower()).strip("-")


# Nothing is uploaded; the viewer makes no requests. This optional Google Fonts download
# is the tool's only network request, enabled by theme.google_font (off by default).
def _google_fetch(family):
    """Download an open-licensed Google Font (regular + bold TTF) into a cache OUTSIDE the repo."""
    if os.environ.get("STORYMAP_NO_NETWORK"):
        return None
    d = os.path.join(FONT_CACHE, _slug(family))
    reg, bold = os.path.join(d, "regular.ttf"), os.path.join(d, "bold.ttf")
    if os.path.isfile(reg) and os.path.isfile(bold):
        return reg, bold
    try:
        url = "https://fonts.googleapis.com/css2?family=%s:wght@400;700" % urllib.parse.quote(family).replace("%20", "+")
        css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.0"}), timeout=15).read().decode()
        faces = re.findall(r"font-weight:\s*(\d+);\s*src:\s*url\(([^)]+)\)", css)
        os.makedirs(d, exist_ok=True)
        for w, u in faces:
            if w in ("400", "700") and u.endswith(".ttf"):
                with open(reg if w == "400" else bold, "wb") as f:
                    f.write(urllib.request.urlopen(u, timeout=30).read())
        if os.path.isfile(reg):
            if not os.path.isfile(bold):
                shutil.copy(reg, bold)
            return reg, bold
    except Exception as ex:
        print("  note  could not download Google Font '%s' (%s); using a fallback" % (family, ex.__class__.__name__))
    return None


def _system_font(family):
    """Find regular/bold files of an installed font family (fontconfig if present, else common font folders)."""
    out = {}
    if shutil.which("fc-match"):
        for key, style in (("regular", "regular"), ("bold", "bold")):
            try:
                r = subprocess.run(["fc-match", "-f", "%{family}|%{file}", "%s:style=%s" % (family, style)],
                                   capture_output=True, text=True, timeout=10).stdout
                fam, _, path = r.partition("|")
                if family.lower() in fam.lower() and os.path.isfile(path) and path.lower().endswith((".ttf", ".otf", ".ttc")):
                    out[key] = path
            except Exception:
                pass
    if "regular" not in out:
        want = re.sub(r"[^a-z0-9]", "", family.lower())
        dirs = ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"), "/usr/share/fonts", os.path.expanduser("~/.fonts")]
        for base in dirs:
            for root, _, files in os.walk(base):
                for fn in files:
                    low = re.sub(r"[^a-z0-9]", "", fn.lower().rsplit(".", 1)[0])
                    if fn.lower().endswith((".ttf", ".otf", ".ttc")) and low.startswith(want):
                        key = "bold" if "bold" in low and "italic" not in low else ("regular" if low in (want, want + "regular") else None)
                        if key and key not in out:
                            out[key] = os.path.join(root, fn)
    if "regular" in out:
        return out["regular"], out.get("bold", out["regular"])
    return None


def resolve_font(m, family, font_file, bold_file, google):
    """-> (regular_path, bold_path, origin) or None. origin: 'file' | 'system' | 'google'."""
    if font_file:
        p = os.path.join(m["root"], font_file)
        if os.path.isabs(font_file) or ".." in font_file.replace("\\", "/").split("/") or not os.path.isfile(p):
            print("  note  theme font_file '%s' must be a relative path inside the folder and exist; ignoring" % font_file)
        else:
            b = os.path.join(m["root"], bold_file) if bold_file and os.path.isfile(os.path.join(m["root"], bold_file)) else p
            return p, b, "file"
    if not family:
        return None
    sysf = _system_font(family)
    if sysf:
        return sysf[0], sysf[1], "system"
    if google:
        g = _google_fetch(family)
        if g:
            return g[0], g[1], "google"
    return None


def apply_theme(m):
    """Fill the module-level theme (TH, STATUS, severity colours, fonts) from stories.yaml `theme:`."""
    raw = m["raw"].get("theme") or {}
    if not isinstance(raw, dict):
        raise SourceError("`theme:` must be a mapping")
    g = lambda k: _s(raw, k)
    th = dict(DEFAULT_THEME)
    if "embed_fonts" in raw:
        value = raw["embed_fonts"]
        if isinstance(value, bool):
            th["embed_fonts"] = value
        elif isinstance(value, str) and value.lower() in ("true", "false"):
            th["embed_fonts"] = value.lower() == "true"
        else:
            raise SourceError("theme.embed_fonts must be a bool (true or false)")
    status = {k: v["color"] for k, v in STATUS_DEFAULT.items()}
    sev = dict(SEV_DEFAULT)
    primary = g("primary") or g("accent")
    m["theme_derived"] = False
    if primary:
        if not is_hex(primary):
            raise SourceError("theme.primary must look like #RRGGBB")
        t, status, sev = derive_theme(primary, g("secondary"))
        th.update(t)
        m["theme_derived"] = True
    for key, names in (("bg", ("background", "bg")), ("ink", ("text", "ink")), ("muted", ("muted",)),
                       ("surface", ("surface",)), ("border", ("border",)), ("secondary", ("secondary",))):
        for n in names:
            if g(n):
                if not is_hex(g(n)):
                    raise SourceError("theme.%s must look like #RRGGBB" % n)
                th[key] = g(n)
    given = {k for k, names in (("bg", ("background", "bg")), ("ink", ("text", "ink")), ("muted", ("muted",)), ("surface", ("surface",)),
                                ("border", ("border",))) for n in names if g(n)}
    mode = g("mode").lower()
    dark = mode == "dark" or (mode != "light" and "bg" in given and _lum(th["bg"]) < 0.30)
    th["dark"] = dark
    if dark:   # dark theme: black page and lanes, light text; colours are lifted so they stay legible on black
        if "bg" not in given:
            th["bg"] = "#0B0C0E"
        h0, s0 = _hsl(th["primary"])[:2]
        s0 = max(0.35, min(0.70, s0))
        mix = lambda a: _mix(th["bg"], "#FFFFFF", a)
        for k, v in dict(ink="#F2F3F5", ink2="#D5D8DC", muted="#A5ABB3", muted2="#80868F", border="#383C42", surface=mix(0.06), surface2=mix(0.10),
                         gray="#8B929B", border_accent=_from_hsl(h0, s0, 0.35), portal_in=_from_hsl(h0, s0, 0.17),
                         portal_out=_from_hsl(_hsl(th["secondary"])[0], s0, 0.17)).items():
            if k not in given:
                th[k] = v
        th["primary"] = _lift(th["primary"])
        th["secondary"] = _lift(th["secondary"])
        th["accent_dark"] = _lift(th["accent_dark"], 0.75)
        for d_, k_ in ((status, "status"), (sev, "severity")):
            sub_ = raw.get(k_) if isinstance(raw.get(k_), dict) else {}
            for k in d_:
                if k not in sub_:
                    d_[k] = _lift(d_[k])
    for grp, dest in (("status", status), ("severity", sev)):
        sub = raw.get(grp) or {}
        if isinstance(sub, dict):
            for k, v in sub.items():
                if k in dest and is_hex(str(v)):
                    dest[k] = str(v)
    th["fallback"] = g("fallback") if g("fallback") in ("serif", "sans-serif", "monospace") else "sans-serif"
    dev = raw.get("device") if isinstance(raw.get("device"), dict) else {}
    dg = lambda k: _s(dev, k).lower() or _s(raw, "device_" + k).lower()
    th["device"] = dict(style=dg("style") or "auto", model=dg("model"), badge=dg("badge") if dg("badge") in ("label", "dot") else "label",
                        frames=_s(dev, "frames") or _s(raw, "device_frames"))
    th["font"], th["heading_font"] = g("font"), g("heading_font") or g("font")
    google = g("google_font").lower() in ("true", "yes", "1")
    files = {}
    for slot, fam, ff, bf in (("body", th["font"], g("font_file"), g("font_file_bold")),
                              ("head", th["heading_font"], g("heading_font_file"), g("heading_font_file_bold"))):
        if slot == "head" and fam == th["font"] and not ff:
            files["head"] = files.get("body")
            continue
        files[slot] = resolve_font(m, fam, ff, bf, google)
    th["font_files"] = files
    th["sev"] = sev
    TH.clear()
    TH.update(th)
    _FONTS.clear()
    for k, v in STATUS_DEFAULT.items():
        STATUS[k]["color"] = status[k]
        STATUS[k]["bg"] = (_from_hsl(_hsl(status[k])[0], 0.35, 0.16) if th["dark"] else _from_hsl(*_hsl(status[k])[:1], 0.55, 0.93)) if (
            m["theme_derived"] or th["dark"]) else v["bg"]
    # topic colours: explicit > derived from the palette > legacy palette
    n = len(m["topics"])
    derived = derive_topic_colors(n, th["primary"]) if m["theme_derived"] else TOPIC_PALETTE
    if th["dark"]:
        derived = [_lift(c) for c in derived]
    for i, tp in enumerate(m["topics"]):
        if not tp.get("color"):
            tp["color"] = derived[i % len(derived)]
    m["theme"] = th


def font_stack(name, fallback=None):
    fb = fallback or TH["fallback"]
    base = '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif' if fb == "sans-serif" else (
        'Georgia,"Times New Roman",serif' if fb == "serif" else 'ui-monospace,Menlo,monospace')
    return ('"%s",%s' % (name, base)) if name else base


def heading_font_stack():
    serif = {"georgia", "times", "times new roman", "baskerville", "palatino", "palatino linotype", "garamond",
             "cambria", "cochin", "charter", "didot", "hoefler text", "iowan old style", "new york", "merriweather",
             "lora", "libre baskerville", "playfair display", "cormorant", "source serif pro", "source serif 4", "noto serif", "pt serif"}
    return font_stack(TH["heading_font"], "serif" if TH["heading_font"].lower() in serif else None)


def font_face_css(text=""):
    """Opt-in WOFF2 subsets: body regular/bold and, when distinct, bold headings."""
    if not TH.get("embed_fonts"):
        return ""
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
        import brotli  # noqa: F401; WOFF2 compression is optional
    except ImportError:
        print("  note  embedded fonts need fontTools and brotli; using system fonts")
        return ""
    css, seen = "", set()
    for slot in ("body", "head"):
        spec = TH["font_files"].get(slot)
        name = TH["font"] if slot == "body" else TH["heading_font"]
        if not spec or not name:
            continue
        for weight, path in (((400, spec[0]), (700, spec[1])) if slot == "body" else ((700, spec[1]),)):
            key = (name, weight, path)
            if key in seen or not os.path.isfile(path):
                continue
            seen.add(key)
            face = None
            try:
                face = TTFont(path, fontNumber=0)
                options = subset.Options()
                options.drop_tables += ["FFTM"]
                sub = subset.Subsetter(options=options)
                sub.populate(text=text)
                sub.subset(face)
                face.flavor = "woff2"
                out = io.BytesIO()
                face.save(out)
                css += '@font-face{font-family:"%s";font-weight:%d;src:url(data:font/woff2;base64,%s) format("woff2")}\n' % (
                    name, weight, base64.b64encode(out.getvalue()).decode())
            except Exception as ex:
                print("  note  could not subset font '%s' (%s); using system fonts" % (name, ex.__class__.__name__))
            finally:
                if face is not None:
                    face.close()
    return css


def fontconfig_env():
    """Environment for Graphviz so it can see downloaded/user fonts that are not installed system-wide."""
    dirs = {os.path.dirname(p) for spec in TH["font_files"].values() if spec for p in spec[:2]}
    dirs = [d for d in dirs if not d.startswith(("/System", "/Library", "/usr/share/fonts"))]
    env = dict(os.environ)
    if dirs:
        conf = os.path.join(tempfile.gettempdir(), "storymap-fonts.conf")
        with open(conf, "w") as f:
            f.write('<?xml version="1.0"?><fontconfig>')
            for inc in ("/etc/fonts/fonts.conf", "/opt/homebrew/etc/fonts/fonts.conf", "/usr/local/etc/fonts/fonts.conf"):
                f.write('<include ignore_missing="yes">%s</include>' % inc)
            for d in dirs:
                f.write("<dir>%s</dir>" % d)
            f.write("</fontconfig>")
        env["FONTCONFIG_FILE"] = conf
    return env


# ---- theme-from: draft a `theme:` block from an app's design tokens
HEX_RE = re.compile(r"(?:#|0x)([0-9A-Fa-f]{6})\b")
SKIP_DIRS = {".git", "node_modules", "Pods", "build", "DerivedData", ".build", "dist", "vendor", "SourcePackages", "Carthage"}


def _sat_light(h):
    _, s, l = _hsl("#" + h)
    return s, l


KNOWN_FONT_RE = re.compile(r"(Georgia|Helvetica Neue|Helvetica|Avenir|Roboto|Merriweather|Poppins|Montserrat|Nunito|Playfair Display|"
                           r"Charter|Palatino|Baskerville|Futura|Menlo|Courier|Open Sans|Source Sans|(?<![A-Za-z])Inter(?![A-Za-z])|(?<![A-Za-z])Lato(?![A-Za-z]))")


def theme_from(path, limit=4000):
    """Scan an app folder for colours and fonts; print candidates and a draft `theme:` block."""
    named, freq, fonts, files_scanned = [], collections.Counter(), collections.Counter(), 0
    name_re = re.compile(r"(?:(?:let|var|val|const|static|public|--)\s*)?([A-Za-z][\w-]*)\s*[:=(]+[^\n#]*?(?:#|0x)([0-9A-Fa-f]{6})\b")
    font_re = re.compile(r"font-family\s*:\s*([^;}\n]+)|fontFamily\s*[:=]\s*['\"]([^'\"]+)|UIFont\(name:\s*\"([^\"]+)|Font\.custom\(\"([^\"]+)|\.custom\(\"([^\"]+)|FontFamily\(\"([^\"]+)")
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            if files_scanned >= limit:
                break
            ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, path)
            try:
                if fn == "Contents.json" and ".colorset" in root:  # iOS asset-catalog colour
                    data = json.load(open(full))
                    comp = data["colors"][0]["color"]["components"]
                    vals = [float(comp[k]) if "." in str(comp[k]) else int(str(comp[k]), 0) / 255.0 for k in ("red", "green", "blue")]
                    hx = "%02X%02X%02X" % tuple(round(v * 255) for v in vals)
                    named.append((os.path.basename(root).replace(".colorset", ""), hx, rel))
                    freq[hx.upper()] += 3
                    continue
                if ext not in ("swift", "kt", "java", "xml", "css", "scss", "less", "ts", "tsx", "js", "jsx", "json", "dart", "m", "h", "xcconfig", "plist"):
                    continue
                if os.path.getsize(full) > 400_000:
                    continue
                text = open(full, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            files_scanned += 1
            for mt in name_re.finditer(text):
                named.append((mt.group(1), mt.group(2), rel))
            for mt in HEX_RE.finditer(text):
                freq[mt.group(1).upper()] += 1
            for mt in KNOWN_FONT_RE.finditer(text):  # families named inside identifiers, e.g. boldGeorgiaTitle1
                fonts[mt.group(1)] += 1
            for mt in font_re.finditer(text):
                f = next(x for x in mt.groups() if x)
                for part in f.split(",")[:2]:
                    part = part.strip().strip("'\"")
                    if part and part.lower() not in ("inherit", "sans-serif", "serif", "monospace", "system-ui", "-apple-system", "initial"):
                        fonts[part] += 1
    prio = ["primary", "accent", "brand", "tint", "link", "progressive", "blue600", "blue500"]
    pick = None
    for p in prio:
        for n, hx, rel in named:
            if p in n.lower() and 0.25 < _sat_light(hx)[0]:
                pick = (n, hx.upper(), rel)
                break
        if pick:
            break
    if not pick:
        sat = [(c, hx) for hx, c in freq.most_common(40) if _sat_light(hx)[0] > 0.35 and 0.25 < _sat_light(hx)[1] < 0.75]
        if sat:
            pick = ("most frequent saturated colour", sat[0][1], "")
    print("# Scanned %d files under the given folder.\n" % files_scanned)
    print("# Named colour candidates (name  hex  file):")
    seen = set()
    for n, hx, rel in named:
        k = (n.lower(), hx.upper())
        if k in seen or not any(w in n.lower() for w in ("primary", "accent", "brand", "tint", "link", "background", "paper", "surface", "text", "border", "success", "warning", "error", "danger", "green", "yellow", "red", "blue", "gray", "grey")):
            continue
        seen.add(k)
        if len(seen) > 40:
            break
        print("#   %-24s #%s  %s" % (n, hx.upper(), rel))
    print("\n# Most frequent colours: " + ", ".join("#%s x%d" % (h, c) for h, c in freq.most_common(8)))
    print("# Fonts mentioned: " + (", ".join("%s x%d" % (f, c) for f, c in fonts.most_common(6)) or "none found (system font?)"))
    print("\n# Draft - REVIEW against the app's real design, then paste into stories.yaml:")
    print("theme:")
    if pick:
        print("  primary: \"#%s\"          # from %s" % (pick[1], pick[0]))
    else:
        print("  # primary: \"#RRGGBB\"     # no obvious brand colour found - set it by hand")
    print("  # text: \"#RRGGBB\"; background: \"#FFFFFF\" (light always); surface: ...; border: ...")
    top_font = fonts.most_common(1)[0][0] if fonts else ""
    print("  font: %s" % (json.dumps(top_font) if top_font else "\"\"          # family name; if it is proprietary just name it (fallback is used)"))
    print("  google_font: false          # off by default; true = download that family from Google Fonts (the only network request)")
    print("  # status:   { built: \"#...\", partly: \"#...\", unverified: \"#...\", missing: \"#...\" }   # default: derived from primary")
    print("  # severity: { high: \"#...\", medium: \"#...\", low: \"#...\" }")
    return 0


# --------------------------------------------------------------------------- set-status (text edit, keeps comments)
def set_status(src_dir, story_id, status, verified=None):
    path = find_source(src_dir)
    if path.endswith(".json"):
        raise SourceError("set-status edits YAML sources; edit the JSON by hand")
    if status not in STATUS:
        raise SourceError("status must be one of: " + ", ".join(STATUS))
    with open(path, encoding="utf-8") as f:
        original = f.read()
    lines = original.split("\n")
    section, start, indent = None, None, 0
    idre = re.compile(r"""^(\s*)-\s+id:\s*["']?%s["']?\s*(#.*)?$""" % re.escape(story_id))
    for i, ln in enumerate(lines):
        mt = re.match(r"^([A-Za-z_]+):", ln)
        if mt:
            section = mt.group(1)
        if section == "stories":
            mi = idre.match(ln)
            if mi:
                start, indent = i, len(mi.group(1)) + 2
                break
    if start is None:
        raise SourceError("story '%s' not found under `stories:` (its first line must be `- id: %s`)" % (story_id, story_id))
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) >= indent):
        end += 1
    # strip trailing blank lines from the block
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1

    def upsert(key, value):
        nonlocal end
        pad = " " * indent
        new = "%s%s: %s" % (pad, key, value)
        for j in range(start + 1, end):
            if re.match(r"^%s%s:" % (re.escape(pad), key), lines[j]):
                lines[j] = new
                return
        at = start + 1
        if key != "status":  # keep `verified` right below `status`
            for j in range(start + 1, end):
                if re.match(r"^%sstatus:" % re.escape(pad), lines[j]):
                    at = j + 1
        lines.insert(at, new)
        end += 1

    upsert("status", status)
    if verified is not None:
        upsert("verified", json.dumps(verified, ensure_ascii=False))
    new_text = "\n".join(lines)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_text)
    try:
        m = load_model(src_dir)
        errs = [i for i in validate(m) if i[0] == "error"]
    except SourceError as ex:
        errs = [("error", "PARSE", str(ex))]
    if errs:
        with open(path, "w", encoding="utf-8", newline="\n") as f:  # roll back
            f.write(original)
        report(errs)
        raise SourceError("change rolled back: the result would not validate")
    print("  %s -> %s%s" % (story_id, status, ("  (verified: %s)" % verified) if verified else ""))


# --------------------------------------------------------------------------- commands
def resolve_dir(arg):
    cands = [arg] if arg else [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.getcwd(), "docs", "story-map"), os.getcwd()]
    for c in cands:
        if c and any(os.path.isfile(os.path.join(c, n)) for n in SOURCE_NAMES):
            return os.path.abspath(c)
    raise SourceError("no stories.yaml found (looked in: %s). Pass the folder: `storymap.py build docs/story-map`"
                      % ", ".join(c for c in cands if c))


def cmd_validate(a):
    d = resolve_dir(a.dir)
    m = load_model(d)
    print("Validating %s" % os.path.relpath(m["source"]))
    issues = validate(m)
    ne, nw = report(issues)
    print("  %d error(s), %d warning(s)" % (ne, nw))
    return 1 if ne or (a.strict and nw) else 0


def cmd_status(a):
    m = load_model(resolve_dir(a.dir))
    print("%s - %d stories, %d screens, %d flows" % (m["app"]["name"], len(m["stories"]), len(m["screens"]), len(m["flows"])))
    print("\nBy status:  " + "   ".join("%s %d" % (k, n) for k, n in counts(m["stories"]).items()))
    print("\nBy flow:")
    for f in m["flows"]:
        us = [u for u in m["stories"] if u["flow_eff"] == f["id"]]
        print("  %-28s %s" % (f["title"][:28], "  ".join("%s %d" % (k, n) for k, n in counts(us).items() if n) or "-"))
    print("\nBy persona:")
    for p in m["personas"]:
        us = [u for u in m["stories"] if u["persona"] == p["id"]]
        print("  %-28s %s" % (p["name"][:28], "  ".join("%s %d" % (k, n) for k, n in counts(us).items() if n) or "-"))
    return 0


def build_formats(a):
    formats = set(FORMATS) if getattr(a, "profile", "lean") == "full" else set(LEAN_FORMATS)
    only = getattr(a, "only", None)
    value = getattr(a, "formats", None)
    if only is not None:
        if value is not None:
            raise SourceError("--only cannot be combined with --formats")
        tokens = [t.strip() for t in only.split(",")]
        unknown = [t for t in tokens if t not in ONLY_FORMATS]
        if unknown:
            raise SourceError("unknown --only value: %s; valid names: %s" % (", ".join(unknown), ", ".join(ONLY_FORMATS)))
        print("note: --only is deprecated; use --formats instead")
        formats = set().union(*(ONLY_FORMATS[t] for t in tokens))
    if value is not None:
        tokens = [t.strip() for t in value.split(",")]
        modify = any(t.startswith(("+", "-")) for t in tokens)
        if not modify:
            formats = set()
        for token in tokens:
            name = token[1:] if token.startswith(("+", "-")) else token
            if name not in FORMATS:
                raise SourceError("unknown format '%s'; valid names: %s" % (name, ", ".join(FORMATS)))
            if token.startswith("-"):
                formats.discard(name)
            else:
                formats.add(name)
    return formats


def output_paths(m, formats, use_graphviz=True):
    """Known requested paths, including children so stale members can be cleaned safely."""
    paths = set()
    singles = dict(html="story-map.html", arch="architecture.png", report="REPORT.md", csv="user-stories.csv",
                   overview="overview.png", **{"flow-map": "flow-map.png", "pdf": "one-pager.pdf"})
    for key, path in singles.items():
        if key in formats:
            paths.add(path)
    if formats & {"onepager", "pdf"}:
        paths.add("one-pager.png")
    if "legacy-md" in formats:
        paths.update(("story-map.md", "user-stories.md", "gaps-and-risks.md"))
    if "flows" in formats:
        paths.update("flows/" + f["id"] + ".png" for f in m["flows"])
    if "crops" in formats:
        paths.update("architecture/" + r["topic"]["id"] + ".png" for r in topic_summary(m) if r["screens"])
    if "mermaid" in formats:
        paths.update(("mermaid/architecture.mmd", "mermaid/topics.mmd", "mermaid/00-overview.mmd"))
        paths.update("mermaid/%02d-%s.mmd" % (i, f["id"]) for i, f in enumerate(m["flows"], 1))
    dot_formats = {"arch", "flows", "overview", "flow-map"} if "dot" in formats else (
        formats & {"arch", "flows", "overview", "flow-map"} if not HAVE_PIL and use_graphviz and shutil.which("dot") else set())
    names = [name for kind, name in (("arch", "architecture"), ("overview", "overview"), ("flow-map", "flow-map")) if kind in dot_formats]
    if "flows" in dot_formats:
        names += [f["id"] for f in m["flows"]]
    paths.update("dot/" + name + ".dot" for name in names)
    return paths


def stale_outputs(gen, expected, clean=False):
    known_files = {"REPORT.md", "story-map.html", "architecture.png", "one-pager.png", "one-pager.pdf", "overview.png",
                   "flow-map.png", "story-map.md", "user-stories.md", "user-stories.csv", "gaps-and-risks.md", "README.md"}
    known_dirs = {"flows", "architecture", "mermaid", "dot", "thumbs"}
    stale = []
    for root, dirs, files in os.walk(gen, followlinks=False):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), gen).replace("\\", "/")
            if (rel in known_files or rel.split("/")[0] in known_dirs) and rel not in expected:
                stale.append(rel)
        for name in dirs[:]:
            path = os.path.join(root, name)
            if os.path.islink(path):
                dirs.remove(name)
                rel = os.path.relpath(path, gen).replace("\\", "/")
                if rel in known_dirs and not any(p.startswith(rel + "/") for p in expected):
                    stale.append(rel)
    if clean:
        for rel in stale:
            os.remove(os.path.join(gen, rel))
        for root, dirs, files in os.walk(gen, topdown=False, followlinks=False):
            if root != gen and os.path.relpath(root, gen).split(os.sep)[0] in known_dirs and not os.listdir(root):
                os.rmdir(root)
    elif stale:
        print("stale (use --clean): " + ", ".join(sorted(stale)))


def cmd_build(a):
    formats = build_formats(a)
    d = resolve_dir(a.dir)
    m = load_model(d)
    if getattr(a, "embed_fonts", False):
        TH["embed_fonts"] = m["theme"]["embed_fonts"] = True
    print("Building %s from %s" % (m["app"]["name"], os.path.relpath(m["source"])))
    ne, nw = report(validate(m), quiet_ok=True)
    if ne and not a.force:
        print("Not building: fix the %d error(s) above (or use --force)." % ne)
        return 1
    if a.strict and nw:
        print("Not building: --strict and %d warning(s)." % nw)
        return 1
    gen = os.path.join(d, "generated")
    os.makedirs(gen, exist_ok=True)
    expected = output_paths(m, formats, use_graphviz=not a.no_graphviz)
    if "legacy-md" in formats:
        gen_stories_md(m, gen)
        gen_gaps_md(m, gen)
    if "csv" in formats:
        gen_stories_csv(m, gen)
    if formats & {"mermaid", "legacy-md"}:
        gen_mermaid(m, gen, render=False, sources="mermaid" in formats, legacy="legacy-md" in formats)
    diagrams = formats & {"arch", "crops", "flows", "flow-map", "overview", "dot"}
    if diagrams:
        failed = False
        for note in gen_diagrams(m, gen, use_graphviz=not a.no_graphviz, formats=diagrams):
            print("  note  " + note)
            failed = failed or note.startswith("graphviz failed on ")
            if note.startswith("flow-map.png skipped"):
                expected.discard("flow-map.png")
        if failed:
            return 1
    if formats & {"onepager", "pdf"}:
        note = gen_onepager(m, gen, pdf="pdf" in formats)
        if note:
            print("  note  " + note)
    if "html" in formats:
        gen_html(m, gen, available=expected if getattr(a, "clean", False) else None)
    if "report" in formats:
        gen_report(m, gen, expected)
    stale_outputs(gen, expected, clean=getattr(a, "clean", False))
    print("Wrote to %s:" % os.path.relpath(gen))
    for path in sorted(expected):
        dest = os.path.join(gen, path)
        if os.path.isfile(dest):
            size = os.path.getsize(dest)
            print("  %s (%s)" % (path, ("%.1f MB" % (size / 1048576)) if size >= 1048576 else ("%.1f KB" % (size / 1024))))
    opt_in = [f for f in FORMATS if f not in formats]
    if opt_in:
        print("opt-in: %s (use --formats +name or --profile full)" % ", ".join(opt_in))
    return 0


def cmd_set_status(a):
    set_status(resolve_dir(a.dir), a.story, a.status, a.verified)
    if not a.no_build:
        return cmd_build(argparse.Namespace(dir=a.dir, force=False, strict=False, only=None, no_graphviz=False, profile="lean", formats=None, clean=False, embed_fonts=False))
    return 0


AGENTS_START = "<!-- user-story-maps:start -->"
AGENTS_END = "<!-- user-story-maps:end -->"


def agents_snippet(template_dir, rel_dir, vendored=False):
    with open(os.path.join(template_dir, "AGENTS-snippet.md"), encoding="utf-8") as f:
        snippet = f.read().strip()
    snippet = snippet.replace("docs/story-map", rel_dir)
    for command in ("validate", "build"):
        snippet = snippet.replace(command + " " + rel_dir, command + " " + shlex.quote(rel_dir))
    if vendored:
        snippet = snippet.replace("python3 <skill>/scripts/storymap.py",
                                  "python3 " + shlex.quote(rel_dir.rstrip("/") + "/storymap.py"))
        snippet = "\n".join(line for line in snippet.splitlines() if not line.startswith("`<skill>` ="))
    return snippet


def apply_agents(root, agents, snippet, rel_dir):
    if agents == "auto":
        agents = next((name for name in ("AGENTS.md", "CLAUDE.md")
                       if os.path.isfile(os.path.join(root, name))), None)
        if agents is None:
            print("Agents: skipped; no AGENTS.md or CLAUDE.md found; re-run with `--agents AGENTS.md` to create it.")
            return
    path = os.path.abspath(os.path.join(root, agents))
    label = os.path.relpath(path, root).replace(os.sep, "/")
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as f:
                old = f.read()
        else:
            old = ""
        newline = "\r\n" if "\r\n" in old else "\n"
        snippet = snippet.replace("\n", newline)
        start = old.find(AGENTS_START)
        end = old.find(AGENTS_END, start + len(AGENTS_START)) if start >= 0 else -1
        if start >= 0 and end >= 0:
            end += len(AGENTS_END)
            if old[start:end] == snippet:
                print("Agents: already up to date in %s (%s)" % (label, rel_dir))
                return
            text = old[:start] + snippet + old[end:]
            action = "updated the story-map block in"
        elif AGENTS_START in old or AGENTS_END in old:
            print("Agents: skipped %s; incomplete story-map markers; add both markers manually or remove the old block." % label)
            return
        elif re.search(r"story-map|stories\.yaml", old, re.I):
            print("Agents: skipped %s; it already mentions the story map; add the markers manually "
                  "or remove the old block to switch to the managed block." % label)
            return
        else:
            separator = "" if not old or old.endswith(newline * 2) else (newline if old.endswith(("\n", "\r")) else newline * 2)
            text = old + separator + snippet + newline
            action = "added the story-map block to"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    except (OSError, UnicodeError) as ex:
        raise SourceError("cannot update agents file %s: %s" % (label, ex))
    print("Agents: %s %s (%s)" % (action, label, rel_dir))


def cmd_init(a):
    given_dir = a.dir or os.path.join("docs", "story-map")
    d = os.path.abspath(given_dir)
    root = repo_root(d)
    rel_dir = os.path.relpath(d, root).replace(os.sep, "/")
    if rel_dir == ".." or rel_dir.startswith("../"):
        rel_dir = given_dir.replace(os.sep, "/")
    agents = getattr(a, "agents", None)
    here = os.path.dirname(os.path.abspath(__file__))
    tdir = next((p for p in (os.path.join(here, "..", "templates"), os.path.join(here, "templates")) if os.path.isdir(p)), None)
    if not tdir:
        raise SourceError("templates/ folder not found next to this script")
    existing = any(os.path.isfile(os.path.join(d, n)) for n in SOURCE_NAMES)
    if existing and agents is None:
        raise SourceError("%s already has a stories.yaml - not overwriting" % d)
    if not existing:
        os.makedirs(os.path.join(d, "screens"), exist_ok=True)
        os.makedirs(os.path.join(d, "generated"), exist_ok=True)
        for n in ("stories.yaml", "README.md"):
            shutil.copy(os.path.join(tdir, n), os.path.join(d, n))
        for sub in ("screens", "generated"):
            with open(os.path.join(d, sub, ".gitkeep"), "w"):
                pass
        ensure_gitignore(d, (".cache/", "frames.json", "frames/", ".demo-session.json", "*.storage-state.json", ".env", ".env.*"))
    if getattr(a, "vendor", False):
        shutil.copy(os.path.abspath(__file__), os.path.join(d, "storymap.py"))
        if not existing:
            readme_path = os.path.join(d, "README.md")
            with open(readme_path, encoding="utf-8") as f:
                readme = f.read()
            command = "python3 " + shlex.quote(rel_dir.rstrip("/") + "/storymap.py")
            readme = "\n".join('SM="%s"' % command if line.startswith('SM="python3 <skill>/scripts/storymap.py"') else line
                               for line in readme.splitlines()) + "\n"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme)
    print("%s %s" % ("Using existing" if existing else "Created", d))
    print("  stories.yaml   <- the ONE file you edit")
    print("  screens/       <- put real screenshots here (see the capture guide in SKILL.md)")
    print("  generated/     <- written by the build; never edit")
    if getattr(a, "vendor", False):
        print("  storymap.py    <- vendored copy of the generator")
    print("Next: edit stories.yaml, then run:  python3 %s build %s" % (shlex.quote(os.path.abspath(__file__)), shlex.quote(d)))
    if agents is not None:
        apply_agents(root, agents, agents_snippet(tdir, rel_dir, getattr(a, "vendor", False)), rel_dir)
    else:
        print("\nIMPORTANT: agents only keep the map current if the repo tells them to.")
        print("Run: python3 %s init %s --agents   (appends the block to AGENTS.md or CLAUDE.md)" %
              (shlex.quote(os.path.abspath(__file__)), shlex.quote(d)))
        print("Use --agents AGENTS.md to create the instruction file if needed.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="storymap.py", description=__doc__.split("\n")[0])
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="validate, then generate the selected formats (default: lean)")
    b.add_argument("dir", nargs="?")
    b.add_argument("--force", action="store_true", help="build even if validation has errors")
    b.add_argument("--strict", action="store_true", help="refuse to build when there are warnings")
    b.add_argument("--profile", choices=("lean", "full"), default="lean", help="output profile (default: lean)")
    b.add_argument("--formats", help="comma list replacing profile, or +name/-name to modify it")
    b.add_argument("--clean", action="store_true", help="remove known stale outputs inside generated/")
    b.add_argument("--only", help="deprecated alias: docs,mermaid,diagrams,html,pdf")
    b.add_argument("--no-graphviz", action="store_true", help="use the built-in Pillow renderer even if Graphviz exists")
    b.add_argument("--embed-fonts", action="store_true", help="embed WOFF2 subsets of theme fonts (needs fontTools and brotli)")
    v = sub.add_parser("validate", help="check the source for problems",
                       description="Check the source, including AGENTS_MISSING, long-field and repeated-text warnings (use --strict to fail on warnings).")
    v.add_argument("dir", nargs="?")
    v.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    st = sub.add_parser("status", help="print counts per status / flow / persona")
    st.add_argument("dir", nargs="?")
    ss = sub.add_parser("set-status", help="change one story's status in stories.yaml, then rebuild")
    ss.add_argument("story")
    ss.add_argument("status", choices=list(STATUS))
    ss.add_argument("--verified", help="how/when you checked it (required to mark built), e.g. 'app, 2026-10-15'")
    ss.add_argument("--dir")
    ss.add_argument("--no-build", action="store_true")
    tf = sub.add_parser("theme-from", help="scan an app's source for design tokens (colours, fonts) and print a draft theme: block")
    tf.add_argument("path", help="app source folder (read-only scan)")
    tf.add_argument("--limit", type=int, default=4000, help="max files to scan")
    i = sub.add_parser("init", help="create a story map; --agents installs or updates repo instructions",
                       description="Create a story map from the template, or update instructions for an existing map with --agents.")
    i.add_argument("dir", nargs="?")
    i.add_argument("--vendor", action="store_true", help="copy storymap.py into the new folder")
    i.add_argument("--agents", nargs="?", const="auto", metavar="FILE",
                   help="update repo AGENTS.md (or CLAUDE.md); give FILE to create it, relative to the repo root")
    i.add_argument("--no-vendor", action="store_true", help=argparse.SUPPRESS)
    argv = list(sys.argv[1:] if argv is None else argv)
    for pos in range(len(argv) - 2, -1, -1):
        if argv[pos] == "--formats" and argv[pos + 1].startswith("-") and not argv[pos + 1].startswith("--"):
            argv[pos:pos + 2] = ["--formats=" + argv[pos + 1]]
    a = ap.parse_args(argv)
    try:
        return {"build": cmd_build, "validate": cmd_validate, "status": cmd_status,
                "set-status": cmd_set_status, "init": cmd_init,
                "theme-from": lambda a: theme_from(a.path, a.limit)}[a.cmd](a)
    except SourceError as ex:
        print("error: %s" % ex, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
