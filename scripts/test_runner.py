#!/usr/bin/env python3
"""
Test runner interactif pour TESTS_MANUELS.md.

Usage :
    python scripts/test_runner.py                     # tests en attente
    python scripts/test_runner.py --module "Auth"     # filtrer par module
    python scripts/test_runner.py --test T44          # un test précis
    python scripts/test_runner.py --failed            # re-tester les échecs
    python scripts/test_runner.py --all               # tout re-tester
    python scripts/test_runner.py --status            # progression globale
    python scripts/test_runner.py --report            # générer rapport HTML+MD
    python scripts/test_runner.py --reset             # remettre tout en pending
"""

import argparse
import sqlite3
import re
import sys
from pathlib import Path
from datetime import datetime

# ── Chemins ───────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).resolve().parent.parent
MD_FILE     = BASE_DIR / "TESTS_MANUELS.md"
DB_FILE     = BASE_DIR / "test_results.sqlite3"
REPORT_DIR  = BASE_DIR / "test_reports"

# ── ANSI ─────────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    GRAY   = "\033[90m"

def g(t):    return f"{C.GREEN}{t}{C.RESET}"
def r(t):    return f"{C.RED}{t}{C.RESET}"
def y(t):    return f"{C.YELLOW}{t}{C.RESET}"
def b(t):    return f"{C.BLUE}{t}{C.RESET}"
def c(t):    return f"{C.CYAN}{t}{C.RESET}"
def gr(t):   return f"{C.GRAY}{t}{C.RESET}"
def bold(t): return f"{C.BOLD}{t}{C.RESET}"

STATUS_ICON = {
    'pending': '⏳', 'passed': '✅', 'failed': '❌',
    'skipped': '⏭ ', 'blocked': '🔒',
}

# ── Parser Markdown ───────────────────────────────────────────────────────────

def parse_tests(md_path: Path) -> list[dict]:
    """Extrait les cas de test de TESTS_MANUELS.md."""
    tests = []
    current_module = ""
    current_sub    = ""

    module_re = re.compile(r'^## (\d+\..+)')
    sub_re    = re.compile(r'^### (\d+\.\d+.+)')
    row_re    = re.compile(r'^\|\s*(T\d+)\s*\|(.+?)\|(.+?)\|')

    with md_path.open(encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            m = module_re.match(line)
            if m:
                current_module = m.group(1).strip()
                continue
            m = sub_re.match(line)
            if m:
                current_sub = m.group(1).strip()
                continue
            m = row_re.match(line)
            if m:
                tests.append({
                    'test_id':    m.group(1).strip(),
                    'module':     current_module,
                    'subsection': current_sub,
                    'action':     m.group(2).strip(),
                    'expected':   m.group(3).strip(),
                })
    return tests

# ── Base de données ───────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(tests: list[dict]):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            test_id    TEXT PRIMARY KEY,
            module     TEXT,
            subsection TEXT,
            action     TEXT,
            expected   TEXT,
            status     TEXT DEFAULT 'pending',
            note       TEXT DEFAULT '',
            updated_at TEXT,
            session_id TEXT
        )
    """)
    # Insérer les nouveaux tests sans écraser les résultats existants
    for t in tests:
        cur.execute("""
            INSERT OR IGNORE INTO tests (test_id, module, subsection, action, expected)
            VALUES (?, ?, ?, ?, ?)
        """, (t['test_id'], t['module'], t['subsection'], t['action'], t['expected']))
    conn.commit()
    conn.close()

def get_tests(status_filter=None, module_filter=None) -> list[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    q, params = "SELECT * FROM tests", []
    conds = []
    if status_filter:
        conds.append("status = ?"); params.append(status_filter)
    if module_filter:
        conds.append("module LIKE ?"); params.append(f"%{module_filter}%")
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY CAST(SUBSTR(test_id, 2) AS INTEGER)"
    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def update_test(test_id, status, note, session_id):
    conn = get_db()
    conn.execute("""
        UPDATE tests SET status=?, note=?, updated_at=?, session_id=?
        WHERE test_id=?
    """, (status, note, datetime.now().isoformat(), session_id, test_id))
    conn.commit()
    conn.close()

def get_stats() -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) as cnt FROM tests GROUP BY status")
    rows = cur.fetchall()
    conn.close()
    return {row['status']: row['cnt'] for row in rows}

def get_module_stats() -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT module, status, COUNT(*) as cnt
        FROM tests GROUP BY module, status ORDER BY module
    """)
    result: dict = {}
    for row in cur.fetchall():
        result.setdefault(row['module'], {})[row['status']] = row['cnt']
    conn.close()
    return result

# ── Session interactive ───────────────────────────────────────────────────────

def prompt_status() -> str | None:
    choices = f"[{g('P')}assé/{r('F')}ailli/{gr('S')}kipé/{y('B')}loqué/{c('?')}aide/q]"
    while True:
        raw = input(f"  {bold('Résultat')} {choices} : ").strip().lower()
        if raw in ('p', 'passe', 'passed'):  return 'passed'
        if raw in ('f', 'fail',  'failed'):  return 'failed'
        if raw in ('s', 'skip',  'skipped'): return 'skipped'
        if raw in ('b', 'block', 'blocked'): return 'blocked'
        if raw == 'q': return None
        if raw == '?':
            print(f"    {g('P')}  — test réussi, résultat conforme")
            print(f"    {r('F')}  — bug trouvé (vous noterez la description)")
            print(f"    {gr('S')}  — ignoré / hors scope / non applicable")
            print(f"    {y('B')}  — bloqué par dépendance manquante (Redis, email…)")
            print(f"    q  — quitter et sauvegarder la session")
        else:
            print(f"  {r('Invalide.')} Tapez P, F, S, B, ? ou q.")

def run_session(rows: list[sqlite3.Row], session_id: str):
    total = len(rows)
    done  = 0
    print(f"\n{c('═' * 62)}")
    print(f"  {bold(session_id)}  ·  {bold(str(total))} tests à exécuter")
    print(f"  Tapez {bold('q')} pour quitter et sauvegarder à tout moment")
    print(f"{c('═' * 62)}\n")

    for i, test in enumerate(rows, 1):
        tid = test['test_id']
        print(f"{bold(b(f'[{tid}]'))} ({i}/{total})")
        print(f"  {bold('Module   :')} {gr(test['module'])}")
        print(f"  {bold('Section  :')} {gr(test['subsection'])}")
        print(f"  {bold('Action   :')} {test['action']}")
        print(f"  {bold('Attendu  :')} {test['expected']}")
        if test['note']:
            print(f"  {bold('Note préc:')} {y(test['note'])}")
        print()

        status = prompt_status()
        if status is None:
            print(f"\n{y('Session interrompue — résultats sauvegardés.')}")
            break

        note = ""
        if status == 'failed':
            note = input(f"  {bold('Description du bug')} (Entrée pour ignorer) : ").strip()

        update_test(test['test_id'], status, note, session_id)
        done += 1
        print(f"  {STATUS_ICON.get(status, '')} Sauvegardé.\n")

    print(f"\n{'─' * 40}")
    print(f"Session terminée — {bold(str(done))}/{total} tests effectués.")
    print_stats()

# ── Affichage progression ─────────────────────────────────────────────────────

def print_stats():
    st      = get_stats()
    total   = sum(st.values())
    passed  = st.get('passed',  0)
    failed  = st.get('failed',  0)
    skipped = st.get('skipped', 0)
    blocked = st.get('blocked', 0)
    pending = st.get('pending', 0)
    tested  = passed + failed + skipped + blocked
    pct     = int(tested / total * 100) if total else 0

    bar_len = 40
    filled  = int(bar_len * tested / total) if total else 0
    bar     = g('█' * filled) + gr('░' * (bar_len - filled))

    print(f"\n{bold('Progression globale')}")
    print(f"  [{bar}] {bold(f'{pct}%')} ({tested}/{total})")
    print(f"  {g('✅ Passés')}    : {bold(str(passed))}")
    print(f"  {r('❌ Échoués')}   : {bold(str(failed))}")
    print(f"  {gr('⏭  Ignorés')}  : {bold(str(skipped))}")
    print(f"  {y('🔒 Bloqués')}   : {bold(str(blocked))}")
    print(f"  {y('⏳ En attente')}: {bold(str(pending))}")

def print_module_stats():
    ms = get_module_stats()
    print(f"\n{bold('Par module')}\n")
    print(f"{'Module':<46} {'✅':>5} {'❌':>5} {'⏭ ':>5} {'🔒':>5} {'⏳':>5}")
    print('─' * 72)
    for module, s in ms.items():
        p = s.get('passed',  0)
        f = s.get('failed',  0)
        sk= s.get('skipped', 0)
        bl= s.get('blocked', 0)
        n = s.get('pending', 0)
        fail_col = r(f'{f:>5}') if f else f'{f:>5}'
        print(f"{module[:45]:<46} {g(f'{p:>5}')} {fail_col} {f'{sk:>5}'} {f'{bl:>5}'} {gr(f'{n:>5}')}")

# ── Rapport HTML ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rapport tests — ma_chorale — {date}</title>
<style>
:root{{--green:#22c55e;--red:#ef4444;--yellow:#f59e0b;--blue:#3b82f6;
      --bg:#0f172a;--surface:#1e293b;--border:#334155;--text:#f1f5f9;--muted:#94a3b8}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);padding:2rem;font-size:14px}}
h1{{font-size:1.6rem;margin-bottom:.4rem}}
h2{{font-size:.85rem;margin:2rem 0 1rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
.meta{{color:var(--muted);font-size:.85rem;margin-bottom:1.5rem}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:.8rem;margin-bottom:1.5rem}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:.9rem;text-align:center}}
.kpi .v{{font-size:2rem;font-weight:700}}.kpi .l{{font-size:.72rem;color:var(--muted);margin-top:.15rem}}
.kpi.kp .v{{color:var(--green)}}.kpi.kf .v{{color:var(--red)}}.kpi.kn .v{{color:var(--yellow)}}.kpi.kt .v{{color:var(--blue)}}
.pbar{{background:var(--surface);border-radius:999px;height:10px;margin-bottom:1.5rem;border:1px solid var(--border);overflow:hidden}}
.pfill{{height:100%;background:linear-gradient(90deg,var(--green),#16a34a);border-radius:999px}}
table{{width:100%;border-collapse:collapse;background:var(--surface);border-radius:10px;overflow:hidden;border:1px solid var(--border);margin-bottom:1.5rem}}
th{{background:#0f172a;padding:.55rem .75rem;text-align:left;font-size:.72rem;text-transform:uppercase;color:var(--muted);letter-spacing:.06em}}
td{{padding:.5rem .75rem;border-bottom:1px solid var(--border);vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover{{background:rgba(255,255,255,.02)}}
.tid{{font-family:monospace;font-weight:600;color:var(--blue);white-space:nowrap}}
.mod{{font-size:.72rem;color:var(--muted)}}
.badge{{display:inline-block;padding:.18rem .45rem;border-radius:5px;font-size:.72rem;font-weight:600;white-space:nowrap}}
.sp .badge{{background:rgba(34,197,94,.2);color:var(--green)}}
.sf .badge{{background:rgba(239,68,68,.2);color:var(--red)}}
.sn .badge{{background:rgba(245,158,11,.2);color:var(--yellow)}}
.ss .badge{{background:rgba(107,114,128,.2);color:#9ca3af}}
.sb .badge{{background:rgba(245,158,11,.15);color:var(--yellow)}}
.sf{{background:rgba(239,68,68,.06)}}
.bug{{display:block;margin-top:.25rem;font-size:.78rem;color:var(--red);font-style:italic}}
.fbar{{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.8rem}}
.fb{{padding:.25rem .7rem;border:1px solid var(--border);border-radius:999px;background:var(--surface);
     color:var(--text);cursor:pointer;font-size:.78rem;transition:all .15s}}
.fb:hover,.fb.on{{background:var(--blue);border-color:var(--blue)}}
.pass{{color:var(--green)}}.fail{{color:var(--red)}}.pend{{color:var(--yellow)}}
@media(max-width:640px){{.mod{{display:none}}}}
</style>
</head>
<body>
<h1>📋 Rapport de tests — ma_chorale</h1>
<p class="meta">Généré le {date_long} · {tested}/{total} exécutés ({pct}%)</p>
<div class="kpis">
  <div class="kpi kt"><div class="v">{total}</div><div class="l">Total</div></div>
  <div class="kpi kp"><div class="v">{passed}</div><div class="l">✅ Passés</div></div>
  <div class="kpi kf"><div class="v">{failed}</div><div class="l">❌ Échoués</div></div>
  <div class="kpi kn"><div class="v">{pending}</div><div class="l">⏳ En attente</div></div>
</div>
<div class="pbar"><div class="pfill" style="width:{pct}%"></div></div>

<h2>Par module</h2>
<table>
<thead><tr><th>Module</th><th>✅</th><th>❌</th><th>⏭ </th><th>🔒</th><th>⏳</th></tr></thead>
<tbody>{module_rows}</tbody>
</table>

<h2>Détail</h2>
<div class="fbar">
  <button class="fb on" onclick="filt('all',this)">Tous</button>
  <button class="fb"    onclick="filt('sf',this)">❌ Échoués</button>
  <button class="fb"    onclick="filt('sn',this)">⏳ En attente</button>
  <button class="fb"    onclick="filt('sp',this)">✅ Passés</button>
  <button class="fb"    onclick="filt('ss',this)">⏭  Ignorés</button>
</div>
<table id="tbl">
<thead><tr><th>ID</th><th>Module</th><th>Action</th><th>Attendu</th><th>Statut</th></tr></thead>
<tbody>{test_rows}</tbody>
</table>
<script>
function filt(cls,btn){{
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('#tbl tbody tr').forEach(tr=>{{
    tr.style.display=(cls==='all'||tr.classList.contains(cls))?'':'none';
  }});
}}
</script>
</body></html>"""

STATUS_CSS   = {'passed':'sp','failed':'sf','pending':'sn','skipped':'ss','blocked':'sb'}
STATUS_LABEL = {'passed':'✅ Passé','failed':'❌ Échoué','pending':'⏳ En attente',
                'skipped':'⏭  Ignoré','blocked':'🔒 Bloqué'}

def generate_html_report() -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M')
    path  = REPORT_DIR / f"test_report_{stamp}.html"

    all_tests = get_tests()
    st        = get_stats()
    ms        = get_module_stats()
    total     = sum(st.values())
    passed    = st.get('passed',  0)
    failed    = st.get('failed',  0)
    skipped   = st.get('skipped', 0)
    blocked   = st.get('blocked', 0)
    pending   = st.get('pending', 0)
    tested    = passed + failed + skipped + blocked
    pct       = int(tested / total * 100) if total else 0

    # Lignes tableau module
    mrows = ""
    for module, s in ms.items():
        p  = s.get('passed',  0)
        f  = s.get('failed',  0)
        sk = s.get('skipped', 0)
        bl = s.get('blocked', 0)
        n  = s.get('pending', 0)
        fc = f'<td class="fail">{f}</td>' if f else f'<td>{f}</td>'
        mrows += f"<tr><td>{module}</td><td class='pass'>{p}</td>{fc}<td>{sk}</td><td>{bl}</td><td class='pend'>{n}</td></tr>\n"

    # Lignes tableau tests
    trows = ""
    for t in all_tests:
        css   = STATUS_CSS.get(t['status'],  'sn')
        label = STATUS_LABEL.get(t['status'], t['status'])
        bug   = f'<span class="bug">🐛 {t["note"]}</span>' if t['note'] else ''
        trows += (
            f'<tr class="{css}">'
            f'<td class="tid">{t["test_id"]}</td>'
            f'<td class="mod">{t["module"][:35]}</td>'
            f'<td>{t["action"]}</td>'
            f'<td>{t["expected"]}</td>'
            f'<td><span class="badge">{label}</span>{bug}</td>'
            f'</tr>\n'
        )

    html = HTML_TEMPLATE.format(
        date      = stamp,
        date_long = datetime.now().strftime('%d/%m/%Y à %H:%M'),
        total=total, passed=passed, failed=failed,
        pending=pending, tested=tested, pct=pct,
        module_rows=mrows, test_rows=trows,
    )
    path.write_text(html, encoding='utf-8')
    return path

def generate_md_summary() -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M')
    path  = REPORT_DIR / f"summary_{stamp}.md"

    st     = get_stats()
    total  = sum(st.values())
    passed = st.get('passed',  0)
    failed = st.get('failed',  0)
    skip   = st.get('skipped', 0)
    block  = st.get('blocked', 0)
    pend   = st.get('pending', 0)
    tested = passed + failed + skip + block
    pct    = int(tested / total * 100) if total else 0

    lines = [
        f"# Résultats tests manuels — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        f"**{tested}/{total}** tests exécutés ({pct}%)",
        "",
        "| Statut | Nb |",
        "|--------|---:|",
        f"| ✅ Passés     | {passed} |",
        f"| ❌ Échoués    | {failed} |",
        f"| ⏭  Ignorés   | {skip}   |",
        f"| 🔒 Bloqués    | {block}  |",
        f"| ⏳ En attente | {pend}   |",
        "",
    ]

    failed_tests = get_tests(status_filter='failed')
    if failed_tests:
        lines += ["## ❌ Tests échoués", ""]
        for t in failed_tests:
            lines.append(f"- **{t['test_id']}** — {t['action']}")
            if t['note']:
                lines.append(f"  > 🐛 {t['note']}")
        lines.append("")

    blocked_tests = get_tests(status_filter='blocked')
    if blocked_tests:
        lines += ["## 🔒 Tests bloqués", ""]
        for t in blocked_tests:
            lines.append(f"- **{t['test_id']}** — {t['action']}")
            if t['note']:
                lines.append(f"  > {t['note']}")
        lines.append("")

    path.write_text("\n".join(lines), encoding='utf-8')
    return path

# ── Entrée principale ─────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Test runner interactif — ma_chorale",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('--module',  help='Filtrer par module (partiel, ex: "Auth")')
    ap.add_argument('--test',    help='Un test précis (ex: T44)')
    ap.add_argument('--failed',  action='store_true', help='Re-tester les tests échoués')
    ap.add_argument('--all',     action='store_true', help='Tout tester (y compris déjà passés)')
    ap.add_argument('--report',  action='store_true', help='Générer rapport HTML + MD uniquement')
    ap.add_argument('--status',  action='store_true', help='Afficher la progression')
    ap.add_argument('--reset',   action='store_true', help='Remettre tous les tests en pending')
    args = ap.parse_args()

    if not MD_FILE.exists():
        print(r(f"Fichier introuvable : {MD_FILE}"))
        sys.exit(1)

    parsed = parse_tests(MD_FILE)
    if not parsed:
        print(r("Aucun test trouvé dans TESTS_MANUELS.md — vérifier le format des tableaux."))
        sys.exit(1)

    init_db(parsed)

    # ── reset ──
    if args.reset:
        confirm = input(f"{r('⚠  Remettre TOUS les tests en pending ?')} (oui/non) : ").strip()
        if confirm.lower() == 'oui':
            conn = get_db()
            conn.execute("UPDATE tests SET status='pending', note='', updated_at=NULL, session_id=NULL")
            conn.commit()
            conn.close()
            print(g(f"✅ {len(parsed)} tests remis en attente."))
        return

    # ── status ──
    if args.status:
        print_stats()
        print_module_stats()
        return

    # ── report ──
    if args.report:
        hp = generate_html_report()
        mp = generate_md_summary()
        print(g(f"✅ HTML → {hp}"))
        print(g(f"✅ MD   → {mp}"))
        return

    # ── sélection des tests à exécuter ──
    if args.test:
        rows = [t for t in get_tests() if t['test_id'] == args.test.upper()]
        if not rows:
            print(r(f"Test '{args.test}' introuvable."))
            sys.exit(1)
    elif args.failed:
        rows = get_tests(status_filter='failed', module_filter=args.module)
    elif args.all:
        rows = get_tests(module_filter=args.module)
    else:
        # défaut : tests en attente uniquement
        rows = get_tests(status_filter='pending', module_filter=args.module)

    if not rows:
        print(y("Aucun test à exécuter avec ces filtres."))
        print_stats()
        return

    session_id = datetime.now().strftime('session_%Y%m%d_%H%M%S')
    run_session(rows, session_id)

    print()
    if input("Générer un rapport HTML ? (o/N) : ").strip().lower() == 'o':
        hp = generate_html_report()
        mp = generate_md_summary()
        print(g(f"✅ HTML → {hp}"))
        print(g(f"✅ MD   → {mp}"))

if __name__ == '__main__':
    main()
