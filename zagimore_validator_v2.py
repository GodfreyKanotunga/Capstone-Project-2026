import mysql.connector
import csv
import datetime
import sys
import re
import os

DB_HOST     = os.environ.get("DB_HOST", "mysql.clarksonmsda.org")
DB_PORT     = int(os.environ.get("DB_PORT", 3306))
DB_USER     = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

if not DB_USER or not DB_PASSWORD:
    print("ERROR: DB_USER and DB_PASSWORD environment variables must be set.")
    sys.exit(1)

OUTPUT_CSV = os.environ.get(
    "OUTPUT_CSV",
    os.path.join(os.path.expanduser("~"), "Desktop", "ETL-project", "validation_report_v2.csv")
)

SECTION_A_RE = re.compile(r'_S26_ZAGIMORE_DS$',        re.IGNORECASE)
SECTION_B_RE = re.compile(r'(?<!S26)_ZAGIMORE[_]?DS$', re.IGNORECASE)

VALIDATION_CHECKS = [
    {
        "label": "Fact Table (Revenue) Check",
        "procedures": [
            "sp_validate_row_counts_enhanced",
            "sp_validate_row_counts",
            "validate_fact_row_count",
            "validate_row_counts",
            "validate_row_count",
            "p_validate_raw_counts",
        ],
    },
    {
        "label": "Customer Dimension Check",
        "procedures": [
            "sp_validate_customer_dimension",
            "validate_customer_dimension_row_count",
            "validate_customer_dimension",
            "validate_customer_row_count",
        ],
    },
    {
        "label": "Product Dimension Check",
        "procedures": [
            "sp_validate_product_dimension",
            "validate_product_dimension_row_count",
            "validate_product_dimension",
            "validate_product_row_count",
        ],
    },
    {
        "label": "Store Dimension Check",
        "procedures": [
            "sp_validate_store_dimension",
            "validate_store_dimension_row_count",
            "validate_store_dimension",
            "validate_store_row_count",
        ],
    },
]

STATUS_COLUMNS    = ["validation_status"]
DIFFERENCE_COLUMNS = ["source_minus_ds", "ds_minus_dw", "difference", "diff"]
SOURCE_COUNT_COLS = ["sourcerowcount", "src_rows", "src_total", "source_total"]
DS_COUNT_COLS     = ["dsrowcount",     "ds_rows",  "ds_total"]
DW_COUNT_COLS     = ["dwrowcount",     "dw_rows",  "dw_total"]


def get_connection(database=None):
    params = dict(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
    if database:
        params["database"] = database
    return mysql.connector.connect(**params)


def discover_all_databases():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE '%ZAGIMORE%'")
        all_dbs = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        print(f"\nERROR: Could not connect to MySQL server: {e}")
        print("Make sure you are connected to the Clarkson VPN.")
        sys.exit(1)

    students = []
    seen     = set()

    own_db = f"{DB_USER}_ZagiClass_DS"
    students.append({"username": DB_USER, "db_name": own_db, "section": "A"})
    seen.add(own_db.lower())

    for db in all_dbs:
        if re.search(r'_ZAGIMORE$', db, re.IGNORECASE):
            continue
        if re.search(r'_ZAGIMORE_DW$', db, re.IGNORECASE):
            continue
        if db.lower() in seen:
            continue

        if SECTION_A_RE.search(db):
            match = re.match(r'^(.+?)_S26_ZAGIMORE_DS$', db, re.IGNORECASE)
            if match:
                students.append({"username": match.group(1), "db_name": db, "section": "A"})
                seen.add(db.lower())

        elif SECTION_B_RE.search(db):
            match = re.match(r'^(.+?)_ZAGIMORE[_]?DS$', db, re.IGNORECASE)
            if match:
                students.append({"username": match.group(1), "db_name": db, "section": "B"})
                seen.add(db.lower())

    students.sort(key=lambda x: x["username"].lower())
    return students


def try_procedure(cursor, db_name, procedure_names):
    last_error = None
    for proc_name in procedure_names:
        try:
            cursor.execute(f"CALL {db_name}.{proc_name}()")
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows    = cursor.fetchall() if cursor.description else []
            while cursor.nextset():
                pass
            return columns, rows, proc_name, None
        except mysql.connector.Error as e:
            try:
                while cursor.nextset():
                    pass
            except Exception:
                pass
            if e.errno == 1305:
                last_error = str(e)
                continue
            return [], [], proc_name, str(e)

    return [], [], None, last_error


def infer_status(columns, rows):
    cols_lower = [c.lower() for c in columns]
    all_rows   = rows or []

    diff_idxs = [cols_lower.index(c) for c in DIFFERENCE_COLUMNS if c in cols_lower]
    if diff_idxs:
        try:
            all_zero = all(
                int(row[i]) == 0
                for row in all_rows
                for i in diff_idxs
                if row[i] is not None
            )
            return ("PASS" if all_zero else "FAIL"), "inferred from difference columns"
        except (ValueError, TypeError):
            pass

    src_idx = next((cols_lower.index(c) for c in SOURCE_COUNT_COLS if c in cols_lower), None)
    ds_idx  = next((cols_lower.index(c) for c in DS_COUNT_COLS     if c in cols_lower), None)
    dw_idx  = next((cols_lower.index(c) for c in DW_COUNT_COLS     if c in cols_lower), None)

    if src_idx is not None and ds_idx is not None:
        mismatches = []
        for row in all_rows:
            try:
                src = int(row[src_idx]) if row[src_idx] is not None else None
                ds  = int(row[ds_idx])  if row[ds_idx]  is not None else None
                dw  = int(row[dw_idx])  if (dw_idx is not None and row[dw_idx] is not None) else None
                if src != ds:
                    mismatches.append(f"src({src}) != ds({ds})")
                if dw is not None and ds != dw:
                    mismatches.append(f"ds({ds}) != dw({dw})")
            except (ValueError, TypeError):
                pass
        note = "inferred from row count comparison"
        if mismatches:
            return "FAIL", f"{note} -- mismatches: {'; '.join(mismatches)}"
        return "PASS", note

    return "UNKNOWN", "could not infer -- unrecognized column format"


def determine_status(columns, rows):
    cols_lower = [c.lower() for c in columns]
    first_row  = rows[0] if rows else []
    detail     = " | ".join(f"{col}={val}" for col, val in zip(columns, first_row))

    for sc in STATUS_COLUMNS:
        if sc in cols_lower:
            idx    = cols_lower.index(sc)
            status = str(first_row[idx]).strip().upper()
            return status, detail, f"explicit {sc} column"

    status, note = infer_status(columns, rows)
    return status, detail, note


def validate_student(username, db_name, section):
    results   = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*70}")
    print(f"  Student  : {username}  |  Section {section}")
    print(f"  Database : {db_name}")
    print(f"  Time     : {timestamp}")
    print(f"{'='*70}")

    try:
        conn   = get_connection(db_name)
        cursor = conn.cursor()
    except mysql.connector.Error as e:
        print(f"  ERROR: Could not connect -- {e}")
        results.append({
            "student":   username, "section": section, "database": db_name,
            "check":     "DB Connection", "procedure": "N/A",
            "status":    "FAIL", "note": "connection error",
            "detail":    str(e), "timestamp": timestamp,
        })
        return results

    for check in VALIDATION_CHECKS:
        label      = check["label"]
        proc_names = check["procedures"]

        columns, rows, used_proc, error = try_procedure(cursor, db_name, proc_names)

        if error:
            status = "FAIL"
            if used_proc:
                note   = "runtime error -- procedure found but failed"
                detail = f"Procedure {used_proc} exists but raised error: {error}"
            else:
                note   = "procedure not found"
                detail = f"No valid procedure found. Last error: {error}"
            print(f"\n  [{label}]")
            print(f"  FAIL -- {note}")
            print(f"  {detail}")
        else:
            status, detail, note = determine_status(columns, rows)
            print(f"\n  [{label}]")
            print(f"  {status}  (proc: {used_proc} | {note})")
            print(f"  {detail}")

        results.append({
            "student":   username,
            "section":   section,
            "database":  db_name,
            "check":     label,
            "procedure": used_proc if used_proc else "NOT FOUND",
            "status":    status,
            "note":      note,
            "detail":    detail,
            "timestamp": timestamp,
        })

    cursor.close()
    conn.close()
    return results


def print_summary(all_results):
    print(f"\n{'='*70}")
    print("  FINAL SUMMARY -- IA 605 Spring 2026 (Both Sections)")
    print(f"{'='*70}")
    print(f"  {'Sec':<5} {'Student':<15} {'Check':<35} {'Status'}")
    print(f"  {'-'*65}")
    for r in all_results:
        print(f"  {r['section']:<5} {r['student']:<15} {r['check']:<35} {r['status']}")
    print(f"{'='*70}\n")


def save_to_csv(all_results, filename):
    fieldnames = [
        "student", "section", "database", "check",
        "procedure", "status", "note", "detail", "timestamp",
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"Report saved to: {filename}")


if __name__ == "__main__":
    print("=" * 70)
    print("  Zagimore ETL Procedure Validator")
    print("  Capstone-Project-2026 | Clarkson University")
    print("  Semester: Spring 2026 -- Both Sections")
    print("=" * 70)

    print("\nDiscovering student databases (both sections)...")
    students = discover_all_databases()

    if not students:
        print("ERROR: No Zagimore staging databases found on the server.")
        sys.exit(1)

    sec_a = [s for s in students if s["section"] == "A"]
    sec_b = [s for s in students if s["section"] == "B"]

    print(f"\nFound {len(students)} student database(s):")
    print(f"  Section A ({len(sec_a)}): {', '.join(s['username'] for s in sec_a)}")
    print(f"  Section B ({len(sec_b)}): {', '.join(s['username'] for s in sec_b)}")

    all_results = []
    for s in students:
        results = validate_student(s["username"], s["db_name"], s["section"])
        all_results.extend(results)

    print_summary(all_results)
    save_to_csv(all_results, OUTPUT_CSV)
