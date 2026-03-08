import urllib.request
import urllib.error
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    resp = urllib.request.urlopen('https://flossy-backend-422640267680.asia-south1.run.app/health', context=ctx)
    print("STATUS:", resp.getcode())
    print("BODY:", resp.read().decode())
    print("HEADERS:", resp.getheaders())
except urllib.error.HTTPError as e:
    print("ERROR STATUS:", e.code)
    print("ERROR BODY:", e.read().decode())
    print("ERROR HEADERS:", e.headers)
except Exception as e:
    print("EXCEPTION:", str(e))
