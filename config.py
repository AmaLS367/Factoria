# config.py
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--profile", type=str, default="user-data")
args = parser.parse_args()

USER_DATA_DIR = args.profile
