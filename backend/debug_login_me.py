import urllib.request, json, traceback, sys
url='http://127.0.0.1:8000/api/v1/auth/login'
creds={'email':'admin@osagaming.com','password':'password'}
try:
    data=json.dumps(creds).encode()
    req=urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    r=urllib.request.urlopen(req)
    body=r.read().decode()
    print('LOGIN_STATUS', r.getcode())
    obj=json.loads(body)
    tok=obj.get('access_token')
    if not tok:
        print('no token')
        sys.exit(1)
    req2=urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/me', headers={'Authorization':'Bearer '+tok})
    r2=urllib.request.urlopen(req2)
    print('ME_STATUS', r2.getcode())
    print(r2.read().decode())
except Exception:
    traceback.print_exc()
    sys.exit(1)
