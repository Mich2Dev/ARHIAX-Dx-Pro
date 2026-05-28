import psycopg2
import json

conn = psycopg2.connect('postgresql://arhiax:arhiax@localhost:5432/arhiax_dx')
cur = conn.cursor()

cur.execute("SELECT token, questions FROM survey_sessions ORDER BY created_at DESC LIMIT 3")
rows = cur.fetchall()

for token, q in rows:
    print(f"\nToken: {token}")
    if isinstance(q, dict):
        raw = q.get('raw_output', '')
        qs  = q.get('questions', [])
        print(f"  questions array: {len(qs)}")
        print(f"  raw_output length: {len(raw)}")
        if raw:
            # Try to parse
            try:
                parsed = json.loads(raw)
                qs2 = parsed.get('questions', [])
                print(f"  parsed from raw: {len(qs2)} questions")
                if qs2:
                    print(f"  first q keys: {list(qs2[0].keys())}")
                    print(f"  first q roles: {qs2[0].get('roles', qs2[0].get('rol_target', 'N/A'))}")
            except Exception as e:
                print(f"  parse error: {e}")
                print(f"  last 100 chars: {raw[-100:]}")

conn.close()
