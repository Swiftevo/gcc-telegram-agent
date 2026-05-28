"""
test_project_cases.py -- project case database smoke tests

Run:
python test_project_cases.py
"""

from core.project_cases import (
    case_to_legacy_project,
    load_ai_review_cases,
    load_project_case_database,
    load_project_cases,
)


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  {status} {name}" + (f" ({detail})" if detail else ""))
    return bool(condition)


def test_project_case_database():
    db = load_project_case_database(force_reload=True)
    cases = load_project_cases()
    ai_cases = load_ai_review_cases()
    categories = {case.get("category") for case in cases}

    results = [
        check("database has schema_version", bool(db.get("schema_version"))),
        check("database has six seed cases", len(cases) == 6, f"count={len(cases)}"),
        check(
            "database covers six categories",
            categories
            == {
                "Open Source",
                "Community",
                "Event",
                "ETH City Series",
                "Travel Scholarship",
                "Gitcoin",
            },
            f"categories={sorted(categories)}",
        ),
        check("all seed cases are available for AI review", len(ai_cases) == len(cases)),
    ]

    for case in cases:
        evidence = case.get("evidence", {})
        results.extend(
            [
                check(f"{case['case_id']} has snapshots", bool(evidence.get("snapshots"))),
                check(
                    f"{case['case_id']} reserves application pointer",
                    "grant_application" in evidence,
                ),
                check(
                    f"{case['case_id']} reserves voting pointer",
                    "voting_record" in evidence,
                ),
            ]
        )

    legacy = case_to_legacy_project(cases[0])
    results.append(check("legacy conversion keeps name", legacy["name"] == cases[0]["title"]))
    results.append(check("legacy conversion keeps summary", bool(legacy["summary"])))

    return all(results)


if __name__ == "__main__":
    print("\n[ Project Case Database ]")
    ok = test_project_case_database()
    print("\nResult:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)

