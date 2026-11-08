const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname,
  '../../datadog/workflows/investigate-network-mac-flapping.json'), 'utf8')).spec;
const script = name => new Function('$', spec.steps.find(s => s.name === name).parameters[0].value);
test('all workflow Slack messages match Operational Conditions channel and thread behavior',()=>{
  const slack=spec.steps.filter(s=>s.actionId.includes('slack'));
  assert.equal(slack.length,4);
  for(const s of slack){
    assert.equal(s.parameters.find(p=>p.name==='channel').value,'#datadog-automation');
    assert.equal(s.parameters.some(p=>p.name==='sendInThread'),false);
  }
});
function samples(values, timestamp=Date.now()-30000) {
  return {status:'ok',series:values.map(([port,value])=>({scope:port?'interface:'+port:'',pointlist:[[timestamp,value]]}))};
}
function context() {
  return {Steps:{Record_AAP_Execution:{data:{status:'JOB_NOT_CONFIGURED',job_launched:false,execution_succeeded:false,aap_job_id:''}},
    Verify_Monitor_State:{overall_state:'OK'},
    Verify_Interface_Admin:samples([['ethernet-1/1',1],['ethernet-1/2',2],['ethernet-1/3',1]]),
    Verify_Interface_Oper:samples([['ethernet-1/1',1],['ethernet-1/2',2],['ethernet-1/3',1]]),
    Verify_Forwarding:samples([['',0]]),Verify_Collector_Freshness:samples([['',1]])}};
}
test('AAP recovery preparation requires an authenticated approval',()=>{
  const Variables={};const Helpers={setVariable:(k,v)=>Variables[k]=v};
  const r=script('Prepare_AAP_Recovery')({Variables,Helpers,Steps:{Record_Approval_Decision:{data:{approval_status:'APPROVED',responder:{id:'U_TEST'}}}}});
  assert.equal(Variables.aap_phase,'collect');assert.equal(r.target_interface,'ethernet-1/2');
  assert.equal(r.job_launched,false);
  assert.throws(()=>script('Prepare_AAP_Recovery')({Variables,Helpers,Steps:{Record_Approval_Decision:{data:{approval_status:'REJECTED'}}}}));
});
test('all green telemetry cannot establish recovery without execution and device evidence',()=>{
  const r=script('Evaluate_Recovery')(context());
  assert.equal(r.criteria.fixed_port_isolated,true);assert.equal(r.criteria.trusted_ports_up,true);
  assert.equal(r.criteria.independent_forwarding_zero_loss,true);
  assert.equal(r.criteria.monitor_ok,true);assert.equal(r.recovery_verified,false);
  assert.ok(r.missing.includes('device_duplicate_state_verified'));
  assert.ok(r.missing.includes('post_execution_evidence_verified'));
});
test('missing, null, stale and duplicate metric samples fail closed',()=>{
  for(const metric of [{status:'ok',series:[]},samples([['',null]]),samples([['',0]],Date.now()-181000),samples([['',0],['',0]])]){
    const c=context();c.Steps.Verify_Forwarding=metric;
    const r=script('Evaluate_Recovery')(c);
    assert.equal(r.criteria.independent_forwarding_zero_loss,false);assert.equal(r.recovery_verified,false);
  }
});
test('unexpected port state and packet loss stay unverified',()=>{
  const c=context();c.Steps.Verify_Interface_Oper=samples([['ethernet-1/1',2],['ethernet-1/2',1],['ethernet-1/3',1]]);
  c.Steps.Verify_Forwarding=samples([['',33.3]]);
  const r=script('Evaluate_Recovery')(c);
  assert.equal(r.criteria.trusted_ports_up,false);assert.equal(r.criteria.fixed_port_isolated,false);
  assert.equal(r.criteria.independent_forwarding_zero_loss,false);
});
test('read failure stops and escalation has no route back to execute',()=>{
  const r=script('Evaluate_Recovery')({Steps:{Verification_Collection_Failed:{data:{reason:'test read failure'}}}});
  assert.equal(r.recovery_verified,false);assert.equal(r.observed.collection_error,'test read failure');
  const d=script('Stop_And_Escalate')({WorkflowId:'w',InstanceId:'i',Steps:{Evaluate_Recovery:{data:r}}});
  assert.equal(d.stopped,true);assert.equal(d.automatic_retry,false);assert.equal(d.escalation_required,true);
  assert.match(d.slack_text,/RECOVERY NOT VERIFIED/);
  assert.equal(spec.steps.find(s=>s.name==='Slack_Escalate_Recovery').outboundEdges[0].nextStepName,'Complete');
});
test('escalation delivery failure is visible in final result',()=>{
  const r=script('Complete')({Steps:{Report:{data:{status:'COMPLETED'}},Stop_And_Escalate:{data:{workflow_result:'RECOVERY_NOT_VERIFIED'}},Escalation_Delivery_Failed:{data:script('Escalation_Delivery_Failed')({})}}});
  assert.equal(r.workflow_result,'ESCALATION_DELIVERY_FAILED');assert.equal(r.escalation_sent,false);
  assert.equal(r.recovery_verified,false);assert.equal(r.automatic_retry,false);
});
