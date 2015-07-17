import sys, os, json
from time import sleep

secondsToSleep = int(sys.argv[1])

print sys.argv
sys.stdout.flush()

try:
    result = json.loads(sys.argv[4].split('=')[1])
    result['foo'] = result['foo'] + 1
except:
    result = {'foo':1}

sleep(secondsToSleep)

try:
    output = os.fdopen(3, 'w')
    output.write(json.dumps(result))
except: pass
