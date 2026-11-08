"""Add fixed generator start/reset branches to an exported Scenario Controller."""
import argparse
import copy
import json
from pathlib import Path

JS = 'com.datadoghq.datatransformation.func'
HTTP = 'com.datadoghq.http.request'
BASE = 'https://192.168.2.66/api/controller/v2'


def build(source, start_id, stop_id, connection_id, team_id):
    if any(not isinstance(i, int) or i <= 0 or i in [38, 39, 40, 41, 42] for i in [start_id, stop_id]) or start_id == stop_id:
        raise ValueError('Require two distinct, verified generator template IDs')
    spec = copy.deepcopy(source)
    if not any('agentTrigger' in trigger for trigger in spec.get('triggers', [])):
        spec.setdefault('triggers', []).append({'agentTrigger': {'rateLimit': {'count': 6, 'interval': '60s'}}, 'startStepNames': ['Route_Scenario']})
    if any(s['name'].startswith('Network_') for s in spec['steps']):
        raise ValueError('Network branches already exist; start from the saved pre-change controller')
    spec['connectionEnvs'][0]['connections'].append({'label': 'NETWORK_AAP', 'connectionId': connection_id})
    steps = spec['steps']
    route = next(s for s in steps if s['name'] == 'Route_Scenario')
    for edge in route['outboundEdges']:
        if edge['branchName'] in ['mac-flapping', 'reset-mac-flapping']:
            edge['nextStepName'] = 'Network_Configure'
    steps[:] = [s for s in steps if s['name'] not in ['MAC_Flapping_Job_Not_Configured', 'Reset_MAC_Flapping_Job_Not_Configured']]
    for parameter in spec['inputSchema']['parameters']:
        if parameter['name'] == 'scenario':
            parameter['description'] = 'Select a fixed POC scenario. mac-flapping stops the managed generator, restores e1/2 and starts ten minutes of duplicate-MAC traffic. reset-mac-flapping stops that generator, restores e1/2 and verifies forwarding.'
    invalid = next(s for s in steps if s['name'] == 'Notify_Invalid_Scenario')
    for parameter in invalid['parameters']:
        if parameter['name'] == 'text':
            parameter['value'] = parameter['value'].replace(' (job not configured)', '')

    def add(name, action, params, next_name=None, branches=None, fail=True, **kwargs):
        step = {'name': name, 'actionId': action, 'parameters': [{'name': k, 'value': v} for k, v in params.items()], **kwargs}
        if next_name:
            step['outboundEdges'] = [{'branchName': 'main', 'nextStepName': next_name}]
        if branches:
            step['outboundEdges'] = [{'branchName': k, 'nextStepName': v} for k, v in branches.items()]
        if fail and action in [HTTP, JS]:
            step['errorHandlers'] = [{'retryStrategy': {'kind': 'RETRY_STRATEGY_LINEAR', 'linear': {'interval': '5s', 'maxRetries': 0}}, 'fallbackStepName': 'Network_Failed'}]
        steps.append(step)
        return step

    def script(name, body, next_name=None, fail=True):
        return add(name, JS, {'script': body}, next_name, fail=fail)

    def http(name, verb, path, next_name, body=None):
        params = {'verb': verb, 'url': BASE + path, 'requestHeaders': [{'key': 'Content-Type', 'value': ['application/json']}], 'responseParsing': 'json', 'allowExpiredCertificate': True}
        if body is not None:
            params['body'] = body
        return add(name, HTTP, params, next_name, connectionLabel='NETWORK_AAP')

    approved = {'lab_id': 'macflap-v2', 'scenario_approved': True, 'ansible_become': True, 'ansible_become_user': 'root', 'ansible_become_method': 'sudo'}
    plans = {
        'mac-flapping': [
            {'id': stop_id, 'playbook': 'lab-v2/ansible/stop-generator.yml', 'vars': approved, 'state': 'stopped'},
            {'id': 42, 'playbook': 'lab-v2/ansible/restore-b.yml', 'vars': {'lab_id': 'macflap-v2', 'target_interface': 'ethernet-1/2', 'change_approved': True}},
            {'id': start_id, 'playbook': 'lab-v2/ansible/start-generator.yml', 'vars': approved, 'state': 'running'},
        ],
        'reset-mac-flapping': [
            {'id': stop_id, 'playbook': 'lab-v2/ansible/stop-generator.yml', 'vars': approved, 'state': 'stopped'},
            {'id': 42, 'playbook': 'lab-v2/ansible/restore-b.yml', 'vars': {'lab_id': 'macflap-v2', 'target_interface': 'ethernet-1/2', 'change_approved': True}},
            {'id': 41, 'playbook': 'lab-v2/ansible/verify-forwarding.yml', 'vars': {}},
        ],
    }
    script('Network_Configure', "const plans=" + json.dumps(plans) + ";const p=plans[$.Trigger.scenario];if(!p)throw Error('Unsupported network scenario');$.Helpers.setVariable('network_plan',p);$.Helpers.setVariable('network_jobs',[]);$.Helpers.setVariable('execution_backend','AAP');$.Helpers.setVariable('job_action',$.Trigger.scenario);$.Helpers.setVariable('workflow_result','ACTION_RUNNING');$.Helpers.setVariable('network_failure_detail','');return {scenario:$.Trigger.scenario};", 'Network_Read_Linux_Reference')
    http('Network_Read_Linux_Reference', 'GET', '/job_templates/41/', 'Network_Validate_Linux_Reference')
    script('Network_Validate_Linux_Reference', "const r=$.Steps.Network_Read_Linux_Reference,b=r.body||{},creds=b.summary_fields?.credentials||[];if(r.status!==200||b.id!==41||b.project!==37||b.inventory!==7||b.playbook!=='lab-v2/ansible/verify-forwarding.yml'||creds.length!==1||creds[0].kind!=='ssh'||!Number.isInteger(creds[0].id))throw Error('Cannot establish JT41 Linux credential reference');$.Helpers.setVariable('network_linux_credential_id',creds[0].id);return {credential_id:creds[0].id};", 'Network_Notify_Started')
    channel = '#datadog-workflow'

    def slack(name, text, next_name=None):
        return add(name, 'com.datadoghq.slack.send_simple_message', {'channel': channel, 'teamId': team_id, 'text': text}, next_name, fail=False)

    slack('Network_Notify_Started', '━━━━━━━━━━━━━━━━━━━━\n:test_tube: *POC CONTROL · STARTED*\n*Network MAC Flapping Scenario*\n━━━━━━━━━━━━━━━━━━━━\n\n*Scenario:* `{{ Trigger.scenario }}`\n*Environment:* network-aiops\n*Fixed lab:* macflap-v2 · sw1 ethernet-1/2\n\nStop the managed generator first, then restore the fixed port. Trigger starts a bounded ten-minute generator; reset instead verifies Host C → Host A forwarding. Job completion does not itself establish Datadog recovery.\n\n_Next → Controlled AAP execution_', 'Network_0_Configure')

    for i in range(3):
        p = 'Network_' + str(i) + '_'
        after = 'Network_' + str(i + 1) + '_Configure' if i < 2 else 'Network_Complete'
        script(p + 'Configure', f"const c=$.Variables.network_plan[{i}];$.Helpers.setVariable('network_config',c);$.Helpers.setVariable('network_phase',{i});$.Helpers.setVariable('network_job_id',null);$.Helpers.setVariable('network_job_succeeded',false);$.Helpers.setVariable('network_poll',0);$.Helpers.setVariable('network_continue',true);return c;", p + 'Read_Template')
        http(p + 'Read_Template', 'GET', '/job_templates/{{ Variables.network_config.id }}/', p + 'Guard_Template')
        script(p + 'Guard_Template', f"const r=$.Steps.{p}Read_Template,b=r.body||{{}},c=$.Variables.network_config,creds=b.summary_fields?.credentials||[];if(r.status!==200||b.id!==c.id||b.project!==37||b.inventory!==7||b.playbook!==c.playbook||b.job_type!=='run'||b.summary_fields?.user_capabilities?.start!==true||(Object.keys(c.vars).length&&b.ask_variables_on_launch!==true)||(c.state&&(!['','lab_linux'].includes(b.limit)||creds.length!==1||creds[0].id!==$.Variables.network_linux_credential_id)))throw Error('Fixed network template identity, Linux credential, limit or launch permission mismatch');return {{allowed:true}};", p + 'Launch')
        http(p + 'Launch', 'POST', '/job_templates/{{ Variables.network_config.id }}/launch/', p + 'Record_Launch', {'extra_vars': '{{ Variables.network_config.vars }}'})
        script(p + 'Record_Launch', f"const r=$.Steps.{p}Launch,b=r.body||{{}},id=b.id||b.job;$.Helpers.setVariable('network_job_id',id||null);if(id)$.Helpers.setVariable('job_id',String(id));if(r.status!==201||!Number.isInteger(id)||id<=0||Object.keys(b.ignored_fields||{{}}).length)throw Error('Ambiguous launch; preserve ID and do not relaunch');$.Helpers.setVariable('aap_job_template_id',String($.Variables.network_config.id));return {{job_id:id}};", p + 'Poll')
        add(p + 'Poll', 'com.datadoghq.core.whileLoop', {'conditions': [{'comparisonOperator': 'lt', 'leftValue': '{{ Variables.network_poll }}', 'rightValue': 60}, {'comparisonOperator': 'eq', 'leftValue': '{{ Variables.network_continue }}', 'rightValue': True}], 'joinOperator': 'and'}, branches={'main': p + 'Check_Completion', 'loopStart': p + 'Sleep'}, fail=False)
        add(p + 'Sleep', 'com.datadoghq.core.sleep', {'durationSeconds': 10}, p + 'Get_Job', fail=False)
        http(p + 'Get_Job', 'GET', '/jobs/{{ Variables.network_job_id }}/', p + 'Record_Job')
        script(p + 'Record_Job', f"const r=$.Steps.{p}Get_Job,b=r.body||{{}},v=$.Variables,c=v.network_config,fail=reason=>{{$.Helpers.setVariable('network_failure_detail',reason);throw Error(reason);}};if(r.status!==200||b.id!==v.network_job_id||b.job_template!==c.id||b.project!==37||b.inventory!==7||b.playbook!==c.playbook)fail('Network job identity mismatch');const state=b.status,pending=['new','pending','waiting','running'].includes(state);if(!pending&&state!=='successful')fail('Network job failed: '+state);let proof=state==='successful';const a=b.artifacts||{{}},pid=a.macflap_generator_main_pid;if(proof&&(!Number.isFinite(Date.parse(b.started))||!Number.isFinite(Date.parse(b.finished))||Date.parse(b.finished)<Date.parse(b.started)))fail('Missing job completion timestamps');if(proof&&c.state)proof=a.macflap_generator_state===c.state&&a.macflap_lab_id==='macflap-v2'&&a.macflap_generator_service==='network-aiops-mac-flapping.service'&&pid!==null&&pid!==undefined&&Number.isInteger(Number(pid))&&(c.state==='running'?Number(pid)>0:Number(pid)===0);if(state==='successful'&&!proof)fail('Missing generator state artifacts');$.Helpers.setVariable('network_continue',pending);$.Helpers.setVariable('network_job_succeeded',proof);$.Helpers.setVariable('network_poll',Number(v.network_poll||0)+1);if(proof){{const jobs=v.network_jobs||[];jobs[{i}]={{id:b.id,template_id:c.id,status:state,started:b.started,finished:b.finished,artifacts:a}};$.Helpers.setVariable('network_jobs',jobs);}}return {{pending,succeeded:proof}};")
        script(p + 'Check_Completion', "if($.Variables.network_job_succeeded!==true)throw Error('Bounded job observation expired; do not relaunch');return {passed:true};", after)
        script(p + 'Poll_Failed', "$.Helpers.setVariable('network_continue',false);$.Helpers.setVariable('network_job_succeeded',false);if(!$.Variables.network_failure_detail)$.Helpers.setVariable('network_failure_detail','AAP job status read failed; inspect the existing job before retrying.');return {stopped:true};", fail=False)
        for step in steps:
            if step['name'] in [p + 'Sleep', p + 'Get_Job', p + 'Record_Job']:
                step['errorHandlers'] = [{'retryStrategy': {'kind': 'RETRY_STRATEGY_LINEAR', 'linear': {'interval': '5s', 'maxRetries': 0}}, 'fallbackStepName': p + 'Poll_Failed'}]

    script('Network_Complete', "$.Helpers.setVariable('workflow_result','ACTION_SUCCEEDED');$.Helpers.setVariable('job_state','succeeded');$.Helpers.setVariable('raw_job_state','successful');$.Helpers.setVariable('failure_reason','');const reset=$.Trigger.scenario==='reset-mac-flapping',jobs=$.Variables.network_jobs||[];const text='━━━━━━━━━━━━━━━━━━━━\\n:white_check_mark: *POC CONTROL · '+(reset?'RESET JOBS COMPLETED':'ACTIVE')+'*\\n*Network MAC Flapping*\\n━━━━━━━━━━━━━━━━━━━━\\n\\n*Scenario:* `'+$.Trigger.scenario+'`\\n*Environment:* network-aiops\\n*Fixed lab:* macflap-v2 · sw1 ethernet-1/2\\n*AAP jobs:* '+jobs.map(j=>'JT'+j.template_id+'/job'+j.id).join(' → ')+'\\n\\n'+(reset?'The managed generator is stopped, e1/2 restored and Host C → Host A forwarding verified. Job completion does not establish Datadog recovery; review fresh monitor and log evidence.':'The managed duplicate-MAC generator is running with a ten-minute bound. Datadog must independently detect real logs. Any recovery change still requires Slack approval.')+'\\n\\nManually launched terminal generators are outside this managed service.\\n\\n_Next → Datadog observation_';return {scenario:$.Trigger.scenario,jobs,recovery_verified:false,slack_text:text};", 'Network_Notify_Success')
    slack('Network_Notify_Success', '{{ Steps.Network_Complete.data.slack_text }}')
    script('Network_Failed', "$.Helpers.setVariable('workflow_result','NETWORK_SCENARIO_FAILED');$.Helpers.setVariable('failure_reason','Network phase '+String($.Variables.network_phase??'configuration')+' failed or returned incomplete evidence. '+String($.Variables.network_failure_detail||'')+' Inspect current job '+String($.Variables.network_job_id||'none')+' before retrying. No automatic relaunch.');return {scenario:$.Trigger.scenario,jobs:$.Variables.network_jobs||[],last_job_id:$.Variables.network_job_id||null};", 'Network_Notify_Failure', fail=False)
    slack('Network_Notify_Failure', '━━━━━━━━━━━━━━━━━━━━\n:x: *POC CONTROL · EXECUTION FAILED*\n*Network Scenario Stopped*\n━━━━━━━━━━━━━━━━━━━━\n\n*Scenario:* {{ Trigger.scenario }}\n*Environment:* network-aiops\n*Failure:* {{ Variables.failure_reason }}\n\nNo automatic retry or further change. A launched job may still be running; review AAP and the managed generator before another request.')
    phase_positions = {}
    common_positions = {'Network_Configure': (2400, 0), 'Network_Read_Linux_Reference': (2400, 220), 'Network_Validate_Linux_Reference': (2400, 440), 'Network_Notify_Started': (2400, 660), 'Network_Complete': (2400, 3300), 'Network_Notify_Success': (2400, 3520), 'Network_Failed': (4200, 1000), 'Network_Notify_Failure': (4200, 1220)}
    for step in steps:
        if not step['name'].startswith('Network_'):
            continue
        if step['name'].endswith('_Record_Job'):
            parameter = next(p for p in step['parameters'] if p['name'] == 'script')
            parameter['value'] = parameter['value'].replace("fail=reason=>{$.Helpers.setVariable('network_failure_detail',reason);throw Error(reason);}", "fail=reason=>{$.Helpers.setVariable('network_failure_detail',reason);$.Helpers.setVariable('network_continue',false);$.Helpers.setVariable('network_job_succeeded',false);return {pending:false,succeeded:false,reason};}").replace(')fail(', ')return fail(')
        if step['name'] in ['Network_Configure', 'Network_Failed'] or step['name'].endswith('_Poll_Failed'):
            step['readinessGate'] = {'thresholdType': 'ANY'}
        if step['name'] in common_positions:
            x, y = common_positions[step['name']]
        else:
            phase = int(step['name'].split('_')[1])
            position = phase_positions.get(phase, 0)
            x, y = 1800 + phase * 800, 900 + position * 210
            phase_positions[phase] = position + 1
        step['display'] = {'bounds': {'x': x, 'y': y}}
    return spec


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start-id', type=int, required=True)
    parser.add_argument('--stop-id', type=int, required=True)
    parser.add_argument('--connection-id', required=True)
    parser.add_argument('--team-id', required=True)
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding='utf-8-sig'))
    data['spec'] = build(data['spec'], args.start_id, args.stop_id, args.connection_id, args.team_id)
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
