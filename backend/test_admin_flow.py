import requests
import json

admin_openid = 'test_admin_openid_12345'
user_openid = 'dev_openid_d9a480d2238a47d1'

print('CHECK ADMIN...')
resp = requests.get('http://127.0.0.1:5000/api/miniprogram/admin/check', headers={'X-WX-Openid': admin_openid})
print(resp.status_code)
print(resp.text)

print('\nGRANT MEMBERSHIP...')
body = {'targetOpenid': user_openid, 'memberType': 'monthly', 'days': 30}
resp = requests.post('http://127.0.0.1:5000/api/miniprogram/admin/grant-membership', headers={'X-WX-Openid': admin_openid, 'Content-Type': 'application/json'}, json=body)
print(resp.status_code)
print(resp.text)

print('\nGET USER INFO...')
resp = requests.get('http://127.0.0.1:5000/api/miniprogram/user/info', headers={'X-Openid': user_openid})
print(resp.status_code)
print(resp.text)
