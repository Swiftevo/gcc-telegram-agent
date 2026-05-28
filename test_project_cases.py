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
        check("five seed cases are available for AI review", len(ai_cases) == 5),
        check(
            "gitcoin placeholder is excluded from AI review",
            any(
                case.get("case_id") == "gcc-gitcoin-placeholder"
                and case.get("ai_review_usage", {}).get("allowed") is False
                for case in cases
            ),
        ),
    ]

    for case in cases:
        evidence = case.get("evidence", {})
        public_record = case.get("public_record", {})
        is_placeholder = case.get("case_id") == "gcc-gitcoin-placeholder"
        results.extend(
            [
                check(
                    f"{case['case_id']} has snapshots or is placeholder",
                    bool(evidence.get("snapshots")) or is_placeholder,
                ),
                check(
                    f"{case['case_id']} reserves application pointer",
                    "grant_application" in evidence,
                ),
                check(
                    f"{case['case_id']} reserves voting pointer",
                    "voting_record" in evidence,
                ),
                check(f"{case['case_id']} has funding block", "funding" in public_record),
                check(
                    f"{case['case_id']} has public goods dimensions",
                    "public_goods_dimensions" in public_record,
                ),
                check(
                    f"{case['case_id']} has lifecycle status",
                    "lifecycle_status" in public_record,
                ),
                check(f"{case['case_id']} has raw data status", "raw_data_status" in evidence),
            ]
        )

    if cases:
        legacy = case_to_legacy_project(cases[0])
        results.append(check("legacy conversion keeps name", legacy["name"] == cases[0]["title"]))
        results.append(check("legacy conversion keeps summary", bool(legacy["summary"])))
    else:
        results.append(check("legacy conversion skipped because no cases loaded", False))

    return all(results)


if __name__ == "__main__":
    print("\n[ Project Case Database ]")
    ok = test_project_case_database()
    print("\nResult:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
