import psycopg2

conn = psycopg2.connect('postgresql://arhiax:arhiax@localhost:5432/arhiax_dx')
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

# Check alembic version
cur.execute("SELECT version_num FROM alembic_version")
versions = [r[0] for r in cur.fetchall()]
print('Alembic versions:', versions)

conn.close()
