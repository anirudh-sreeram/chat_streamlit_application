#!/usr/bin/env python3

"""
This tool deploys to Element AI toolkit
"""
import json
import os
import sys
import time
import argparse
import subprocess
import pandas as pd
import yaml
import shlex


def fire_cmd(cmd):
    print(">>>", cmd)
    try:
        sp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = sp.communicate()
        print(stdout, stderr)
        err = stderr.decode("utf-8")
        if err:
            print("Error>>", err)
            return False, str(err)
        out = stdout.decode("utf-8")
        print("Output >>", out)
        return True, out
    except Exception as e:
        print("Exception:", cmd,"\n", str(e))
        return False, str(e)


def str2listoflist(cmd_out):
    output = []
    lines = cmd_out.split('\n')
    header_str = lines.pop(0)
    header = header_str.split()
    header_indexes = []
    for h in header:
        header_indexes.append(header_str.find(h))
    output.append(header)
    for line in lines:
        if not line:
            continue
        values = []
        for i in range(len(header_indexes)):
            if i < (len(header_indexes) - 1):
                values.append(line[header_indexes[i]:header_indexes[i+1]-1].strip())
            else:
                values.append(line[header_indexes[i]:].strip())
        output.append(values)
    return output


def listoflist2df(output):
    return pd.DataFrame(output[1:], columns=output[0])


def listoflist2dict(output):
    header = output.pop(0)
    if len(output) == 1:
        content = {}
        for i, item in enumerate(output[0]):
            if i < len(header):
                content[header[i]] = item
            else:
                content[header[-1]] += ' ' + item
        return content
    rows_dict = []
    for row in output:
        row_dict = {}
        for i, item in enumerate(row):
            row_dict[header[i]] = item
        rows_dict.append(row_dict)

    return rows_dict


def get_user():
    ret, out = fire_cmd("eai user get")
    if not ret:
        return {"job": "get_user", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def get_role(account, role_label):
    cmd = "eai role get %s.%s" % (account, role_label)
    ret, out = fire_cmd(cmd)
    if not ret:
        return {"job": "get_role", "status": "Failed", "message": out, "cmd": cmd}
    if "http: 404" in out:
        # Create a new role
        cmd = "eai role new %s.%s" % (account, role_label)
        ret, out = fire_cmd(cmd)
        if not ret:
            return {"job": "new_role", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def get_rolekeys(account, role_label):
    cmd = "eai role key new %s.%s" % (account, role_label)
    ret, out = fire_cmd(cmd)
    if not ret:
        return {"job": "get_role", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def get_rolepolicy(account, role_label):
    cmd = 'eai role policy new {0}.{1} "job:get@$(eai account get --field urn {0})"'.format(account, role_label)
    ret, out = fire_cmd(cmd)
    if not ret:
        return {"job": "get_rolepolicy", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def get_datadirs():
    cmd = "eai data ls"
    ret, out = fire_cmd(cmd)
    if not ret:
        return {"job": "get_datadirs", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def get_datadir(datadir_name):
    datadirs = get_datadirs()
    print("Data Dirs", datadirs)
    datadir = ''
    if datadir_name:
        for dd in datadirs:
            if datadir_name == dd['name']:
                datadir = datadir_name
        if not datadir:
            print("Error::Expected data dir[%s] not found" % datadir_name)
            print("Datadir present", datadirs)
            sys.exit(1)
    else:
        datadir = datadirs[0]['name'] if isinstance(datadirs, list) else datadirs['name']
    return datadir


def create_deployconfig(run_yaml, account, datadir, ymal_config):
    with open(run_yaml, 'r') as file:
        run_config = yaml.safe_load(file)
    print(run_config)
    run_config['data'] = ["%s.%s:/mnt/home" % (account, datadir)]
    if 'yaml_command_modelid' in ymal_config:
        run_config['command'][run_config['command'].index('--model-id') + 1] = ymal_config['yaml_command_modelid']
    if 'yaml_resource_mem' in ymal_config:
        run_config['resources']['mem'] = ymal_config['yaml_resource_mem']
    if 'yaml_resource_cpu' in ymal_config:
        run_config['resources']['cpu'] = ymal_config['yaml_resource_cpu']
    if 'yaml_resource_gpu' in ymal_config:
        run_config['resources']['gpu'] = ymal_config['yaml_resource_gpu']
    if 'yaml_resource_gpu_memory' in ymal_config:
        run_config['resources']['gpuMem'] = ymal_config['yaml_resource_gpu_memory']
    deploy_config = os.path.dirname(run_yaml) + "/deploy_" + os.path.basename(run_yaml)
    with open(deploy_config, 'w') as file:
        yaml.dump(run_config, file)
    return deploy_config


def create_deployconfig_from_stvars(outfile):
    import streamlit as st
    run_config = st.session_state["run.yaml"]
    print("Run Config", run_config)
    run_config['data'] = st.session_state['data'].split('\n')
    for attr in ['name']:
        run_config[attr] = st.session_state[attr]
    for cattr in ["max-input-length", "max-total-tokens"]:
        run_config['command'][run_config['command'].index("--"+cattr)+1] = int(st.session_state["command."+cattr])
    run_config['command'][run_config['command'].index("--model-id") + 1] = st.session_state["command.model-id"]
    for rattr in ["cpu", "gpu", "gpuMem", "mem"]:
        run_config['resources'][rattr] = int(st.session_state["resources." + rattr])
    with open(outfile, 'w') as file:
        yaml.dump(run_config, file)


def start_job(account, model, config):
    cmd = "eai job new -i %s -f %s --account %s" % (model, config, account)
    print("start_job:", cmd)
    ret, out = fire_cmd(cmd)
    if not ret:
        return {"job": "start_job", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def update_job_policy(account, role_label, job_id):
    cmd = "eai role policy new %s.%s job:get@$(eai job get %s --field urn)" % (account, role_label, job_id)
    ret, out = fire_cmd(cmd)
    if not ret:
        return {"job": "update_job_policy", "status": "Failed", "message": out, "cmd": cmd}
    return listoflist2dict(str2listoflist(out))


def get_jobs(account=''):
    cmd="eai job ls"
    if account:
        cmd += ' --account ' + account
    ret, out = fire_cmd(cmd)
    print("Ret:", ret)
    print("Out:", out)
    if not ret:
        return {"job": "get_jobs", "status": "Failed", "message": out, "cmd": cmd}
    if not out.strip():
        return {"job": "get_jobs", "status": "Success", "message": "No Active Jobs", "cmd": cmd}
    df = listoflist2df(str2listoflist(out))
    #return df
    return df[df['state'].isin(["RUNNING", "QUEUING", "QUEUED"])]


def get_endpoints_json(endpoints_file):
    if not endpoints_file:
        return {"job": "update_endpoints", "status": "Failed", "message": "Valid Endpoint needed"}
    if not os.path.isfile(endpoints_file):
        return {"job": "update_endpoints", "status": "Failed", "message": "File[%s] not found" % endpoints_file}
    return json.loads(open(endpoints_file, "r").read())


def get_endpoints(endpoints_file):
    return pd.DataFrame(get_endpoints_json(endpoints_file)).transpose()[["url", "prompt_tags"]]


def update_endpoints(endpoints_file, account=''):
    endpoints_json = get_endpoints_json(endpoints_file)
    endpoints_url = {}
    for ep in endpoints_json:
        endpoints_url[endpoints_json[ep]["url"].replace("-8080.job.console.elementai.com/generate", "")] = ep
    # print("Epoints", endpoints_json)

    df = get_jobs(account)
    records = df.to_dict('records')
    # Clean up endpoints
    # print("\nRecords", records)
    records_url = {}
    for record in records:
        records_url[record["accessUrl"].replace(".job.console.elementai.com", "")] = record
    # print("Current Records:", records_url.keys())

    updated_eps = {}
    # Add new endpoints
    for url in records_url:
        if url not in endpoints_url:
            print("\nNew Endpoint:", url)
            updated_eps[records_url[url]['name']] = \
                {'url': url + '-8080.job.console.elementai.com/generate',
                 'Authorization': 'Bearer 8o30OElfDYV_D6YbbznT0A:GDC2BsXIfSdfjv9iWka3V4MkazpvHfe0cCwXohzbP0Q',
                 'Content-Type': 'application/json', 'formatter': 'dummy_formatter',
                 'chat_formatter': 'dummy_formatter', 'server': 'huggingface_server',
                 'prompt_tags': {'user': '<|user|>\n', 'context': '<|system|>\n', 'robot': '<|assistant|>\n',
                                 'end': '<|end|>\n'},
                 'timeout': 20}
    # Existing endpoints
    for url in endpoints_url:
        print("\nSearching:", url)
        if url not in records_url:
            print("Endpoint", url, "no longer available")
        else:
            print("Endpoint", url, "available as", endpoints_url[url])
            updated_eps[endpoints_url[url]] = endpoints_json[endpoints_url[url]]
    json.dump(updated_eps, open(endpoints_file, 'w'), indent=4)
    return get_endpoints(endpoints_file)


def deploy(role_label, datadir_name, model, run_yaml, ymal_config):
    user = get_user()
    print("User:", user)
    role = get_role(user['account'], role_label)
    print("Role:", role)
    rolekeys = get_rolekeys(user['account'], role_label)
    print("Role Keys:", rolekeys)
    rolepolicy = get_rolepolicy(user['account'], role_label)
    print("Role Policy:", rolepolicy)
    datadir = get_datadir(datadir_name)
    print("DataDir:", datadir)
    deploy_config = create_deployconfig(run_yaml, user['account'], datadir, ymal_config)
    job = start_job(user['account'], model, deploy_config)
    print("Job Started", job)
    updated_policy = update_job_policy(user['account'], role_label, job['id'])
    print("Updated Policy", updated_policy)


def parse_input():
    desc = """
    Usage: %(prog)s [options] model 
    """

    examples = """
    eg:
    python3 %(prog)s ghcr.io/huggingface/text-generation-inference:0.5.0
    python3 %(prog)s -r role_deploy_llm2 ghcr.io/huggingface/text-generation-inference:0.5.0
    python3 %(prog)s -r role_deploy_llm2 -d data2 ghcr.io/huggingface/text-generation-inference:0.5.0
    python3 %(prog)s -r role_deploy_llm2 -yc_mid bigscience/bloomz-560m -yr_mem 32 -yr_cpu 2 -yr_gpu 1 -yr_gpumem 20 ghcr.io/huggingface/text-generation-inference:0.5.0
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=desc,
                                     epilog=examples)

    parser.add_argument('-r', '--role_label', help='Role Label. Default=role_deploy_llm', default="role_deploy_llm")
    parser.add_argument('-d', '--datadir',
                        help="EAI data dir to deploy to. Default=first dir available from `eai data ls`", default='')
    parser.add_argument('-y', '--run_yaml',
                        help="YAML run configuration file. Default=toolkit/configs/run.yaml",
                        default='toolkit/configs/run.yaml')
    parser.add_argument('-yc_mid', '--yaml_command_modelid', help="Model Id Command in YAML run config. Default=''", default='')
    parser.add_argument('-yr_mem', '--yaml_resource_mem', help="Resource Memory. Default=0", default=0, type=int)
    parser.add_argument('-yr_cpu', '--yaml_resource_cpu', help="Resource CPU. Default=0", default=0, type=int)
    parser.add_argument('-yr_gpu', '--yaml_resource_gpu', help="Resource GPU. Default=0", default=0, type=int)
    parser.add_argument('-yr_gpumem', '--yaml_resource_gpu_memory', help="Resource GPU Memory. Default=0", default=0, type=int)

    parser.add_argument('model', help="External Model link")
    if len(sys.argv) < 2:
        parser.parse_args(['-h'])
    return parser.parse_args()


def main():
    start_time = time.time()
    args = parse_input()
    print(args)
    dargs = vars(args)
    ymal_config = {}
    for yc in ['yaml_command_modelid', 'yaml_resource_mem', 'yaml_resource_cpu', 'yaml_resource_gpu', 'yaml_resource_gpu_memory']:
        if dargs[yc]:
            ymal_config[yc] = dargs[yc]
    print(ymal_config)
    deploy(args.role_label, args.datadir, args.model, args.run_yaml, ymal_config)
    print("Time Lapsed = %s secs" % time.strftime("%H:%M:%S", time.gmtime(time.time() - start_time)))


def test_update_endpoints():
    update_endpoints("endpoints/model_serving_endpoints.json", "snow.core_llm.inference01")


if __name__ == '__main__':
    # main()
    test_update_endpoints()
