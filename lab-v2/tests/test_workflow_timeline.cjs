const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const spec = JSON.parse(fs.readFileSync(path.join(__dirname,
  "../../datadog/workflows/investigate-network-mac-flapping.json"), "utf8")).spec;
function script(name) {
  return new Function("$", spec.steps.find(s => s.name === name)
    .parameters.find(p => p.name === "script").value);
}
const extract = script("Extract_Evidence"), finalize = script("Finalize_Report");
let seq = 0;
function log(action, minute, target = "sub-interface ethernet-1/2.1", attrs = {}) {
  seq += 1;
  const prefix = "bridgetable|2163|2163|" + seq + "|N: A duplicate MAC address 02:00:00:00:00:AA ";
  return {id: "log-" + seq, attributes: {
    host: "sw1", service: "sr_l2_mac_mgr",
    timestamp: "2026-11-06T06:" + minute + ":00Z",
    tags: ["env:network-aiops", "service:nokia-srlinux"],
    message: prefix + (action === "detected" ? "was detected on " + target + "."
      : "detected on " + target + " is now deleted."),
    ...attrs
  }};
}
function evidence(rows, meta = {status: "done"}) {
  return extract({Steps: {
    Normalize_Context: {data: {incident_key: "test", mode: "manual_replay",
      window: {from: "2026-11-06T06:00:00Z", to: "2026-11-06T07:00:00Z"}}},
    Search_Incident_Logs: {data: rows, meta},
    Get_Monitor: {overall_state: "Alert"}
  }});
}
function agent(e, recovery = e.expected_recovery_status) {
  return {status: "completed", finalResponse: {
    classification: e.classification, recovery_status: recovery, confidence: "HIGH",
    summary: "Fixture evidence summary", limitations: [], next_checks: [],
    evidence_log_ids: e.entries.map(x => x.log_id), physical_loop_confirmed: false,
    device_recovery_verified: false, remediation_allowed: false
  }, toolCalls: [{name: "validate_output", executionMetadata: {type: "internal"}}]};
}
function report(e, a = agent(e)) {
  return finalize({Steps: {Extract_Evidence: {data: e}, Run_Agent: a}});
}

test("old deletions cannot clear newer detections: actual v2 regression", () => {
  const e = evidence([log("deleted", "10"), log("deleted", "10", "mac-flap"),
    log("detected", "20"), log("detected", "20", "mac-flap")]);
  assert.equal(e.expected_recovery_status, "UNVERIFIED");
  assert.equal(e.timeline.unmatched_detection_targets, 2);
  assert.equal(report(e).status, "COMPLETED");
  assert.equal(report(e).classification, "MAC_FLAPPING_EVIDENCE");
});
test("deletions after all matching detections are clear-event evidence only", () => {
  const e = evidence([log("detected", "10"), log("detected", "10", "mac-flap"),
    log("deleted", "20"), log("deleted", "20", "mac-flap")]);
  assert.equal(e.expected_recovery_status, "CLEAR_EVENT_OBSERVED");
  assert.equal(report(e).device_recovery_verified, false);
  assert.equal(report(e).remediation_allowed, false);
});
test("new detection after clear invalidates earlier clear", () => {
  assert.equal(evidence([log("detected", "10"), log("deleted", "20"),
    log("detected", "30")]).expected_recovery_status, "UNVERIFIED");
});
test("equal timestamps do not establish event ordering", () => {
  assert.equal(evidence([log("detected", "20"), log("deleted", "20")])
    .expected_recovery_status, "UNVERIFIED");
});
test("wrong host, MAC or target cannot clear a detection", () => {
  const wrongMac = log("deleted", "20");
  wrongMac.attributes.message = wrongMac.attributes.message.replace(":AA", ":BB");
  for (const clear of [log("deleted", "20", undefined, {host: "sw2"}),
    wrongMac, log("deleted", "20", "sub-interface ethernet-1/1.1")]) {
    assert.equal(evidence([log("detected", "10"), clear])
      .expected_recovery_status, "UNVERIFIED");
  }
});
test("partial clearing of two targets remains unverified", () => {
  assert.equal(evidence([log("detected", "10"), log("detected", "10", "mac-flap"),
    log("deleted", "20")]).expected_recovery_status, "UNVERIFIED");
});
test("empty and detection-only samples remain unverified", () => {
  for (const rows of [[], [log("detected", "20")]]) {
    assert.equal(evidence(rows).expected_recovery_status, "UNVERIFIED");
  }
});
test("deletion-only sample records a clear event, never verified recovery", () => {
  const e = evidence([log("deleted", "20")]);
  assert.equal(e.classification, "CLEAR_EVENT_OBSERVED");
  assert.equal(report(e).device_recovery_verified, false);
});
test("incomplete/truncated/warned samples cannot establish latest clear", () => {
  for (const meta of [{status: "running"}, {status: "done", page: {after: "next"}},
    {status: "done", warnings: [{}]}]) {
    assert.equal(evidence([log("detected", "10"), log("deleted", "20")], meta)
      .expected_recovery_status, "UNVERIFIED");
  }
});
test("unsafe recovery status and invented citations are rejected", () => {
  const e = evidence([log("deleted", "10"), log("detected", "20")]);
  assert.equal(report(e, agent(e, "CLEAR_EVENT_OBSERVED")).status, "AI_ANALYSIS_FAILED");
  const bad = agent(e);
  bad.finalResponse.evidence_log_ids.push("invented");
  assert.equal(report(e, bad).status, "AI_ANALYSIS_FAILED");
});
test("agent-only graph has no native actions or dangling edges", () => {
  const names = new Set(spec.steps.map(s => s.name));
  assert.equal(spec.steps.length, 101);
  for (const s of spec.steps) {
    assert.ok(!s.actionId.includes("bitsai.sre"));
    for (const edge of s.outboundEdges || []) assert.ok(names.has(edge.nextStepName));
  }
});
function message(result, notify = true) {
  return script("Report")({WorkflowId: "workflow", InstanceId: "instance", Steps: {
    Normalize_Context: {data: {query: "scoped-query", notify_slack: notify,
      window: {from: "2026-11-06T06:00:00Z", to: "2026-11-06T07:00:00Z"}}},
    Finalize_Report: {data: result}
  }});
}
test("POC message reports evidence and neutralizes injected Slack mentions", () => {
  const e = evidence([log("detected", "20")]);
  const r = report(e); r.summary = "<@channel> @here";
  const out = message(r);
  assert.match(out.slack_text, /INCIDENT RESPONSE · EVIDENCE REVIEWED/);
  assert.match(out.slack_text, /No Automatic Remediation/);
  assert.ok(!out.slack_text.includes("<@channel>"));
  assert.ok(!out.slack_text.includes("@here"));
  assert.ok(!out.slack_text.includes("Native Bits Investigation"));
  assert.equal(out.notify_slack, true);
});
test("failed or skipped reports never claim successful investigation", () => {
  const failed = message({status: "COLLECTION_FAILED", classification: "UNKNOWN"});
  assert.match(failed.slack_text, /INVESTIGATION FAILED/);
  assert.ok(!failed.slack_text.includes("Analysis Completed"));
  assert.equal(message({status: "SKIPPED"}).notify_slack, false);
  assert.equal(message({status: "COMPLETED"}, false).notify_slack, false);
});
