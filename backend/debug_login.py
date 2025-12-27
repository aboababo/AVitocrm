import urllib.request, json, traceback, sys
url='http://127.0.0.1:8000/api/v1/auth/login'
creds={'email':'admin@osagaming.com','password':'password'}
try:
    data=json.dumps(creds).encode()
    req=urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    r=urllib.request.urlopen(req)
    body=r.read().decode()
    print('STATUS', r.getcode())
    print(body)
except Exception:
    traceback.print_exc()
    sys.exit(1)
