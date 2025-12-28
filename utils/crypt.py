import json
import base64
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

KEY_HEX = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
key = bytes.fromhex(KEY_HEX)  # 32 bytes → AES-256

def encrypt(data, iv=None):
    """
    模拟 CryptoJS.AES.encrypt 的行为（CBC + PKCS7 + 随机 IV）
    :param data: str or dict/list (JSON-serializable)
    :return: dict with 'ciphertext' and 'iv', both Base64 strings
    """
    # 1. 处理输入数据：对象转 JSON 字符串
    if isinstance(data, (dict, list)):
        plaintext = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    else:
        plaintext = str(data)

    # 2. 转为 bytes
    plaintext_bytes = plaintext.encode('utf-8')

    # 3. 生成随机 16 字节 IV（AES block size）
    if iv is not None:
        # 传进来的是16进制字符串
        iv = bytes.fromhex(iv)
    else:
        iv = os.urandom(16)

    # 4. PKCS7 填充（CryptoJS 默认）
    padded_data = pad(plaintext_bytes, AES.block_size)

    # 5. AES-CBC 加密
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext_bytes = cipher.encrypt(padded_data)

    # 6. 转为 Base64 字符串（与 CryptoJS.toString() 一致）
    ciphertext_b64 = base64.b64encode(ciphertext_bytes).decode('ascii')
    iv_b64 = base64.b64encode(iv).decode('ascii')

    return {
        'ciphertext': ciphertext_b64,
        'iv': iv_b64
    }

# 示例使用
if __name__ == '__main__':
    result = encrypt("SAsaf31412@","25da179e3b0f16290d23f7101b43101e")
    print("Ciphertext:", result['ciphertext'])
    print("IV:", result['iv'])