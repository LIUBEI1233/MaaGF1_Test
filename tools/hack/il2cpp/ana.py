import base64
import hashlib
import time
import gzip
import io

def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def discuz_authcode_decode(string, operation='DECODE', key='', expiry=0):
    """
    Discuz! AuthCode implementation in Python
    :param string: 密文 或 明文
    :param operation: 'DECODE' 解密 或 'ENCODE' 加密
    :param key: 你的 Secret Key
    :param expiry: 过期时间
    """
    ckey_length = 4
    key = md5(key)
    keya = md5(key[:16])
    keyb = md5(key[16:])
    
    if operation == 'DECODE':
        keyc = string[:ckey_length]
    else:
        keyc = md5(str(time.time()))[-ckey_length:]

    cryptkey = keya + md5(keya + keyc)
    key_length = len(cryptkey)

    if operation == 'DECODE':
        try:
            # 少女前线 URL Decode 替换: 这里的 string 是 URL 编码过的 Base64
            # 如果传入的是原始抓包数据，记得先把 %2b 换成 +，%2f 换成 /，%3d 换成 =
            # 或者直接使用 python 的 urllib.parse.unquote
            string = base64.b64decode(string[ckey_length:])
        except:
            return None
    else:
        string = f'{expiry:010d}' + md5(string + keyb)[:16] + string
        string = string.encode('utf-8') # py3 fix

    string_length = len(string)
    result = bytearray(string_length)
    box = list(range(256))
    rndkey = [0] * 256

    for i in range(256):
        rndkey[i] = ord(cryptkey[i % key_length])

    j = 0
    for i in range(256):
        j = (j + box[i] + rndkey[i]) % 256
        box[i], box[j] = box[j], box[i]

    a = 0
    j = 0
    for i in range(string_length):
        a = (a + 1) % 256
        j = (j + box[a]) % 256
        box[a], box[j] = box[j], box[a]
        
        # Python 2/3 compatibility for byte XOR
        byte_val = string[i] if isinstance(string, bytes) else ord(string[i])
        result[i] = byte_val ^ (box[(box[a] + box[j]) % 256])

    if operation == 'DECODE':
        try:
            result_str = result.decode('utf-8')
            if (int(result_str[:10]) == 0 or int(result_str[:10]) - int(time.time()) > 0) and \
               result_str[10:26] == md5(result_str[26:] + keyb)[:16]:
                return result_str[26:]
            else:
                return None
        except:
            return None
    else:
        return keyc + base64.b64encode(result).decode('utf-8').replace('=', '')

# ================= 测试区域 =================

candidate_key  = "D0444EF516D9189DB0D96373C2E58257B28D8ABD"

cipher_text  = "NWED4UkeZWKtX1Xz+3wTgL5bmjzAWRCm2XstjvnrmBq4LldLDqUYsJWtHWNGZNVU/TroC5y8boy0wiDlCWM40bmANuFQshZFd/Iht774FF7ucRWnRp5a774s7MQYtIE4vLEdtEQZWjJuqJFwnZ1iKyfn/QYgLfoR+sfzJmlcOVaq6s7uxpyFFpJ8GjEpatAmauSKr8wCqZalwEJn29EsVL7kMiI9LhDEIlxo/ZCbC1xJg1HYfdEKSbIKy1q2MgpJliWJIpa0fZDLZ+5b8CdHnA1MEST56zAw8e2FEOj4Uw4b2fpz8TtDLmM2ypCaccoTjdIX6h97+27XZOsPvAxmhb6O6J/ShCqPEAsnGl+jI+BIFQT4Q8FrJ2eQBHkNT80VgUi2OZMAQXIFUQk+9vqt/txxxigGlEKLU6NCYZKPzA35vm4jyxLyn6mR4VmChN7B2xLsle32HEVqX8UFd0irsrhPSH+1OjQaaWx3HqBxbgOIf5PY4pQqaecTYqFn2ojjneLhx4HyCxd+wOm6NTjXgPugBhGCucLf8bBRj9Vfpjs68EH5UKOzoht7eZQYV/x9QsYfvi17yEqBfNBJozk3Hg78rz38Wg4t6EH5QZgrwCbIQJ6DSPdgMoqRRfLpAsLqQbcXdStYKrFdev6tRmCE0v8XLMS0cLtZ/Evw1vfqM61o1bPRQtIB09ceopHHyggUDWwwbhmXrXrMCYBadLXI2W49m/BlWIXCe3gqzs4z3/6EzkrHvx7ERtY26kkHqqCaGOu/IiiKxR4IsDTldB/BBIFNH06oJNC1/MQ2fesKYNqFoNFXpOSX4SyarMSLV/zcFBdparpkNQ01NaHr+bhOywk8opQhJuhnFnAOuKxAfbJLAahz5woSGih+xWl8e7dWrCrf+iUaVwb3cYwGNGkW3tIKQedDqBkLIiaURI+LyEaDhPx3Cqae1rC5ataspGUtVhn6FDm+i5BKfp3Zb3Ilw9ekw2OUhjpSQY96/chcdhYyBSI7rW31+xbegUPGugzvgFl093I2iFZ8M9cYAA3mG4wBn0MSg+MOsbhi3TUnFlV/4Wroji3UMp8JDkjqVyVDDE9GF0yE5Nt5L3sMBow7+jlg2m8B6tZwNisJl9yIK9CLfHK6/dWdQq2ptD1sxgM60PktI+LnXd0RmpG6QX9EtqhPD9mfNriWNIZ9p+il+4WDyo2P9Rv0Ah4SMnNmHHnotIljMEoHedp4KRFXLERbLhK1Rrlr1lV0Q374J1dHOWiRWjIZid63YnUPHEsFOmH436PJ7M25qY4fVXhN6FDS34OZjc8uszjRHN/8OujFe3LBjeqcOgxmHMLLt9R3Az7z+SdK2gYmSu30gOy1G+PwvTDtPc81pJcWF05jwD+A4fBPwCgBA/BlH+sN2OdhCQGh5Tv/1vLZqdVnTmJNPlRFNGNJ3v4U9cQF4DgDOzEY+h3aC4HOc/G0gZ5Lrj5fPEUqJPHZDnMofPXKpJhsGTMk6RxRiSbilpy1nBfYaISch8mzz06S4OE955+W5c1O2JOP0UlffNE5sTvNUfk9wOSY4Bd0PPb8mpA12grRq"

# 尝试解密流程
try:
    # 1. 尝试 AuthCode 解密
    decoded_data = discuz_authcode_decode(cipher_text, candidate_key)
    
    if decoded_data:
        print("AuthCode 解密初步成功，尝试 Gzip 解压...")
        # 2. 尝试 Gzip 解压
        # 注意：有时候 Gzip 数据没有头部，或者有额外的头部，可能需要调整切片
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(decoded_data.encode('latin1'))) as f:
                plaintext = f.read()
                print(">>> 成功解密并解压！内容如下：")
                print(plaintext.decode('utf-8'))
        except Exception as e:
            print(f"Gzip 解压失败: {e}")
            print("尝试直接输出解密内容:", decoded_data)
    else:
        print("AuthCode 解密返回空，Key 可能错误。")

except Exception as e:
    print(f"发生错误: {e}")