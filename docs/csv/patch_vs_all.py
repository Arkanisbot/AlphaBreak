"""Patch build_vs_all_competitors.py to use updated AlphaBreak tiers."""
import re

# Read file
path = r"c:\Users\nicho\OneDrive\Documents\GitHub\data-acq-functional-SophistryDude\Securities_prediction_model\docs\csv\build_vs_all_competitors.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Tier changes: feature substring -> new tier
# We look for patterns like: ("Feature name", "comp_status", "OLD_TIER", "verdict")
# and replace OLD_TIER with new tier

CHANGES = {
    # Charting changes
    "Drawing tools":              "Pro",
    "Auto-detected trendlines":   "Pro",
    "Auto Fibonacci levels":      "No",
    # Options changes
    "Greeks":                     "Elite",  # covers "Greeks (Delta..." and "Options chain + Greeks"
    "Fair value":                 "Pro",
    "Probability of profit":      "Pro",
    "Market Maker Move":          "Pro",
    # AI changes
    "News NLP sentiment":         "Pro",
    # Data changes
    "Real-time data":             "Pro",
    "WebSocket streaming":        "Pro",
    "Dark pool data":             "Pro",
}

# For each feature, find all 4-tuple patterns and replace the AB tier (3rd element)
# Pattern: ("Feature...", "comp_status", "ab_status", "verdict")
# We need to be careful: the ab_status is the 3rd quoted string in the tuple

lines = content.split("\n")
patched = 0
new_lines = []

for line in lines:
    original = line
    for feat_substr, new_tier in CHANGES.items():
        # Match lines that contain the feature name in a tuple definition
        # These look like: ("Feature name", "comp_status", "ab_status", "verdict"),
        if feat_substr in line and '("' in line:
            # Extract the tuple parts
            # Find pattern: ("...", "...", "OLD", "...")
            m = re.match(r'^(\s*\(".*?",\s*".*?",\s*)"(.*?)"(,\s*".*?"\),?)$', line)
            if m:
                prefix = m.group(1)
                old_tier = m.group(2)
                suffix = m.group(3)
                # Only change if it's different and looks like a tier
                if old_tier != new_tier and old_tier in ("Free", "Pro", "Elite", "Planned", "No"):
                    line = f'{prefix}"{new_tier}"{suffix}'
                    patched += 1
                    # Also update verdict if needed
                    if new_tier == "No" and "ADVANTAGE: AlphaBreak" in line:
                        line = line.replace("ADVANTAGE: AlphaBreak", "Neither offers")

    new_lines.append(line)

content = "\n".join(new_lines)

# Special cases: "Options chain + Greeks" should stay Free (chain is free, Greeks separate)
# Actually the feature in vs-all is "Options chain + Greeks" as one line - need to handle
# Let's fix: Greeks line that says "Options chain" should stay as-is, only pure Greeks lines change
# The "Options chain + Greeks" is a combined feature - let's check what happened

# Fix: revert "Options chain + Greeks" back - it should stay Free (chain is free)
# The Greeks-only line doesn't exist in vs-all, it's always "Options chain + Greeks"
# User said Options chain = Free but Greeks = Elite. In vs-all they're combined.
# Keep as Free since the chain itself is free - Greeks are the Elite add-on
lines2 = content.split("\n")
new_lines2 = []
for line in lines2:
    if "Options chain + Greeks" in line and '"Elite"' in line:
        # This combined feature should stay Free
        line = line.replace('"Elite"', '"Free"', 1)
    # Also "Options chain" alone should be Free
    if re.search(r'\("Options chain"\s*,', line) and '"Elite"' in line:
        line = line.replace('"Elite"', '"Free"', 1)
    new_lines2.append(line)
content = "\n".join(new_lines2)

# Also need to handle verdict updates for changed tiers
# Drawing tools was "Planned" -> "Pro": update verdicts
content = content.replace(
    '("Drawing tools",                   "Yes", "Pro",     "Bloomberg has full suite")',
    '("Drawing tools",                   "Yes", "Pro",     "Parity at Pro tier")'
)
content = content.replace(
    '("Drawing tools",                   "Yes", "Pro",     "ADVANTAGE: thinkorswim")',
    '("Drawing tools",                   "Yes", "Pro",     "Parity at Pro tier")'
)
content = content.replace(
    '("Drawing tools",                   "Yes", "Pro",     "ADVANTAGE: Barchart")',
    '("Drawing tools",                   "Yes", "Pro",     "Parity at Pro tier")'
)
content = content.replace(
    '("Drawing tools",                   "Yes", "Pro",     "ADVANTAGE: TrendSpider")',
    '("Drawing tools",                   "Yes", "Pro",     "Parity at Pro tier")'
)
# Drawing tools for platforms that don't have them
content = content.replace(
    '("Drawing tools",                   "No",    "Pro",     "ADVANTAGE: AlphaBreak (planned)")',
    '("Drawing tools",                   "No",    "Pro",     "ADVANTAGE: AlphaBreak")'
)

# Auto Fib -> No: update verdicts
content = content.replace('"Auto Fibonacci levels",           "No",  "No",      "ADVANTAGE: AlphaBreak"',
                          '"Auto Fibonacci levels",           "No",  "No",      "Neither offers"')
content = content.replace('"Auto Fibonacci levels",           "No",    "No",   "ADVANTAGE: AlphaBreak"',
                          '"Auto Fibonacci levels",           "No",    "No",   "Neither offers"')

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Patched {patched} tier values in build_vs_all_competitors.py")
