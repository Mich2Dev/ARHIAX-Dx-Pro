package arhiax.dx.governance

default allow = false

allow if {
  input.client.authorized_boundary_id == "boundary-diagnostico-org"
  input.requested_autonomy_level == "A1"
}

deny_reason contains "boundary_mismatch" if {
  input.client.authorized_boundary_id != "boundary-diagnostico-org"
}

deny_reason contains "invalid_autonomy" if {
  not input.requested_autonomy_level == "A0"
  not input.requested_autonomy_level == "A1"
  not input.requested_autonomy_level == "A2"
}
