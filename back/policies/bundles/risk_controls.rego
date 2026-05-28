package arhiax.dx.risk

default publication_requires_human = true

deny_reason contains "retention_exceeds_30_days" if {
  input.processing_profile.retention_days > 30
}

deny_reason contains "raw_respondent_storage" if {
  input.processing_profile.store_raw_respondent_data
}

deny_reason contains "docx_low_qa" if {
  some i
  input.requested_tools[i] == "docx_generator"
  input.simulation.qa_score < 85
}

escalate_reason contains "publish_report" if {
  input.processing_profile.publish_report
}
