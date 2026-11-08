const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const spec=JSON.parse(fs.readFileSync(path.join(__dirname,'../../datadog/workflows/investigate-network-mac-flapping.json'),'utf8')).spec;
const script=n=>new Function('$',spec.steps.find(s=>s.name===n).parameters[0].value);
function ctx(phase='isolate'){
 const Variables={aap_phase:phase,aap_config:{id:39,name:'Isolate Host B',playbook:'lab-v2/ansible/isolate-b.yml',extra_vars:{lab_id:'macflap-v2',target_interface:'ethernet-1/2',change_approved:true}},aap_job_id:'123',aap_jobs:{},aap_poll_count:0};
 return {Variables,Steps:{},Helpers:{setVariable:(k,v)=>Variables[k]=v}};
}
function template(){return {status:200,body:{id:39,playbook:'lab-v2/ansible/isolate-b.yml',inventory:7,project:37,job_type:'run',ask_variables_on_launch:true,summary_fields:{user_capabilities:{start:true}}}};}
test('fixed template mapping contains only 38-41, restore 42 is never auto-launched',()=>{
 for(const [p,id,phase]of [['Collect',38,'collect'],['Isolate',39,'isolate'],['Device',40,'verify_device'],['Forward',41,'verify_forwarding']]){
  const c=ctx(phase);const r=script(p+'_Configure_AAP_Phase')(c);assert.equal(r.id,id);
  assert.ok(!JSON.stringify(r).includes('42'));
 }
});
test('template fingerprint, permission and approved extra vars fail closed',()=>{
 for(const mutate of [r=>r.status=403,r=>r.body.id=42,r=>r.body.playbook='other.yml',r=>r.body.inventory=null,r=>r.body.inventory=8,r=>r.body.project=99,r=>r.body.summary_fields.user_capabilities.start=false,r=>{r.body.ask_variables_on_launch=false;r.body.extra_vars='{}';}]){
  const c=ctx(),r=template();mutate(r);c.Steps.Isolate_AAP_Read_Template=r;
  assert.equal(script('Isolate_Validate_AAP_Template')(c).valid,false);
 }
 const c=ctx();c.Steps.Isolate_AAP_Read_Template=template();assert.equal(script('Isolate_Validate_AAP_Template')(c).valid,true);
});
test('launch validates template identity and ignored approval variables',()=>{
 for(const body of [{id:123,job_template:42},{id:123,job_template:39,ignored_fields:{extra_vars:{change_approved:true}}}]){
  const c=ctx();c.Steps.Isolate_AAP_Launch_Fixed_Job={status:201,body};
  assert.equal(script('Isolate_Validate_AAP_Launch')(c).valid,false);
  assert.equal(c.Variables.aap_job_id,'123'); // Preserve possibly launched job for manual review.
 }
});
test('job polling validates both job ID and template ID',()=>{
 for(const body of [{id:124,job_template:39,status:'successful'},{id:123,job_template:42,status:'successful'}]){
  const c=ctx();c.Steps.Isolate_AAP_Get_Job={status:200,body};
  assert.equal(script('Isolate_Record_AAP_Job_State')(c).valid,false);
  assert.equal(c.Variables.aap_job_state,'invalid');
 }
 const c=ctx();c.Steps.Isolate_AAP_Get_Job={status:200,body:{id:123,job_template:39,status:'successful',finished:new Date().toISOString()}};
 assert.equal(script('Isolate_Record_AAP_Job_State')(c).status,'successful');
});
test('polls are bounded and launch requests never retry',()=>{
 for(const p of ['Collect','Isolate','Device','Forward']){
  const launch=spec.steps.find(s=>s.name===p+'_AAP_Launch_Fixed_Job');
  assert.equal(launch.errorHandlers[0].retryStrategy.linear.maxRetries,0);
  const loop=spec.steps.find(s=>s.name===p+'_Poll_AAP_Job');
  assert.equal(loop.parameters[0].value[0].rightValue,60);
 }
});
test('integration failure records possible partial execution and never relaunches',()=>{
 const c=ctx();const r=script('AAP_Integration_Failed')(c);
 assert.equal(r.status,'AAP_INTEGRATION_FAILED');assert.equal(r.remediation_may_have_run,true);
});
