"""
Convert all <div class="card"> sections inside tab-content divs to widget-card pattern.

Pattern:
- Find <div class="card"> with an <h2> or <h3> as the first text element
- Convert to widget-card with widget-header (containing the title + collapse button)
  and widget-collapsible wrapping the body
- Skip sections that are already widget-card or analyze-section (already done)
- Generate unique IDs for each collapsible div

This script reads the HTML, processes it with regex, and writes the result.
"""
import re
import sys

INPUT = r"c:\Users\nicho\OneDrive\Documents\GitHub\data-acq-functional-SophistryDude\Securities_prediction_model\frontend\index.html"

with open(INPUT, 'r', encoding='utf-8') as f:
    html = f.read()

# Counter for unique IDs
widget_counter = [0]

def make_widget_id():
    widget_counter[0] += 1
    return f"widgetCollapse{widget_counter[0]}"

# We need a more targeted approach. Instead of regex on the whole file,
# let's find specific patterns and convert them.

# Pattern: A <div class="card"> that contains an <h2>Title</h2> as its content start
# These are the simple "card" sections on tabs like Reports, Trend, Options, etc.

# The tricky part: these cards have varying internal structure.
# Rather than a full parser, let's identify each tab's card and convert manually
# by finding the specific h2 titles.

# Cards to convert (title text -> widget ID prefix):
CARDS_TO_CONVERT = [
    # Reports tab - has complex header, skip automatic conversion
    # Trend tab
    ('Predict Trend Breaks', 'trendWidget'),
    # Options tab
    ('Options Analysis', 'optionsWidget'),
    # Earnings tab
    ('Quarterly Earnings Calendar', 'earningsWidget'),
    # Trading tab
    ('Trade Execution', 'tradingWidget'),
    # Long Term tab
    ('Long Term Trading Watchlist', 'longtermWidget'),
    # Indicators tab
    ('Indicator Guide', 'indicatorsWidget'),
    # Forex tab
    ('Forex Correlations', 'forexWidget'),
    # Stats tab
    ('Model Performance Statistics', 'statsWidget'),
    # Portfolio tab
    ('Theoretical Portfolio Tracker', 'portfolioWidget'),
]

converted = 0

for title, widget_id in CARDS_TO_CONVERT:
    # Find the pattern: <div class="card">\n    <h2>Title</h2>
    # We need to match the card div, extract its h2, and wrap content

    # Pattern 1: <div class="card">\n...whitespace...<h2>Title</h2>\n...whitespace...<p class="description">desc</p>
    pattern = re.compile(
        r'(<div class="card">)\s*\n(\s*)<h2>' + re.escape(title) + r'</h2>\s*\n\s*<p class="description">(.*?)</p>',
        re.DOTALL
    )

    match = pattern.search(html)
    if match:
        indent = match.group(2)
        desc = match.group(3)
        collapse_id = widget_id + 'Body'

        replacement = f'''<div class="widget-card" id="{widget_id}">
{indent}<div class="widget-header">
{indent}    <h3 class="widget-title">{title}</h3>
{indent}    <span class="widget-subtitle">{desc}</span>
{indent}    <div class="header-spacer"></div>
{indent}    <button class="widget-collapse-btn" data-target="{collapse_id}" title="Collapse/Expand">
{indent}        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="6 9 12 15 18 9"></polyline></svg>
{indent}    </button>
{indent}</div>
{indent}<div class="widget-collapsible" id="{collapse_id}">'''

        # Also need to handle the description box that follows
        # and ensure the closing </div> for widget-collapsible is added before the card's closing </div>

        html = pattern.sub(replacement, html)
        converted += 1
        print(f"  Converted: {title}")
    else:
        # Try without description paragraph
        pattern2 = re.compile(
            r'(<div class="card">)\s*\n(\s*)<h2>' + re.escape(title) + r'</h2>',
        )
        match2 = pattern2.search(html)
        if match2:
            indent = match2.group(2)
            collapse_id = widget_id + 'Body'

            replacement = f'''<div class="widget-card" id="{widget_id}">
{indent}<div class="widget-header">
{indent}    <h3 class="widget-title">{title}</h3>
{indent}    <div class="header-spacer"></div>
{indent}    <button class="widget-collapse-btn" data-target="{collapse_id}" title="Collapse/Expand">
{indent}        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="6 9 12 15 18 9"></polyline></svg>
{indent}    </button>
{indent}</div>
{indent}<div class="widget-collapsible" id="{collapse_id}">'''

            html = pattern2.sub(replacement, html)
            converted += 1
            print(f"  Converted (no desc): {title}")
        else:
            print(f"  SKIPPED: {title} - pattern not found")

# Now we need to close the widget-collapsible divs.
# Each converted card's content ends with </div>\n    </div> (closing card, closing tab)
# We need to insert </div> before the card's closing </div>

# For each widget we converted, find the closing pattern and insert the extra </div>
for title, widget_id in CARDS_TO_CONVERT:
    collapse_id = widget_id + 'Body'
    # Check if this widget was converted
    if f'id="{collapse_id}"' in html:
        # Find the position of the collapsible div
        pos = html.find(f'id="{collapse_id}"')
        if pos == -1:
            continue

        # Now find the matching closing </div> for the widget-card
        # We need to count div nesting from the widget-card start
        widget_start = html.rfind(f'id="{widget_id}"', 0, pos)
        if widget_start == -1:
            continue

        # Find the start of the widget-card div
        card_start = html.rfind('<div', 0, widget_start)

        # Count nested divs to find the matching close
        depth = 0
        i = card_start
        found_close = -1
        while i < len(html):
            if html[i:i+4] == '<div':
                depth += 1
            elif html[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    found_close = i
                    break
            i += 1

        if found_close > 0:
            # Insert </div> (closing widget-collapsible) right before the card's closing </div>
            # Find the last </div> before found_close that closes the inner content
            # Actually, we need to insert </div> just before the final </div> of the card
            indent_guess = '                    '
            insert_text = f'\n{indent_guess}</div>'  # close widget-collapsible
            html = html[:found_close] + insert_text + html[found_close:]
            print(f"  Closed collapsible for: {title}")

print(f"\nTotal converted: {converted}")

# Also handle the Reports tab which has a different structure
# Reports uses report-header-row instead of h2
reports_pattern = r'(<div class="card">)\s*\n\s*<!-- Reports Header Row -->'
if re.search(reports_pattern, html):
    html = re.sub(
        reports_pattern,
        '<div class="widget-card" id="reportsWidget">\n                    <!-- Reports Header Row -->',
        html
    )
    print("  Converted Reports card to widget-card")

with open(INPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nDone! File updated.")
