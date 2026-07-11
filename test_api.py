import urllib.request, time
time.sleep(5)
r = urllib.request.urlopen("http://localhost:8000/api/health")
print(r.read().decode())
r2 = urllib.request.urlopen("http://localhost:8000/api/system/info")
print(r2.read().decode())
