#!/usr/bin/env python3
"""
Generators of streamlit apps. Like cybertron generating various types of streamlit apps.
Workflow instruction file can be provided as input file or user input
"""
import json
import os
import re
import sys
import ast
import argparse
import configparser
import importlib
import subprocess
import streamlit as st

sys.path.append(os.getcwd())


def fire_cmd(cmd):
    print(">>>", cmd)
    try:
        sp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = sp.communicate()
        print(stdout, stderr)
        err = stderr.decode("utf-8")
        if err:
            print("Error>>", err)
            return err
        out = stdout.decode("utf-8")
        print("Output >>", out)
        return out
    except Exception as e:
        print("Exception:", cmd, "\n", str(e))


def preprocess(wobj, replace=True):
    def dollar_replace(match):
        match = match.group()
        key = match.replace('$', '')
        ret = st.session_state[key] if key in st.session_state else ''
        if isinstance(ret, str):
            return ret
        return json.dumps(ret).replace('"', "'")

    def dollar_construct(match):
        match = match.group()
        key = match.replace('$', '')
        return "st.session_state['%s']" % key

    json_convert = True
    if isinstance(wobj, str):
        json_convert = False
    instr = json.dumps(wobj) if json_convert else wobj
    print("Input:", instr)
    if replace:
        out = re.sub(r'\$\w+', dollar_replace, instr)
    else:
        out = re.sub(r'\$\w+', dollar_construct, instr)
    print("Out:", out)
    return json.loads(out) if json_convert else out


def cmd_exec(cmd):
    print("Cmd Exec:", cmd)
    if isinstance(cmd, str):
        return fire_cmd(cmd)
    module = ""
    if "ui" in cmd:
        if isinstance(cmd["ui"], list):
            cmd = {"package": "lib.uibuilder", "call": "uibuilder", "param_type": "json", "param": {"main": cmd["ui"]}}
        else:
            cmd = {"package": "lib.uibuilder", "call": "uibuilder", "param_type": "json", "param": {"main":[cmd["ui"]]}}
        print("UI:", cmd)
    if "package" in cmd:
        module = importlib.import_module(cmd["package"])
    param = ""
    if "param" in cmd:
        param = preprocess(cmd["param"], replace=True)
        if isinstance(param, dict):
            for p in param:
                if param[p] in st.session_state:
                    param[p] = st.session_state[param[p]]
    if "call" in cmd:
        func = getattr(module, cmd["call"])
        if isinstance(param, dict) and "param_type" not in cmd:
            return func(**param)
        else:
            if param:
                return func(param)
            return func()
    if "py" in cmd:
        return exec(compile(ast.parse(preprocess(cmd["py"], replace=False)), filename="<ast>", mode="exec"))
    if "sh" in cmd:
        return fire_cmd(cmd["sh"])


class ExtendedEnvInterpolation(configparser.ExtendedInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_get(self, parser, section, option, value, defaults):
        value = os.path.expandvars(value)
        # print(value)
        return super().before_get(parser, section, option, value, defaults)


def config_to_dict(app_config):
    config = {}
    for section in app_config.sections():
        config[section] = {}
        for key in app_config[section]:
            config[section][key] = app_config[section][key]
    return config


def check_key(key):
    if key not in st.session_state:
        return False
    if isinstance(st.session_state[key], list):
        return True if len(st.session_state[key]) > 0 else False
    if st.session_state[key]:
        return True
    return False


def checkifkey(stage):
    if "ifkey" in stage:
        if not check_key(stage["ifkey"]):
            # if witem[stage]["ifkey"] not in st.session_state or not st.session_state[witem[stage]["ifkey"]]:
            print(stage["ifkey"], "Not Set. Continuing...")
            return False
        return True
    if "ifkeyall" in stage:
        for k in stage["ifkeyall"]:
            if not check_key(k):
                print(k, "Not Set among ifkeyall", stage["ifkeyall"], ". Continuing...")
                return False
    if "ifkeyany" in stage:
        for k in stage["ifkeyany"]:
            if check_key(k):
                return True
        print("None Set among ifkeyany", stage["ifkeyany"], ". Continuing...")
        return False
    return True


def process_workflow(wobj):
    for stage in wobj:
        print("*" * 50, stage)
        print(wobj[stage])
        if not checkifkey(wobj[stage]):
            continue
        if "exec" in wobj[stage]:
            print("Exec", wobj[stage]["exec"])
            if isinstance(wobj[stage]["exec"], list):
                for cmd in wobj[stage]["exec"]:
                    out = cmd_exec(cmd)
                    print("Command:", cmd, "\n", "Output:", out)
                    if out is not None:
                        if "key" in cmd:
                            st.session_state[cmd["key"]] = out
            else:
                out = cmd_exec(wobj[stage]["exec"])
                if out is not None:
                    st.session_state[wobj[stage]["exec"]["key"]] = out


def start_streambot(workflow, global_config):
    print("start_streamlitron:", workflow, global_config)
    if workflow != '':
        st.session_state["workflow"] = workflow
    if "use_workflow" in st.session_state:
        st.session_state["workflow"] = st.session_state["use_workflow"]
    workflow_placeholder = "Select Workflow"
    if "workflow" not in st.session_state or st.session_state["workflow"] == workflow_placeholder:
        st.header("Welcome to Streamlitron!")
        if "workflows" not in st.session_state:
            st.session_state["workflows"] = []
            folder = global_config["GLOBAL"]["workflow_dir"]
            for file in sorted(os.listdir(folder)):
                fpath = os.path.join(folder, file)
                if os.path.isfile(fpath) and fpath.endswith(".json"):
                    st.session_state["workflows"].append(os.path.join(folder, file))
        cmd_exec({"package": "lib.uibuilder", "call": "uibuilder", "param_type": "json",
                  "param": {"main": [{"st.selectbox": {"key": "use_workflow",
                                                       "options": [workflow_placeholder] + st.session_state[
                                                           "workflows"],
                                                       "label": "Select Workflow", "label_visibility": "collapsed"}}]}})

    if "workflow" in st.session_state and st.session_state["workflow"] != workflow_placeholder:
        with open(st.session_state["workflow"]) as fh:
            wobj = json.load(fh)
            process_workflow(wobj)


def parse_input():
    desc = """
    Usage: streamlit run %(prog)s [options] script 
    """

    examples = """
    eg:
    streamlit run %(prog)s
    streamlit run %(prog)s -- -w workflows/model_deploy.json
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=desc,
                                     epilog=examples)
    parser.add_argument("-w", "--workflow_file", help="Pipeline workflow File", default='', required=False)
    return parser.parse_args()


def main():
    args = parse_input()

    global_parser = configparser.ConfigParser(interpolation=ExtendedEnvInterpolation())
    global_parser.read("config/global.ini")
    global_config = config_to_dict(global_parser)
    start_streambot(args.workflow_file, global_config)


if __name__ == '__main__':
    main()
