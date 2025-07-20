import json


def load_report(path="report.json"):
    with open(path, "r") as f:
        return json.load(f)


def format_outcome(status):
    return {
        "passed": "✅",
        "failed": "❌",
        "skipped": "⏭️"
    }.get(status, status)


def get_duration(test):
    duration = 0
    for step in ("setup", "call", "teardown"):
        duration += test.get(step, {}).get("duration", 0)
    return duration


def main():
    report = load_report()
    tests = report["tests"]

    with open("TEST_REPORT.md", "w", encoding="utf-8") as file:
        print("# Test Report", file=file)
        print("| Test Name | Outcome | Duration (s) |", file=file)
        print("|-----------|---------|---------------|", file=file)

    with open("TEST_REPORT.md", "a", encoding="utf-8") as file:
        for test in tests:
            name = test["nodeid"]
            outcome = format_outcome(test["outcome"])
            duration = round(get_duration(test), 3)
            print(f"| `{name}` | {outcome} | {duration} |", file=file)


if __name__ == "__main__":
    main()
