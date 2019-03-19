#!/bin/python
import subprocess
out1 = subprocess.call("nohup redis-server &", shell=True)
out = subprocess.call("nohup python -u main.py > out.log 2>&1 &", shell=True)
