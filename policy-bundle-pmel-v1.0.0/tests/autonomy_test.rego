package arhia.pmel.base.autonomy_test

import data.arhia.pmel.base.autonomy

test_permit_capture_at_a2 if {
    autonomy.allow with input as {
        "agent": {"component": "capture_agent", "autonomy_level": "A2"}
    }
}

test_deny_escalation_to_a3 if {
    count(autonomy.deny) > 0 with input as {
        "agent": {"component": "to_be_generator", "autonomy_level": "A3"}
    }
}

test_deny_escalation_to_a4 if {
    count(autonomy.deny) > 0 with input as {
        "agent": {"component": "to_be_generator", "autonomy_level": "A4"}
    }
}

test_escalate_unknown_component if {
    count(autonomy.escalate) > 0 with input as {
        "agent": {"component": "unknown_new_agent", "autonomy_level": "A2"}
    }
}

test_suspend_repeated_violations if {
    count(autonomy.suspend) > 0 with input as {
        "agent": {"component": "capture_agent", "autonomy_level": "A2", "violation_count": 3}
    }
}
