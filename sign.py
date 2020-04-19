from base64 import b64encode, b64decode

from Crypto.PublicKey import RSA

import functions

keysize = 2048
(public, private) = functions.newkeys(keysize)
public = RSA.importKey(public)
private = RSA.importKey(private)
signature = b64encode(functions.sign(msg1, private))
verify = functions.verify(msg1, b64decode(signature), public)

print(private.exportKey('PEM'))
print(public.exportKey('PEM'))
print("Signature: " + signature)
print("Verify: %s" % verify)
print functions.verify(msg2, b64decode(signature), public)
