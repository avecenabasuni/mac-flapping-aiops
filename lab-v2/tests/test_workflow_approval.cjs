const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname,
  '../../datadog/workflows/investigate-network-mac-flapping.json'), 'utf8')).spec;
const script = name => new Function('$', spec.steps.find(s => s.name === name).parameters[0].value);
function context() {
  return {Steps: {Normalize_Context: {data: {mode:'monitor_alert',notify_slack:true}},
    Report: {data: {status:'COMPLETED',classification:'MAC_FLAPPING_EVIDENCE',confidence:'HIGH',
      evidence:{sample_complete:true,counts_in_returned_sample:{unparsed:0,detections:2},warnings:[],
        hosts:['sw1'],macs:['02:00:00:00:00:aa'],expected_recovery_status:'UNVERIFIED',
        timeline:{latest_detection_at:new Date(Date.now()-60000).toISOString()}}}}}};
}
test('fresh bounded lab evidence permits placeholder decision only', () => {
  const r=script('Evaluate_Approval_Eligibility')(context());
  assert.equal(r.eligible,true);assert.equal(r.execution_enabled,false);
  assert.equal(r.job_template_id,'');assert.equal(r.remediation_allowed,false);
});
test('manual, stale, incomplete, foreign and cleared evidence cannot request approval', () => {
  const mutations=[c=>c.Steps.Normalize_Context.data.mode='manual_replay',
    c=>c.Steps.Normalize_Context.data.notify_slack=false,
    c=>c.Steps.Report.data.status='AI_ANALYSIS_FAILED',
    c=>c.Steps.Report.data.confidence='LOW',
    c=>c.Steps.Report.data.evidence.sample_complete=false,
    c=>c.Steps.Report.data.evidence.counts_in_returned_sample.unparsed=1,
    c=>c.Steps.Report.data.evidence.hosts=['other'],
    c=>c.Steps.Report.data.evidence.macs=['00:00:00:00:00:01'],
    c=>c.Steps.Report.data.evidence.expected_recovery_status='CLEAR_EVENT_OBSERVED',
    c=>c.Steps.Report.data.evidence.timeline.latest_detection_at=new Date(Date.now()-16*60000).toISOString()];
  for(const mutate of mutations){const c=context();mutate(c);assert.equal(script('Evaluate_Approval_Eligibility')(c).eligible,false);}
});
test('approve, reject and missing actor are audited without any AAP job', () => {
  for(const [decision,expected] of [['approve','JOB_NOT_CONFIGURED'],['reject','REMEDIATION_REJECTED'],['unexpected','APPROVAL_UNAVAILABLE']]){
    const r=script('Record_Approval_Decision')({Steps:{Slack_Approval_Request:{decision,responder:{id:'U_TEST',team_id:'T_TEST',username:'fixture'}}}});
    assert.equal(r.workflow_result,expected);assert.equal(r.aap_job_id,'');
    assert.equal(r.remediation_executed,false);assert.equal(r.recovery_verified,false);
  }
  assert.equal(script('Record_Approval_Decision')({Steps:{Slack_Approval_Request:{decision:'approve'}}}).workflow_result,'APPROVAL_UNAVAILABLE');
});
test('approval timeout/error fails closed and formatter never claims remediation', () => {
  const d=script('Approval_Unavailable')({});
  const r=script('Format_Decision_Result')({WorkflowId:'w',InstanceId:'i',Steps:{Approval_Unavailable:{data:d}}});
  assert.equal(d.workflow_result,'APPROVAL_UNAVAILABLE');assert.match(r.slack_text,/No remediation executed/);
});
test('no executable AAP or native investigation actions exist', () => {
  for(const s of spec.steps)assert.ok(!/http.request|ansible|bitsai.sre/i.test(s.actionId));
  const a=spec.steps.find(s=>s.name==='Slack_Approval_Request');
  assert.equal(a.parameters.find(p=>p.name==='timeoutHours').value,1);
  assert.equal(a.parameters.find(p=>p.name==='channel').value,'#datadog-automation');
});
