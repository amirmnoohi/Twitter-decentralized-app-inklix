from Crypto import Random
from Crypto.Hash import SHA512, SHA384, SHA256, SHA, MD5
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

hash = "SHA-256"


def newkeys(keysize):
    random_generator = Random.new().read
    key = RSA.generate(keysize, random_generator)
    private, public = key, key.publickey()
    return public, private


def sign(message, priv_key, hashalg="SHA-256"):
    global hash
    hash = hashalg
    signer = PKCS1_v1_5.new(priv_key)
    if hash == "SHA-512":
        digest = SHA512.new()
    elif hash == "SHA-384":
        digest = SHA384.new()
    elif hash == "SHA-256":
        digest = SHA256.new()
    elif hash == "SHA-1":
        digest = SHA.new()
    else:
        digest = MD5.new()
    digest.update(message)
    return signer.sign(digest)


def verify(message, signature, pub_key):
    signer = PKCS1_v1_5.new(pub_key)
    if hash == "SHA-512":
        digest = SHA512.new()
    elif hash == "SHA-384":
        digest = SHA384.new()
    elif hash == "SHA-256":
        digest = SHA256.new()
    elif hash == "SHA-1":
        digest = SHA.new()
    else:
        digest = MD5.new()
    digest.update(message)
    return signer.verify(digest, signature)
