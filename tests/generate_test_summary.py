import json


def load_report(path="report.json"):
    with open(path, "r") as f:
        return json.load(f)


def format_outcome(status):
    return {
        "passed": "✅",
        "failed": "❌",
        "error": "❌",
        "skipped": "⏭️"
    }.get(status, status)


def get_duration(test):
    duration = 0
    for step in ("setup", "call", "teardown"):
        duration += test.get(step, {}).get("duration", 0)
    return duration


def get_html_header():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #2980b9; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }
        h3 { color: #3498db; margin-top: 25px; }
        h4 { color: #3498db; margin-top: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .passed { color: #27ae60; font-weight: bold; }
        .failed { color: #e74c3c; font-weight: bold; }
        .skipped { color: #f39c12; font-weight: bold; }
        .test-name { font-family: monospace; }
        .number { width: 3%; text-align: center; }
        .name { width: 77%; }
        .outcome { width: 10%; text-align: center; }
        .duration { width: 10%; text-align: center; }
    </style>
</head>
<body>
    <h1>Test Report</h1>
"""


def get_html_footer():
    return """
</body>
</html>
"""


def format_outcome(outcome):
    outcome_classes = {
        'passed': 'passed',
        'failed': 'failed',
        'skipped': 'skipped',
        'error': 'failed'
    }
    return f'<span class="{outcome_classes.get(outcome, "")}">{outcome.upper()}</span>'


def write_test_table(file, tests, total):
    file.write('<table>\n')
    file.write('    <thead>\n')
    file.write('        <tr>\n')
    file.write('            <th class="number">#</th>\n')
    file.write('            <th class="name">Test Name</th>\n')
    file.write('            <th class="outcome">Outcome</th>\n')
    file.write('            <th class="duration">Duration (s)</th>\n')
    file.write('        </tr>\n')
    file.write('    </thead>\n')
    file.write('    <tbody>\n')

    for t, test in enumerate(tests, 1):
        name = test["nodeid"].split("::")[-1]
        outcome = format_outcome(test["outcome"])
        duration = round(get_duration(test), 3)
        file.write('        <tr>\n')
        file.write(f'            <td class="number">{t + total}</td>\n')
        file.write(f'            <td class="test-name name">{name}</td>\n')
        file.write(f'            <td class="outcome">{outcome}</td>\n')
        file.write(f'            <td class="duration">{duration}</td>\n')
        file.write('        </tr>\n')

    file.write('    </tbody>\n')
    file.write('</table>\n')

    return total + len(tests)


def write_section(file, data, level, total):
    if isinstance(data, dict):
        for title, value in data.items():
            if title == "_values":
                total = write_test_table(file, value, total)
                continue

            heading_tag = f'h{min(level + 1, 6)}'
            file.write(f'<{heading_tag}>{title}</{heading_tag}>\n')
            total = write_section(file, value, level + 1, total)
    elif isinstance(data, list):
        for value in data:
            total = write_section(file, value, level + 1, total)
    return total


def main():
    report = load_report()
    tests_raw = report["tests"]

    root = {}
    for test in tests_raw:
        parts = [p.strip() for p in test["nodeid"].split("::")]
        node = root
        for key in parts[:-1]:
            if key not in node or not isinstance(node[key], dict):
                node[key] = {}
            node = node[key]
        node.setdefault("_values", []).append(test)

    with open("TEST_REPORT.html", "w", encoding="utf-8") as file:
        file.write(get_html_header())

        total = 0
        for file_name, value in root.items():
            file_name = file_name.split("/")[-1]
            file.write(f'<h2>{file_name}</h2>\n')
            total = write_section(file, value, 2, total)

        file.write(get_html_footer())


if __name__ == "__main__":
    main()
