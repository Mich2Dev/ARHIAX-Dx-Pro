"""Inspect real diagnostic output to understand what data is available for PDF."""
import psycopg2
import json

conn = psycopg2.connect('postgresql://arhiax:arhiax@localhost:5432/arhiax_dx')
cur = conn.cursor()

# Get completed diagnostics
cur.execute("""
    SELECT id, organization_name, domain, subprocess, objective, size_org, 
           status, decision, autonomy_level, created_at, completed_at
    FROM diagnostics 
    WHERE status = 'completed'
    ORDER BY created_at DESC LIMIT 3
""")
diagnostics = cur.fetchall()
print(f"Completed diagnostics: {len(diagnostics)}")

for diag in diagnostics:
    diag_id, org, domain, subprocess, objective, size_org, status, decision, autonomy, created, completed = diag
    print(f"\n{'='*60}")
    print(f"Org: {org}")
    print(f"Domain: {domain} | Subprocess: {subprocess}")
    print(f"Status: {status} | Decision: {decision}")
    
    # Get all stages with their outputs
    cur.execute("""
        SELECT tool_name, phase, status, model_used, tokens_used, latency_ms, output
        FROM pipeline_stages
        WHERE diagnostic_id = %s AND status = 'completed'
        ORDER BY created_at
    """, (diag_id,))
    stages = cur.fetchall()
    print(f"\nCompleted stages: {len(stages)}")
    
    for tool_name, phase, st, model, tokens, latency, output in stages:
        if output:
            actual = output.get('output', output)
            if isinstance(actual, dict):
                keys = list(actual.keys())
                # Check for raw_output
                has_raw = 'raw_output' in actual
                print(f"  {tool_name:25} | {tokens or 0:6} tok | keys: {keys[:5]} {'[RAW]' if has_raw else ''}")
                
                # Show key content for important agents
                if tool_name == 'g13_redactor' and not has_raw:
                    print(f"    executive_summary: {str(actual.get('executive_summary',''))[:100]}")
                    print(f"    main_findings: {len(actual.get('main_findings',[]))} items")
                    print(f"    roadmap keys: {list(actual.get('roadmap',{}).keys())}")
                    
                if tool_name == 'g12_hallazgos' and not has_raw:
                    print(f"    findings_matrix: {len(actual.get('findings_matrix',[]))} items")
                    print(f"    problem_statements: {len(actual.get('problem_statements',[]))} items")
                    print(f"    strategic_recommendations: {len(actual.get('strategic_recommendations',[]))} items")
                    
                if tool_name == 'g07_cuellos' and not has_raw:
                    print(f"    bottlenecks: {len(actual.get('bottlenecks',[]))} items")
                    print(f"    total_loss: {actual.get('total_opportunity_loss_usd_month','N/A')}")
                    
                if tool_name == 'g11a_bayesiano' and not has_raw:
                    print(f"    confirmed_hypotheses: {actual.get('confirmed_hypotheses',[])}")
                    print(f"    critical_gaps: {len(actual.get('critical_perception_gaps',[]))} items")
                    
                if tool_name == 'g10a_scoring' and not has_raw:
                    print(f"    overall_score: {actual.get('scoring_summary',{}).get('overall_score','N/A')}")
                    print(f"    delta_sigma: {actual.get('delta_sigma',{}).get('max_gap','N/A')}")
                    
                if tool_name == 'g14_qa_control' and not has_raw:
                    print(f"    qa_score: {actual.get('qa_score','N/A')}")
                    print(f"    approved: {actual.get('approved_for_rendering','N/A')}")

conn.close()
