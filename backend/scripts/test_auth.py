#!/usr/bin/env python3
"""Простой тест для /api/v1/auth/login и /api/v1/auth/me
Использует стандартную библиотеку (urllib) чтобы не требовать requests.
"""
import json
import urllib.request
import urllib.error

HOST = "http://127.0.0.1:8000"

def post_login(email, password):
    url = f"{HOST}/api/v1/auth/login"
    data = json.dumps({"email": email, "password": password}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode(), resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return None, str(e)

def get_me(token):
    url = f"{HOST}/api/v1/auth/me"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode(), resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return None, str(e)

if __name__ == '__main__':
    email = "admin@osagaming.com"
    password = "password"
    code, body = post_login(email, password)
    print('LOGIN_STATUS', code)
    print(body)
    if code == 200:
        try:
            data = json.loads(body)
            token = data.get('access_token') or data.get('token') or data.get('accessToken')
            if token:
                code2, body2 = get_me(token)
                print('ME_STATUS', code2)
                print(body2)
        except Exception as e:
            print('PARSE_ERROR', e)
