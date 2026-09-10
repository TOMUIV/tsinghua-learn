#!/usr/bin/env python3
"""
_config.py — 路径 + 配置 + 凭证集中管理
所有脚本通过 import _config 获取路径/配置/账号密码
凭证存储策略：
- Windows: DPAPI
- Linux: 本地主密钥文件 + Fernet 强加密
"""
import os, json, base64, sys, importlib, stat

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CRED_FILE   = os.path.join(_SKILL_DIR, "credentials.json")
_CONFIG_FILE = os.path.join(_SKILL_DIR, "config.json")
_STATE_FILE  = os.path.join(_SKILL_DIR, "sessions", "learn_session.json")
_FP_FILE     = os.path.join(_SKILL_DIR, "profiles", "learn_fingerprint.json")
_PROFILE_DIR = os.path.join(_SKILL_DIR, "profiles", "learn_profile")
_UPLOAD_DIR  = os.path.join(_SKILL_DIR, "uploads")


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ── 凭据加密工具（Windows DPAPI + Linux Fernet）──────
_DPAPI_AVAILABLE = False
_CRED_PREFIX_DPAPI = "dpapi:"
_CRED_PREFIX_B64 = "b64:"
_CRED_PREFIX_KEYRING = "keyring:"
_CRED_PREFIX_FERNET = "fernet:"
_SECRET_DIR = os.path.join(_SKILL_DIR, "secrets")
_MASTER_KEY_FILE = os.path.join(_SECRET_DIR, "master.key")

if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
        class _DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]
        _crypt32 = ctypes.windll.crypt32
        _kernel32 = ctypes.windll.kernel32
        _CRYPTPROTECT_UI_FORBIDDEN = 0x1
        _DPAPI_AVAILABLE = True
    except Exception:
        pass

def _dpapi_encrypt(plaintext):
    """Windows DPAPI 加密，返回 base64 文本。"""
    if not _DPAPI_AVAILABLE:
        raise RuntimeError("当前平台不支持 DPAPI")
    data_bytes = plaintext.encode()
    data_in = _DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_ubyte)))
    data_out = _DATA_BLOB()
    entropy = _DATA_BLOB()
    if _crypt32.CryptProtectData(ctypes.byref(data_in), "tsinghua-learn", ctypes.byref(entropy),
                                 None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(data_out)):
        raw = ctypes.string_at(data_out.pbData, data_out.cbData)
        _kernel32.LocalFree(data_out.pbData)
        return base64.b64encode(raw).decode()
    return base64.b64encode(plaintext.encode()).decode()


def _dpapi_decrypt(ciphertext):
    """Windows DPAPI 解密（输入为 base64 文本）。"""
    if not _DPAPI_AVAILABLE:
        raise RuntimeError("当前平台不支持 DPAPI")
    try:
        raw = base64.b64decode(ciphertext)
    except Exception:
        return ciphertext
    data_in = _DATA_BLOB(len(raw), ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_ubyte)))
    data_out = _DATA_BLOB()
    entropy = _DATA_BLOB()
    if _crypt32.CryptUnprotectData(ctypes.byref(data_in), None, ctypes.byref(entropy),
                                   None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(data_out)):
        result = ctypes.string_at(data_out.pbData, data_out.cbData).decode()
        _kernel32.LocalFree(data_out.pbData)
        return result
    return ciphertext


def _b64_encrypt(plaintext):
    return base64.b64encode(plaintext.encode()).decode()

def _b64_decrypt(ciphertext):
    try:
        return base64.b64decode(ciphertext).decode()
    except Exception:
        return ciphertext

def _load_fernet_class():
    try:
        return importlib.import_module("cryptography.fernet").Fernet
    except Exception as e:
        raise RuntimeError(f"缺少 cryptography 依赖，无法使用 Linux 凭据加密: {e}")

def _check_linux_secret_permissions(path):
    if not sys.platform.startswith("linux"):
        return
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o077:
        raise RuntimeError(f"密钥文件权限过宽（当前 {oct(mode)}），请设置为 600: {path}")

def _read_or_create_linux_master_key(create):
    if not sys.platform.startswith("linux"):
        raise RuntimeError("仅 Linux 平台支持 Fernet 主密钥文件")

    Fernet = _load_fernet_class()
    if os.path.exists(_MASTER_KEY_FILE):
        _check_linux_secret_permissions(_MASTER_KEY_FILE)
        with open(_MASTER_KEY_FILE, "rb") as f:
            key = f.read().strip()
        if not key:
            raise RuntimeError("主密钥文件为空，请重新初始化凭据")
        return key

    if not create:
        raise RuntimeError("Linux 主密钥不存在，请重新初始化凭据")

    os.makedirs(_SECRET_DIR, exist_ok=True)
    key = Fernet.generate_key()
    with open(_MASTER_KEY_FILE, "wb") as f:
        f.write(key)
    try:
        os.chmod(_MASTER_KEY_FILE, 0o600)
    except Exception as e:
        raise RuntimeError(f"设置主密钥文件权限失败: {e}")
    _check_linux_secret_permissions(_MASTER_KEY_FILE)
    return key

def _fernet_encrypt(plaintext):
    key = _read_or_create_linux_master_key(create=True)
    Fernet = _load_fernet_class()
    token = Fernet(key).encrypt((plaintext or "").encode())
    return token.decode()

def _fernet_decrypt(ciphertext):
    key = _read_or_create_linux_master_key(create=False)
    Fernet = _load_fernet_class()
    try:
        return Fernet(key).decrypt(ciphertext.encode()).decode()
    except Exception:
        raise RuntimeError("Fernet 密文解密失败，请重新初始化凭据")

def encode_cred(s):
    """跨平台编码：Windows 用 DPAPI，Linux 用 Fernet，其他平台回退 base64。"""
    if _DPAPI_AVAILABLE:
        return _CRED_PREFIX_DPAPI + _dpapi_encrypt(s)
    if sys.platform.startswith("linux"):
        return _CRED_PREFIX_FERNET + _fernet_encrypt(s)
    return _CRED_PREFIX_B64 + _b64_encrypt(s)

def decode_cred(s):
    """
    跨平台解码：
    - dpapi: 前缀：仅 Windows 可解密
    - fernet: 前缀：Linux 主密钥文件解密
    - b64: 前缀：跨平台兼容回退
    - 无前缀：兼容旧版本（优先按当前平台策略尝试）
    """
    if not isinstance(s, str):
        return ""

    if s.startswith(_CRED_PREFIX_DPAPI):
        payload = s[len(_CRED_PREFIX_DPAPI):]
        if not _DPAPI_AVAILABLE:
            raise RuntimeError("检测到 Windows DPAPI 凭据，请在当前平台重新初始化凭据")
        return _dpapi_decrypt(payload)

    if s.startswith(_CRED_PREFIX_B64):
        payload = s[len(_CRED_PREFIX_B64):]
        return _b64_decrypt(payload)

    if s.startswith(_CRED_PREFIX_FERNET):
        payload = s[len(_CRED_PREFIX_FERNET):]
        if not sys.platform.startswith("linux"):
            raise RuntimeError("检测到 Linux Fernet 凭据，请在当前平台重新初始化凭据")
        return _fernet_decrypt(payload)

    if s.startswith(_CRED_PREFIX_KEYRING):
        raise RuntimeError("检测到旧版 Linux Keyring 凭据，请重新初始化凭据")

    # 兼容旧格式：Windows 旧版默认写入 DPAPI(base64)
    if _DPAPI_AVAILABLE:
        try:
            return _dpapi_decrypt(s)
        except Exception:
            return _b64_decrypt(s)

    # 非 Windows 旧版数据：尝试按 base64 解码；失败则说明是 DPAPI 密文
    decoded = _b64_decrypt(s)
    if decoded == s and s:
        raise RuntimeError("检测到无法解码的旧凭据，可能来自 Windows DPAPI，请重新初始化凭据")
    return decoded


# ── 配置 ──────────────────────────────────────
_cfg = None
def load_config():
    global _cfg
    if _cfg is not None:
        return _cfg
    if not os.path.exists(_CONFIG_FILE):
        _cfg = {}
    else:
        _cfg = _load_json(_CONFIG_FILE)
    return _cfg

def get_semester():
    """学期从 API 自动检测，此处仅作手动覆盖（可在 config.json 中添加 semester 字段）。"""
    return load_config().get("semester") or ""

_DOWNLOAD_DIR = os.path.join(_SKILL_DIR, "downloads")
def get_download_dir():
    return _DOWNLOAD_DIR


# ── 用户偏好配置 ────────────────────────────
def get_config(key, default=None):
    return load_config().get(key, default)

def auto_mark_read():
    return get_config("auto_mark_read", False)

def confirm_before_cleanup():
    return get_config("confirm_before_cleanup", True)

def confirm_before_download():
    return get_config("confirm_before_download", True)

def is_initialized():
    """检查是否已完成初始化：credentials.json 存在且 4 个字段均非空。"""
    creds = load_credentials()
    required = ["username", "password", "student_id", "name"]
    return all(creds.get(k) for k in required)


# ── 凭证 ──────────────────────────────────────
def load_credentials():
    """返回 dict: username, password, student_id, name（已解密）"""
    if not os.path.exists(_CRED_FILE):
        return {}
    cred = _load_json(_CRED_FILE)
    out = {}
    for k, v in cred.items():
        try:
            out[k] = decode_cred(v)
        except Exception:
            # 跨平台迁移时若旧凭据无法解密，按空值处理，触发重新初始化
            out[k] = ""
    return out

def save_credentials(username, password, student_id="", name=""):
    """写入凭据（Windows: DPAPI；Linux: 主密钥文件 + Fernet）。"""
    data = {
        "username": encode_cred(username),
        "password": encode_cred(password),
        "student_id": encode_cred(student_id),
        "name": encode_cred(name),
    }
    with open(_CRED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_student_id():
    return load_credentials().get("student_id", "")

def get_student_name():
    return load_credentials().get("name", "")

def get_username():
    return load_credentials().get("username", "")


# ── 路径 getter ──────────────────────────────
def get_state_file():
    return _STATE_FILE

def get_fp_file():
    return _FP_FILE

def get_profile_dir():
    return _PROFILE_DIR

def get_skill_dir():
    return _SKILL_DIR

def get_upload_dir():
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    return _UPLOAD_DIR

def get_submissions_log():
    """返回 submissions 日志文件路径。"""
    d = os.path.join(_SKILL_DIR, "submissions")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "submissions_log.json")

def get_download_dir_abs():
    return get_download_dir()
