import urllib.request, urllib.error
req = urllib.request.Request('https://jobdiscovery-api.onrender.com/api/v1/auth/google', method='OPTIONS')
req.add_header('Origin', 'https://job-discovery-six.vercel.app')
req.add_header('Access-Control-Request-Method', 'POST')
try:
  res = urllib.request.urlopen(req)
  print(res.getcode(), res.headers.get('Access-Control-Allow-Origin'))
except urllib.error.HTTPError as e:
  print(e.code, e.headers.get('Access-Control-Allow-Origin'))
