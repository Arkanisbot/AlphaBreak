#!/bin/bash
# ============================================================================
# AlphaBreak SEO Routes Deploy
# ============================================================================
# Idempotent. Safe to re-run.
#
# Installs nginx location blocks for:
#   - Programmatic ticker pages:   /stocks/<TICKER>
#   - Comparison pages:            /compare/{tradingview,seeking-alpha,bloomberg}
#   - Blog deep links:             /blog/<slug>
#   - Static SEO files:            /sitemap.xml, /robots.txt
#
# Called by deploy-seo-routes.ps1 from a dev machine, or directly on the EC2
# box via `bash scripts/deploy-seo-routes.sh`.
# ============================================================================

set -euo pipefail

SNIPPET="/etc/nginx/snippets/alphabreak-seo.conf"
FRONTEND_ROOT="$HOME/AlphaBreak/frontend"
BACKUP_DIR="/var/backups/nginx"

# Where we write backups. NEVER put backups inside /etc/nginx/sites-enabled
# or /etc/nginx/conf.d — nginx loads every file it finds there and a backup
# with a duplicate server block crashes `nginx -t`.
sudo mkdir -p "$BACKUP_DIR"

# Proactively remove any stray .bak.* files inside sites-enabled and conf.d
# that a previous buggy version of this script may have left behind. nginx
# will try to load them and fail.
echo "-- Cleaning stray .bak.* files from nginx-scanned directories --"
for dir in /etc/nginx/sites-enabled /etc/nginx/conf.d; do
    [ -d "$dir" ] || continue
    while IFS= read -r -d '' stray; do
        echo "  evicting $stray → $BACKUP_DIR/"
        sudo mv "$stray" "$BACKUP_DIR/"
    done < <(sudo find "$dir" -maxdepth 1 -type f -name '*.bak.*' -print0 2>/dev/null)
done

# ---- 1. Auto-discover the nginx config for alphabreak.vip ------------------
discover_nginx_conf() {
    local candidates=()

    # sites-enabled symlinks — resolve to real targets so we edit the source,
    # not the link itself.
    if [ -d /etc/nginx/sites-enabled ]; then
        while IFS= read -r -d '' f; do
            candidates+=("$(readlink -f "$f")")
        done < <(find /etc/nginx/sites-enabled -maxdepth 1 -type l -print0 2>/dev/null)
        while IFS= read -r -d '' f; do
            candidates+=("$f")
        done < <(find /etc/nginx/sites-enabled -maxdepth 1 -type f -print0 2>/dev/null)
    fi
    if [ -d /etc/nginx/conf.d ]; then
        while IFS= read -r -d '' f; do
            candidates+=("$f")
        done < <(find /etc/nginx/conf.d -maxdepth 1 -type f -name '*.conf' -print0 2>/dev/null)
    fi
    candidates+=("/etc/nginx/nginx.conf")

    # Dedupe and prefer files whose server_name is exactly alphabreak.vip over
    # subdomain configs like poker.alphabreak.vip. First pass: exact match.
    for f in "${candidates[@]}"; do
        [ -f "$f" ] || continue
        if sudo grep -qE 'server_name[[:space:]]+[^;]*\balphabreak\.vip\b' "$f" 2>/dev/null; then
            # Skip files that ONLY have subdomain matches
            if ! sudo grep -qE 'server_name[[:space:]]+[^;]*\b(poker|api|mail|admin)\.alphabreak\.vip' "$f" 2>/dev/null; then
                echo "$f"
                return 0
            fi
            # File has the right domain alongside subdomains — still use it
            if sudo grep -qE 'server_name[[:space:]]+[^;]*(^|\s|,)alphabreak\.vip(\s|,|;)' "$f" 2>/dev/null; then
                echo "$f"
                return 0
            fi
        fi
    done

    # Second pass: any file mentioning alphabreak as a fallback
    for f in "${candidates[@]}"; do
        [ -f "$f" ] || continue
        if sudo grep -qE 'server_name[^;]*alphabreak' "$f" 2>/dev/null; then
            echo "$f"
            return 0
        fi
    done
    return 1
}

NGINX_CONF="$(discover_nginx_conf || true)"
if [ -z "${NGINX_CONF:-}" ]; then
    echo "ERROR: could not auto-discover the nginx config for alphabreak.vip."
    echo ""
    echo "Run this on the box to find it manually:"
    echo "  sudo grep -rl 'alphabreak' /etc/nginx/"
    echo ""
    echo "Then pass --conf <path> or edit this script directly."
    exit 1
fi
echo "  using nginx config: $NGINX_CONF"

# Sanity check: ensure this file contains a server block that serves the
# primary alphabreak.vip domain, not just a subdomain.
if ! sudo grep -qE 'server_name[^;]*(^|[^.])alphabreak\.vip' "$NGINX_CONF"; then
    echo ""
    echo "WARNING: the auto-discovered file ($NGINX_CONF) does not appear to"
    echo "contain a server block for the primary alphabreak.vip domain."
    echo "It may be for a subdomain. The include will still be added to the"
    echo "last server block in the file, which may not be what you want."
    echo ""
    echo "To override, edit NGINX_CONF in this script or pass --conf."
    echo ""
fi

# ---- 2. Write the nginx snippet --------------------------------------------
echo ""
echo "-- Writing nginx snippet at $SNIPPET --"
sudo mkdir -p /etc/nginx/snippets
sudo tee "$SNIPPET" >/dev/null <<NGINX_SNIPPET
# AlphaBreak SEO routes — managed by scripts/deploy-seo-routes.sh
# DO NOT EDIT BY HAND; edits are overwritten on the next deploy.

# Programmatic ticker pages: /stocks/<TICKER>
location ~ ^/stocks/[A-Za-z0-9\-\.]+/?\$ {
    try_files \$uri /index.html;
    add_header Cache-Control "no-cache, must-revalidate" always;
}

# Competitive comparison pages
location ~ ^/compare/(tradingview|seeking-alpha|bloomberg)/?\$ {
    try_files \$uri /index.html;
    add_header Cache-Control "no-cache, must-revalidate" always;
}

# Blog article deep links
location ~ ^/blog/[a-z0-9\-_]+/?\$ {
    try_files \$uri /blog-viewer.html;
}

# Static SEO files at the root
location = /sitemap.xml { root $FRONTEND_ROOT; }
location = /robots.txt  { root $FRONTEND_ROOT; }
NGINX_SNIPPET

# ---- 3a. Clean up stray includes from non-target nginx files ---------------
# An earlier version of this script could auto-discover the wrong file (e.g.
# a subdomain config) and inject the include there. We proactively remove the
# include line from any nginx config file that isn't our target, so re-runs
# converge on a clean state.
echo ""
echo "-- Scanning for stray includes in other nginx files --"
STRAY_FILES=$(sudo grep -rlE '^\s*include\s+/etc/nginx/snippets/alphabreak-seo\.conf' /etc/nginx 2>/dev/null || true)
for f in $STRAY_FILES; do
    # Skip if this is our target file — we WANT the include there.
    if [ "$f" = "$NGINX_CONF" ]; then
        continue
    fi
    # Also skip the snippet file itself (shouldn't reference itself anyway).
    if [ "$f" = "$SNIPPET" ]; then
        continue
    fi
    echo "  removing stray include from $f"
    STRAY_BACKUP="$BACKUP_DIR/$(basename "$f").bak.$(date +%Y%m%d_%H%M%S)"
    sudo cp "$f" "$STRAY_BACKUP"
    sudo sed -i '/include[[:space:]]\+\/etc\/nginx\/snippets\/alphabreak-seo\.conf/d' "$f"
done

# ---- 3b. Inject include directive into the target file --------------------
echo ""
echo "-- Injecting include directive into $NGINX_CONF --"

if sudo grep -q "snippets/alphabreak-seo.conf" "$NGINX_CONF"; then
    echo "  include already present; skipping injection"
else
    BACKUP="$BACKUP_DIR/$(basename "$NGINX_CONF").bak.$(date +%Y%m%d_%H%M%S)"
    echo "  backing up to $BACKUP"
    sudo cp "$NGINX_CONF" "$BACKUP"

    # Find the server block whose server_name matches the primary domain and
    # inject right before its closing brace. We use Python for safe brace
    # matching; sed is too fragile with nested braces.
    sudo python3 - "$NGINX_CONF" <<'PYEOF'
import re
import sys

path = sys.argv[1]
with open(path, 'r') as f:
    s = f.read()

# Find all server blocks and pick the one whose server_name contains
# alphabreak.vip as a top-level domain (not a subdomain prefix).
server_positions = [m.start() for m in re.finditer(r'\bserver\s*\{', s)]
if not server_positions:
    print('ERROR: no "server {" block found in ' + path, file=sys.stderr)
    sys.exit(1)

def match_close(text, start):
    depth = 0
    i = text.index('{', start)
    while i < len(text):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

chosen_close = -1
for pos in server_positions:
    close_pos = match_close(s, pos)
    if close_pos < 0:
        continue
    block = s[pos:close_pos]
    # Match 'alphabreak.vip' but NOT preceded by another domain segment
    if re.search(r'server_name[^;]*(^|\s|,)alphabreak\.vip(\s|,|;|$)', block):
        chosen_close = close_pos
        break

if chosen_close < 0:
    # Fall back to the last server block
    last_pos = server_positions[-1]
    chosen_close = match_close(s, last_pos)
    if chosen_close < 0:
        print('ERROR: unmatched braces', file=sys.stderr)
        sys.exit(1)
    print('  WARNING: no server block matched alphabreak.vip exactly;')
    print('  injecting into the last server block.')

inject = '\n    include /etc/nginx/snippets/alphabreak-seo.conf;\n'
new_s = s[:chosen_close] + inject + s[chosen_close:]
with open(path, 'w') as f:
    f.write(new_s)
print('  include directive injected')
PYEOF
fi

# ---- 4. Validate + reload --------------------------------------------------
echo ""
echo "-- Testing nginx config --"
sudo nginx -t

echo ""
echo "-- Reloading nginx --"
sudo systemctl reload nginx

# ---- 5. Smoke tests --------------------------------------------------------
echo ""
echo "-- HTTP smoke tests --"
URLS=(
    "https://alphabreak.vip/"
    "https://alphabreak.vip/robots.txt"
    "https://alphabreak.vip/sitemap.xml"
    "https://alphabreak.vip/stocks/AAPL"
    "https://alphabreak.vip/stocks/NVDA"
    "https://alphabreak.vip/stocks/TSLA"
    "https://alphabreak.vip/compare/tradingview"
    "https://alphabreak.vip/compare/seeking-alpha"
    "https://alphabreak.vip/compare/bloomberg"
    "https://alphabreak.vip/blog/01-why-most-new-traders-lose-money"
)
ANY_FAIL=0
for url in "${URLS[@]}"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || echo "ERR")
    status="OK"
    if [ "$code" != "200" ] && [ "$code" != "301" ] && [ "$code" != "302" ]; then
        status="FAIL"
        ANY_FAIL=1
    fi
    printf "  %-4s %s  %s\n" "$code" "$status" "$url"
done

echo ""
if [ "$ANY_FAIL" -eq 0 ]; then
    echo "== All smoke tests passed =="
    exit 0
else
    echo "== Some smoke tests failed — see above =="
    exit 2
fi
