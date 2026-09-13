"""Clearly labeled synthetic stdio server. Never contacts OpenAI or reads credentials."""
import json
import os
import sys
import time
mode=sys.argv[1] if len(sys.argv)>1 else 'normal'
initialized=False
for line in sys.stdin:
    msg=json.loads(line)
    method=msg['method']
    if method=='initialized':
        initialized=True
        continue
    if method!='initialize' and not initialized:
        sys.exit(3)
    if mode=='exit': sys.exit(1)
    if mode=='timeout': time.sleep(5)
    if mode=='invalid':
        print('not json',flush=True)
        continue
    if mode=='oversize':
        print('x'*1100000,flush=True)
        continue
    if mode=='error':
        print(json.dumps({'id':msg['id'],'error':{'code':-1,'message':'secret must never be logged','data':{'retryAfterSeconds':90}}}),flush=True)
        continue
    print(json.dumps({'method':'irrelevant/notification','params':{}}),flush=True)
    print(json.dumps({'id':msg['id']-1,'result':{'outdated':True}}),flush=True)
    result={}
    if method=='account/read': result={'account':{'type':'chatgpt','email':'fixture@example.invalid'}}
    if method=='account/rateLimits/read':
        result={'accountId':'fixture-account','rateLimits':{},'rateLimitsByLimitId':{'codex':{
          'primary':{'usedPercent':1,'windowDurationMins':10080,'resetsAt':int(os.environ.get('PACE_TEST_RESET', int(time.time())+500000))}}}}
    print(json.dumps({'id':msg['id'],'result':result}),flush=True)
