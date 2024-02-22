#!/usr/bin/env python3
"""
Tool to export eval data in standarized csv format
"""
import sys
import argparse

import pandas as pd
from lib import evaldata_manager as edm

root = "./mnt/eval_data/eval_run_results"


def dump(models, runspecs):
    av_models, av_runspecs = edm.get_model_runspec_map(root)
    models = models.split(',') if models else av_models
    runspecs = runspecs.split(',') if runspecs else av_runspecs
    outcome_data, record_data = edm.load_data_from_files(root, models, runspecs)
    edm.convert_runspec_to_df(outcome_data)
    for runspec in outcome_data:
        outcome_data[runspec].to_csv("eval_summary/%s.csv" % runspec)
    denormalized_recorddata = edm.denormalize_records_data(record_data)
    edm.convert_runspec_to_df(denormalized_recorddata)
    for runspec in denormalized_recorddata:
        denormalized_recorddata[runspec].to_csv("eval_records/%s.csv" % runspec)
    print("Data Dumping Done")


def view(req_models, req_runspecs):
    models, runspecs = edm.get_model_runspec_map(root)
    print("Models:", len(models))
    if req_models:
        for req_model in req_models:
            print("Model %s:" % req_model, "Runspecs:", models[req_model])
    else:
        print("Sample Model %s:" % runspecs["runspec_multi_turn_questions"][:2],
              "Runspecs in Model [NOW_LLM_llama13b_1115_nopair_cdpo_005] :",
              models["NOW_LLM_llama13b_1115_nopair_cdpo_005"])
    print("RunSpecs:", len(runspecs))
    if req_runspecs:
        for req_runspec in req_runspecs.split(','):
            print("Runspecs %s:" % req_runspec, runspecs[req_runspec])
    else:
        print("Sample Runspecs %s:" % "runspec_multi_turn_questions", runspecs["runspec_multi_turn_questions"][:2])


def parse_input():
    desc = """
    Usage: %(prog)s <action>
    Allowed actions: dump view
    """
    examples = """
    eg: %(prog)s dump
    %(prog)s -r runspec_multi_turn_questions view
    %(prog)s -r runspec_multi_turn_questions dump
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=desc,
                                     epilog=examples)
    parser.add_argument('-m', '--models', help='CSV models. Default is all', default="")
    parser.add_argument('-r', '--runspec', help='CSV runspecs. Default is all', default="")
    parser.add_argument("action", help="Action: dump or view")
    if len(sys.argv) < 2:
        parser.parse_args(['-h'])
    return parser.parse_args()


def main():
    args = parse_input()
    print(args)
    if args.action == "view":
        view(args.models, args.runspec)
    elif args.action == "dump":
        dump(args.models, args.runspec)


if __name__ == "__main__":
    main()