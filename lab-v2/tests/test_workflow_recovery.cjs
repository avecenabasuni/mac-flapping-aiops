const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const spec=JSON.parse(fs.readFileSync(path.join(__dirname,'../../datadog/workflows/investigate-network-mac-flapping.json'),'utf8')).spec;
const script=n=>new Function('$',spec.steps.find(s=>s.name===n).parameters[0].value);
function context(){
 const now=Date.now(),isoEnd=now-420000,at=n=>new Date(n).toISOString();
 const job=(id,template,start,end)=>({id,template_id:template,status:'successful',valid:true,started:at(start),finished:at(end)});
 const Variables={aap_jobs:{isolate:job(139,39,isoEnd-10000,isoEnd),verify_device:job(140,40,isoEnd+1000,isoEnd+10000),verify_forwarding:job(141,41,isoEnd+11000,isoEnd+20000)},verification_deadline:now+600000,verification_attempt:0,verification_read_failed:false};
 const metric=values=>({status:'ok',series:values.map(([port,value])=>({scope:port?'interface:'+port:'',pointlist:[90000,60000,30000].map(age=>[now-age,value])}))});
 const seed=target=>({log_id:'seed-'+target,timestamp:at(isoEnd-60000),host:'sw1',mac:'02:00:00:00:00:aa',event_action:'detected',target_type:target==='mac-flap'?'mac-vrf':'sub-interface',interface:target==='mac-flap'?'':target,network_instance:target==='mac-flap'?target:''});
 const Steps={Record_Approval_Decision:{data:{approval_status:'APPROVED',responder:{id:'U_TEST'}}},Record_AAP_Execution:{data:{execution_succeeded:true,job_launched:true,aap_job_id:'139',remediation_executed:true}},Report:{data:{evidence:{entries:[seed('mac-flap'),seed('ethernet-1/2.1')]}}},Verify_Monitor_State:{overall_state:'OK'},Verify_Interface_Admin:metric([['ethernet-1/1',1],['ethernet-1/2',2],['ethernet-1/3',1]]),Verify_Interface_Oper:metric([['ethernet-1/1',1],['ethernet-1/2',2],['ethernet-1/3',1]]),Verify_Forwarding:metric([['',0]]),Verify_Collector_Freshness:metric([['',1]]),Verify_Recovery_Logs:{data:[],meta:{status:'done'}}};
 const c={Variables,Steps,Helpers:{setVariable:(k,v)=>Variables[k]=v},WorkflowId:'w',InstanceId:'i'};
 c.log=(target,action='deleted',time=isoEnd+60000)=>({id:'log-'+target+'-'+time+'-'+action,attributes:{host:'sw1',service:'sr_l2_mac_mgr',timestamp:at(time),tags:['env:network-aiops','service:nokia-srlinux'],message:'bridgetable|2163|2163|00001|N: A duplicate MAC address 02:00:00:00:00:AA '+(action==='detected'?'was detected on ':'detected on ')+(target==='mac-flap'?'':'sub-interface ')+target+(action==='detected'?'.':' is now deleted.')}});
 Steps.Verify_Recovery_Logs.data=[c.log('mac-flap'),c.log('ethernet-1/2.1')];return c;
}
const evaluate=c=>script('Evaluate_Recovery')(c);
test('complete post-job telemetry and matching clears plus quiet window can verify recovery',()=>{
 const c=context(),r=evaluate(c);assert.equal(r.recovery_verified,true);assert.equal(r.status,'RECOVERY_VERIFIED');
 assert.equal(Object.keys(r.criteria).length,13);assert.deepEqual(r.missing,[]);assert.equal(c.Variables.verification_continue,false);
 assert.equal(r.device_mac_table_clearance_confirmed,false);assert.equal(r.physical_loop_confirmed,false);
});
test('approval, successful exact jobs and post-isolation verification order are mandatory',()=>{
 for(const mutate of [c=>c.Steps.Record_Approval_Decision.data.approval_status='REJECTED',c=>c.Variables.aap_jobs.isolate.status='failed',c=>c.Variables.aap_jobs.verify_device.template_id=42,c=>c.Variables.aap_jobs.verify_forwarding.valid=false,c=>c.Variables.aap_jobs.verify_forwarding.started=c.Variables.aap_jobs.isolate.started,c=>c.Steps.AAP_Integration_Failed={data:{reason:'failure'}}]){const c=context();mutate(c);assert.equal(evaluate(c).recovery_verified,false);assert.equal(c.Variables.verification_continue,false);}
});
test('old clears cannot clear newer detections, and both detection targets must clear',()=>{
 const c=context();c.Steps.Verify_Recovery_Logs.data.pop();assert.equal(evaluate(c).criteria.matching_post_isolation_log_clearance,false);
 const d=context();d.Steps.Verify_Recovery_Logs.data.push(d.log('ethernet-1/2.1','detected',Date.now()-10000));assert.equal(evaluate(d).recovery_verified,false);
});
test('a matching clear during the approved isolation job counts, but a pre-start clear does not',()=>{
 const c=context(),start=Date.parse(c.Variables.aap_jobs.isolate.started);
 c.Steps.Verify_Recovery_Logs.data=[c.log('mac-flap','deleted',start+5000),c.log('ethernet-1/2.1','deleted',start+5000)];
 assert.equal(evaluate(c).recovery_verified,true);
 const d=context(),before=Date.parse(d.Variables.aap_jobs.isolate.started)-1;
 d.Steps.Verify_Recovery_Logs.data=[d.log('mac-flap','deleted',before),d.log('ethernet-1/2.1','deleted',before)];
 assert.equal(evaluate(d).recovery_verified,false);
});
test('wrong host/MAC/target and malformed logs never establish clearance',()=>{
 for(const mutate of [c=>c.Steps.Verify_Recovery_Logs.data[0].attributes.host='other',c=>c.Steps.Verify_Recovery_Logs.data[0].attributes.message=c.Steps.Verify_Recovery_Logs.data[0].attributes.message.replace('00:AA','00:BB'),c=>c.Steps.Verify_Recovery_Logs.data[1]=c.log('ethernet-1/3.1'),c=>c.Steps.Verify_Recovery_Logs.data[0].attributes.message='DATADOG_SYSLOG_TEST']){const c=context();mutate(c);assert.equal(evaluate(c).recovery_verified,false);}
});
test('incomplete, warned or truncated queries fail closed immediately',()=>{
 for(const meta of [{status:'running'},{status:'done',page:{after:'cursor'}},{status:'done',warnings:['partial']}]){const c=context();c.Steps.Verify_Recovery_Logs.meta=meta;assert.equal(evaluate(c).criteria.complete_log_query,false);assert.equal(c.Variables.verification_continue,false);}
});
test('quiet window starts after matching deletion, not only after last detection',()=>{
 const c=context();c.Steps.Verify_Recovery_Logs.data=[c.log('mac-flap','deleted',Date.now()-180000),c.log('ethernet-1/2.1','deleted',Date.now()-180000)];const r=evaluate(c);assert.equal(r.criteria.matching_post_isolation_log_clearance,true);assert.equal(r.criteria.quiet_after_clearance_5m,false);assert.equal(c.Variables.verification_continue,true);
});
test('new detection resets clearance even if monitor is OK',()=>{
 const c=context();c.Steps.Verify_Recovery_Logs.data.push(c.log('mac-flap','detected',Date.now()-30000));assert.equal(evaluate(c).criteria.matching_post_isolation_log_clearance,false);
});
test('zero loss needs multiple fresh post-job samples spanning one minute',()=>{
 for(const points of [[[Date.now()-1000,0]],[[Date.now()-700000,0],[Date.now()-650000,0]],[[Date.now()+1000,0]],[[Date.now()-90000,null],[Date.now()-30000,null]],[[Date.now()-90000,0],[Date.now()-30000,33.3]],[[Date.now()-90000,0],[Date.now()-30000,0],[Date.now()-30000,100]]]){const c=context();c.Steps.Verify_Forwarding.series[0].pointlist=points;assert.equal(evaluate(c).criteria.independent_forwarding_zero_loss,false);}
});
test('ambiguous metric series and wrong port state cannot verify recovery',()=>{
 const c=context();c.Steps.Verify_Forwarding.series.push(c.Steps.Verify_Forwarding.series[0]);assert.equal(evaluate(c).recovery_verified,false);
 const d=context();d.Steps.Verify_Interface_Oper.series[0].pointlist.forEach(p=>p[1]=2);assert.equal(evaluate(d).criteria.trusted_ports_up,false);
});
test('expired observation and read failure stop, never relaunch remediation',()=>{
 const c=context();c.Variables.verification_deadline=Date.now()-1;assert.equal(evaluate(c).recovery_verified,false);assert.equal(c.Variables.verification_continue,false);
 const d=context();d.Variables.verification_read_failed=true;assert.equal(evaluate(d).recovery_verified,false);assert.equal(d.Variables.verification_continue,false);
});
test('finalizer and success formatter propagate verified scope and audit evidence',()=>{
 const c=context(),r=evaluate(c);const v=script('Finalize_Recovery_Verification')(c);assert.equal(v.status,'RECOVERY_VERIFIED');c.Steps.Finalize_Recovery_Verification={data:v};const message=script('Format_Recovery_Verified')(c);assert.match(message.slack_text,/Telemetry Recovery Verified/);assert.match(message.slack_text,/does not confirm a physical loop/);assert.equal(message.escalation_required,false);
 c.Steps.Format_Recovery_Verified={data:message};c.Steps.Slack_Recovery_Verified={ts:'test-not-sent'};const out=script('Complete')(c);assert.equal(out.recovery_verified,true);assert.equal(out.success_notification_sent,true);assert.equal(out.escalation_required,false);
});
test('failed verification escalates and delivery failures remain visible',()=>{
 const c=context();c.Steps.Verify_Monitor_State.overall_state='Alert';const r=evaluate(c);c.Steps.Finalize_Recovery_Verification={data:r};const d=script('Stop_And_Escalate')(c);assert.equal(d.escalation_required,true);assert.equal(d.automatic_retry,false);assert.match(d.slack_text,/RECOVERY NOT VERIFIED/);
 c.Steps.Stop_And_Escalate={data:d};c.Steps.Escalation_Delivery_Failed={data:{workflow_result:'ESCALATION_DELIVERY_FAILED',reason:'test'}};assert.equal(script('Complete')(c).workflow_result,'ESCALATION_DELIVERY_FAILED');
});
test('success notification failure retains verified proof but never claims delivery',()=>{
 const c=context();c.Steps.Finalize_Recovery_Verification={data:evaluate(c)};c.Steps.Format_Recovery_Verified={data:script('Format_Recovery_Verified')(c)};c.Steps.Recovery_Notification_Failed={data:script('Recovery_Notification_Failed')(c)};
 const r=script('Complete')(c);assert.equal(r.workflow_result,'RECOVERY_VERIFIED_NOTIFICATION_FAILED');assert.equal(r.recovery_verified,true);assert.equal(r.success_notification_sent,false);
});
test('all Slack actions retain Operational Conditions top-level channel behavior',()=>{
 for(const s of spec.steps.filter(s=>s.actionId.includes('slack'))){assert.equal(s.parameters.find(p=>p.name==='channel').value,'#datadog-automation');assert.equal(s.parameters.some(p=>p.name==='sendInThread'),false);}
});
