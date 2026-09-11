import urllib.request
import json
import os
import sys

base = 'http://127.0.0.1:8000'

def api_post(path, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {'Content-Type': 'application/json'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(base + path, data=data, headers=h, method='POST')
    return json.loads(urllib.request.urlopen(req).read())

def api_get(path):
    req = urllib.request.Request(base + path)
    return json.loads(urllib.request.urlopen(req).read())

# 1. Passport
pdata = api_post('/api/v1/passport/create', {'raw_text': 'Ashwagandha + Brahmi for sleep'})
pid = pdata['id']
print('[PASS] Passport created:', pid[:8])

# 2. Export
edata = api_post('/api/v1/export/dossier', {'passport_id': pid})
print('[PASS] Export:', edata['status'], '|', edata['filename'])
fp = os.path.join('exports', edata['filename'])
assert os.path.exists(fp), 'Export file missing'
print('[PASS] Export file exists:', os.path.getsize(fp), 'bytes')

# 3. FTO
fdata = api_post('/api/v1/fto/check', {'passport_id': pid})
print('[PASS] FTO:', fdata['overall_risk'], '| patents:', len(fdata['similar_patents']))

# 4. Label firewall
ldata = api_post('/api/v1/label/analyze', {'label_text': 'Supports healthy skin and moisturizes'})
print('[PASS] Label:', ldata['overall_status'], '| claims:', len(ldata['claims']))

# 5. Roadmap
rdata = api_get('/api/v1/roadmap/' + pid)
print('[PASS] Roadmap:', rdata['total_phases'], 'phases | next:', rdata['next_action'])

# 6. Patent readiness
stud = api_get('/api/v1/analysis/readiness/' + pid)
print('[PASS] Patent readiness: novelty', stud['novelty_score'], '| overall', stud['overall_readiness'])

# 7. Upload
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = b'--' + boundary.encode() + b'\r\n'
body += b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
body += b'Content-Type: text/plain\r\n\r\n'
body += b'This is a test disclosure document with terms like treat and cure\r\n'
body += b'--' + boundary.encode() + b'--\r\n'
req = urllib.request.Request(
    base + '/api/v1/upload/disclosure-check',
    data=body,
    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
)
udata = json.loads(urllib.request.urlopen(req).read())
print('[PASS] Upload:', udata['status'], '| threats:', len(udata['threats_detected']))

# 8. Chat
cdata = api_post('/api/v1/chat/query', {'question': 'What evidence is missing for regulatory approval?'})
print('[PASS] Chat: sources', len(cdata['sources']), '| confidence', cdata['confidence'])

# 9. Auth
try:
    ad = api_post('/api/v1/auth/signup', {'name': 'E2E Test', 'email': 'e2e@test.com', 'password': 'securepass123'})
    print('[PASS] Auth signup:', ad['user']['email'])
except urllib.error.HTTPError as e:
    if e.code == 400:
        print('[OK] Auth signup: user already exists (re-run)')
    else:
        raise
ldata = api_post('/api/v1/auth/login', {'email': 'e2e@test.com', 'password': 'securepass123'})
print('[PASS] Auth login:', ldata['user']['name'])

print('\nALL ENDPOINT TESTS PASSED')