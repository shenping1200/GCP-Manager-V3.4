# -*- coding: utf-8 -*-

import sys

import os

import json

import requests

import sqlite3

import threading

import random

import time

import re

import string

import secrets

import configparser

import socket

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from urllib.parse import urlparse, parse_qs

from collections import defaultdict, deque

from concurrent.futures import ThreadPoolExecutor, as_completed, Future

from PyQt6.QtWidgets import (

    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,

    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget,

    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,

    QFrame, QSplitter, QGroupBox, QFormLayout, QCheckBox, QRadioButton, QTextEdit, QButtonGroup,

    QSpinBox, QPlainTextEdit

)

from PyQt6.QtCore import Qt, pyqtSignal, QThread, QEvent, QTimer

from PyQt6.QtGui import QColor, QAction, QCursor, QIcon

from PyQt6.QtGui import QClipboard



from google.cloud import compute_v1

from google.api_core.exceptions import GoogleAPIError


APP_ICON_FILE = "app_icon.ico"

APP_USER_MODEL_ID = "xiaolong.gcp.manager.v7.6"


def set_windows_app_user_model_id():

    if sys.platform != "win32":

        return

    try:

        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)

    except Exception:

        pass



# 延迟导入paramiko - 在需要时才导入，避免启动时崩溃
PARAMIKO_AVAILABLE = False

paramiko = None



def check_paramiko():

    """检查并导入paramiko"""

    global PARAMIKO_AVAILABLE, paramiko

    if not PARAMIKO_AVAILABLE:

        try:

            import paramiko
            # Paramiko may log stack traces from internal Transport threads to stderr.
            # In normal operation (instance reboot/delete during connect), this is noisy but not actionable.
            import logging
            for name in ("paramiko", "paramiko.transport", "paramiko.auth_handler", "paramiko.packet"):
                logger = logging.getLogger(name)
                logger.setLevel(logging.CRITICAL)
                logger.propagate = False
            try:
                paramiko.util.logging.getLogger("paramiko").setLevel(logging.CRITICAL)
            except Exception:
                pass

            PARAMIKO_AVAILABLE = True

            return True

        except ImportError:

            PARAMIKO_AVAILABLE = False

            return False

    return True


def check_pysocks():
    """检查PySocks是否安装（SOCKS5代理需要requests[socks]）"""
    try:
        import socks
        return True
    except ImportError:
        return False


# =============================================================================
# 全局常量配置
# =============================================================================

DEFAULT_MACHINE_TYPE = "e2-micro"

DEFAULT_IMAGE_FAMILY = "projects/ubuntu-os-cloud/global/images/family/ubuntu-minimal-2204-lts"

DEFAULT_DISK_TYPE = "pd-standard"

DEFAULT_DISK_SIZE_GB = 30

DEFAULT_NETWORK = "global/networks/default"

DEFAULT_SUBNET = "regions/{region}/subnetworks/default"

NETWORK_TIER = "STANDARD"

MAX_WORKERS = 3

DELETE_TIMEOUT = 300



# SSH执行引擎 v6.9 增强配置

SSH_DEFAULT_KEEPALIVE = 30       # TCP keepalive 间隔秒数，防 NAT 断连

SSH_DEFAULT_CONNECT_TIMEOUT = 15 # SSH 连接超时秒数

SSH_DEFAULT_IDLE_TIMEOUT = 3600   # 命令输出静默超时秒数

SSH_DEFAULT_TOTAL_TIMEOUT = 1800  # 命令总执行时间上限秒

SSH_POLL_INTERVAL = 0.01         # 频道轮询间隔0ms，≈100Hz

SSH_BUF_SIZE = 65536             # 接收缓冲64KB

SSH_SSH_KEY_DIR = os.path.join(os.environ.get('APPDATA', '.'), 'XiaoLong', 'ssh_keys')  # SSH密钥缓存目录



FREE_REGIONS = {

    "us-central1 (爱荷华)": "us-central1",
    "us-east1 (南卡罗来纳)": "us-east1",
    "us-west1 (俄勒冈)": "us-west1"

}



PAID_REGIONS = {

    # 美国 (US)
    "us-central2 (达拉斯)": "us-central2", "us-east2 (俄亥俄)": "us-east2",
    "us-east3 (南卡罗来纳)": "us-east3", "us-east4 (北弗吉尼亚)": "us-east4",
    "us-east5 (俄亥俄)": "us-east5", "us-west2 (洛杉矶)": "us-west2",
    "us-west3 (盐湖城)": "us-west3", "us-west4 (拉斯维加斯)": "us-west4",
    "us-south1 (德克萨斯)": "us-south1",
    # 亚洲 (Asia)
    "asia-east1 (台湾)": "asia-east1", "asia-east2 (香港)": "asia-east2",
    "asia-northeast1 (东京)": "asia-northeast1", "asia-northeast2 (大阪)": "asia-northeast2",
    "asia-northeast3 (首尔)": "asia-northeast3", "asia-south1 (孟买)": "asia-south1",
    "asia-south2 (德里)": "asia-south2", "asia-southeast1 (新加坡)": "asia-southeast1",
    "asia-southeast2 (雅加达)": "asia-southeast2",
    # 欧洲 (Europe)
    "europe-west1 (比利时)": "europe-west1", "europe-west2 (伦敦)": "europe-west2",
    "europe-west3 (法兰克福)": "europe-west3", "europe-west4 (荷兰)": "europe-west4",
    "europe-west6 (苏黎世)": "europe-west6", "europe-west8 (米兰)": "europe-west8",
    "europe-west9 (巴黎)": "europe-west9", "europe-west10 (柏林)": "europe-west10",
    "europe-west12 (都灵)": "europe-west12", "europe-central2 (华沙)": "europe-central2",
    "europe-north1 (芬兰)": "europe-north1", "europe-southwest1 (马德里)": "europe-southwest1",
    # 其他 (Others)
    "australia-southeast1 (悉尼)": "australia-southeast1", "australia-southeast2 (墨尔本)": "australia-southeast2",
    "me-central1 (多哈)": "me-central1", "me-central2 (利雅得)": "me-central2",
    "me-west1 (特拉维夫)": "me-west1", "southamerica-east1 (圣保罗)": "southamerica-east1",
    "southamerica-west1 (圣地亚哥)": "southamerica-west1",
    "northamerica-northeast1 (蒙特利尔)": "northamerica-northeast1",
    "northamerica-northeast2 (多伦多)": "northamerica-northeast2",

}



ZONE_OPTIONS = {

    "us-central1": ["us-central1-a", "us-central1-b", "us-central1-c", "us-central1-f"],

    "us-east1": ["us-east1-b", "us-east1-c", "us-east1-d"],

    "us-west1": ["us-west1-a", "us-west1-b", "us-west1-c"]

}



# 合法代理正则校验

PROXY_REGEX = re.compile(r'^(\d{1,3}\.){3}\d{1,3}:\d{1,5}(:.*){0,2}$')



SUPPORTED_PROXY_FORMATS = [

    "http:IP:PORT:USER:PASS",

    "https:IP:PORT:USER:PASS",

    "socks:IP:PORT:USER:PASS",

    "socks5:IP:PORT:USER:PASS",

    "http://USER:PASS@IP:PORT",

    "https://USER:PASS@IP:PORT",

    "socks://USER:PASS@IP:PORT",

    "socks5://USER:PASS@IP:PORT"

]





def resource_path(relative_path):

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)



def proxy_formats_help_text():

    return "支持的代理格式：\n" + "\n".join(SUPPORTED_PROXY_FORMATS)





def parse_proxy_input(proxy_text, fallback_proxy_type=None, require_protocol=False):

    proxy_text = (proxy_text or "").strip()

    if not proxy_text:

        return {'ok': True, 'empty': True, 'proxy_type': fallback_proxy_type or 'HTTPS', 'proxy_url': ''}



    lower = proxy_text.lower()

    protocol = None

    rest = proxy_text



    scheme_map = {

        'socks5://': 'SOCKS5',

        'socks://': 'SOCKS5',

        'http://': 'HTTPS',

        'https://': 'HTTPS',

        'socks5:': 'SOCKS5',

        'socks:': 'SOCKS5',

        'http:': 'HTTPS',

        'https:': 'HTTPS',

    }



    original_scheme = None  # 记录用户输入的原始协议前缀 http/https/socks5

    for prefix, mapped_type in scheme_map.items():

        if lower.startswith(prefix):

            protocol = mapped_type

            original_scheme = prefix.rstrip(':/')  # 提取原始协议前缀

            rest = proxy_text[len(prefix):]

            break



    if '@' in rest:

        user_pass, host_port = rest.rsplit('@', 1)

        host_parts = host_port.split(':')

        if len(host_parts) < 2 or not host_parts[0] or not host_parts[1]:

            return {'ok': False, 'error': f"无法识别代理类型或地址\n{proxy_formats_help_text()}"}

        ip = host_parts[0].strip()

        port = host_parts[1].strip()

        up_parts = user_pass.split(':')

        if not up_parts or not up_parts[0]:

            return {'ok': False, 'error': f"无法识别代理账号信息\n{proxy_formats_help_text()}"}

        user = up_parts[0].strip()

        password = ':'.join(up_parts[1:]).strip() if len(up_parts) > 1 else ''

    else:

        parts = rest.split(':')

        if protocol is None:

            if require_protocol:

                return {'ok': False, 'error': f"无法识别代理类型，请在代理信息中带上协议前缀\n{proxy_formats_help_text()}"}

            protocol = fallback_proxy_type or 'HTTPS'

        if len(parts) < 4:

            return {'ok': False, 'error': f"代理格式不正确\n{proxy_formats_help_text()}"}

        ip = parts[0].strip()

        port = parts[1].strip()

        user = parts[2].strip()

        password = ':'.join(parts[3:]).strip()



    if not ip or not port or not user:

        return {'ok': False, 'error': f"代理信息不完整\n{proxy_formats_help_text()}"}



    proxy_type = protocol or fallback_proxy_type or 'HTTPS'

    # 根据代理类型和原始输入选择正确协议前缀
    if proxy_type == 'SOCKS5':
        scheme = 'socks5'
    elif original_scheme:
        scheme = original_scheme  # 保留用户输入的 http/https
    else:
        scheme = 'https'  # 无前缀时默认 https（与 HTTPS 类型匹配）

    proxy_url = f"{scheme}://{user}:{password}@{ip}:{port}"

    return {

        'ok': True,

        'empty': False,

        'proxy_type': proxy_type,

        'proxy_url': proxy_url,

        'ip': ip,

        'port': port,

        'user': user,

        'password': password,

        'normalized_input': proxy_text

    }





# =============================================================================

# 配置管理# =============================================================================

class ConfigManager:

    def __init__(self):

        self.config_dir = os.path.join(os.environ.get('APPDATA'), 'XiaoLong')

        self.json_file = os.path.join(self.config_dir, 'nezha_config.json')

        self.ini_file = os.path.join(self.config_dir, 'GCP_Manager_v6.9.ini')

        self.config = configparser.ConfigParser()

        os.makedirs(self.config_dir, exist_ok=True)



    def load_json(self):

        if os.path.exists(self.json_file):

            try:

                with open(self.json_file, 'r', encoding='utf-8') as f:

                    return json.load(f)

            except:

                return {}

        return {}



    def save_json(self, data):

        with open(self.json_file, 'w', encoding='utf-8') as f:

            json.dump(data, f, indent=2, ensure_ascii=False)



    def load_layout(self):

        if os.path.exists(self.ini_file):

            try:

                self.config.read(self.ini_file, encoding='utf-8')

            except:

                pass



    def save_layout(self, data):

        self.config['Layout'] = data

        with open(self.ini_file, 'w', encoding='utf-8') as f:

            self.config.write(f)





# =============================================================================

# 哪吒监控API00%适配你的面板：{"success":true,"data":[...]}# =============================================================================

class NezhaAPI:

    def __init__(self, panel_url, jwt_token):

        self.panel_url = panel_url.rstrip('/')  # 自动去除结尾/

        self.jwt_token = self._parse_token(jwt_token)

        # 会话配置（防卡死
        self.session = requests.Session()

        self.session.timeout = 15

        self.session.headers = {

            "Cookie": f"nz-jwt={self.jwt_token}",

            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",

            "Content-Type": "application/json"

        }



    def _parse_token(self, token_input):

        """解析Token：自动去掉nz-jwt=前缀"""

        if not token_input:

            return ""

        token = token_input.strip()

        return token.split('nz-jwt=')[-1].split(';')[0].strip() if 'nz-jwt=' in token else token



    def get_server_list(self):

        """修复布尔值判断，精准解析你的面板JSON"""

        try:

            # 发送请求
            resp = self.session.get(f"{self.panel_url}/api/v1/server")

            resp.encoding = 'utf-8'



            # 校验状态码

            if resp.status_code != 200:

                return False, f"面板接口返回错误：{resp.status_code}"



            # 解析JSON（你的面板是标准JSON
            data = resp.json()



            # 修复核心问题：兼容success的布尔值类型（True/true
            success_flag = data.get('success')

            # 同时兼容Python布尔值True和JSON字符true"

            if isinstance(data, dict) and (success_flag is True or success_flag == "true"):

                server_list = data.get('data', [])

                return True, server_list

            else:

                return False, f"面板返回success字段异常：{success_flag}"



        except requests.exceptions.ConnectionError:

            return False, "无法连接面板，请检查地址/网络"

        except requests.exceptions.Timeout:

            return False, "面板响应超时5秒）"

        except json.JSONDecodeError:

            return False, "面板返回非标准JSON格式"

        except Exception as e:

            return False, f"未知错误：{str(e)}"





class NezhaFetcher(QThread):

    finished = pyqtSignal(dict, str)



    def __init__(self, panel_url, jwt_token):

        super().__init__()

        self.panel_url = panel_url

        self.jwt_token = jwt_token



    def run(self):

        """精准提取：geoip.ip.ipv4_addr name 映射"""

        try:

            api = NezhaAPI(self.panel_url, self.jwt_token)

            success, server_list = api.get_server_list()



            if not success:

                self.finished.emit({}, str(server_list))

                return



            # 构建IP-名称映射（完全匹配你的面板字段）

            ip_name_map = {}

            for server in server_list:

                # 提取IP：固定路geoip ip ipv4_addr

                ipv4 = server.get('geoip', {}).get('ip', {}).get('ipv4_addr', '').strip()

                # 提取名称：固定字name

                name = server.get('name', '未知服务器').strip()



                # 只保留有效IP

                if ipv4 and re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ipv4):

                    ip_name_map[ipv4] = name



            # 输出调试信息（方便你核对            print(f"匹配到{len(ip_name_map)}台服务器：{ip_name_map}")

            self.finished.emit(ip_name_map, "OK")



        except Exception as e:

            self.finished.emit({}, f"解析失败：{str(e)}")





# =============================================================================

# 数据库（线程安全# =============================================================================

class AccountDB:

    def __init__(self, db_path="accounts.db"):

        self.lock = threading.Lock()

        self.conn = sqlite3.connect(db_path, check_same_thread=False)

        self.create_table()

        self.create_vm_passwords_table()



    def create_table(self):

        with self.lock:

            self.conn.execute("""

                CREATE TABLE IF NOT EXISTS accounts (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    email TEXT, project_id TEXT, key_path TEXT,

                    proxy TEXT DEFAULT '', proxy_type TEXT DEFAULT 'HTTPS'

                )

            """)

            self.conn.commit()



    def create_vm_passwords_table(self):

        with self.lock:

            self.conn.execute("""

                CREATE TABLE IF NOT EXISTS vm_passwords (

                    name TEXT PRIMARY KEY,

                    ip TEXT,

                    password TEXT

                )

            """)

            self.conn.commit()



    def save_vm_password(self, name, ip, password):

        with self.lock:

            self.conn.execute(

                "INSERT OR REPLACE INTO vm_passwords (name, ip, password) VALUES (?, ?, ?)",

                (name, ip, password)

            )

            self.conn.commit()



    def get_vm_password(self, name):

        with self.lock:

            row = self.conn.execute("SELECT password FROM vm_passwords WHERE name=?", (name,)).fetchone()

            return row[0] if row else None



    def get_all_vm_passwords(self):

        with self.lock:

            return self.conn.execute("SELECT name, ip, password FROM vm_passwords").fetchall()



    def add_account(self, email, project_id, key_path, proxy='', proxy_type='HTTPS'):

        with self.lock:

            self.conn.execute(

                "INSERT INTO accounts VALUES (NULL,?,?,?,?,?)",

                (email, project_id, key_path, proxy, proxy_type)

            )

            self.conn.commit()



    def delete_account(self, acc_id):

        with self.lock:

            self.conn.execute("DELETE FROM accounts WHERE id=?", (acc_id,))

            self.conn.commit()



    def update_account(self, acc_id, proxy=None, proxy_type=None):

        with self.lock:

            if proxy is not None:

                self.conn.execute("UPDATE accounts SET proxy=? WHERE id=?", (proxy, acc_id))

            if proxy_type is not None:

                self.conn.execute("UPDATE accounts SET proxy_type=? WHERE id=?", (proxy_type, acc_id))

            self.conn.commit()



    def get_all(self):

        with self.lock:

            return self.conn.execute("SELECT * FROM accounts").fetchall()



    def get_by_id(self, acc_id):

        with self.lock:

            return self.conn.execute("SELECT * FROM accounts WHERE id=?", (acc_id,)).fetchone()





# =============================================================================

# 代理上下文管理器（修复：非法代理自动跳过# =============================================================================

class ProxyEnvContext:

    def __init__(self, proxy_url):

        self.proxy_url = proxy_url

        self.old = {}



    def __enter__(self):

        # 空代非法代理 直接不启

        if not self.proxy_url or len(self.proxy_url) < 5:

            return self

        self.old = {

            'HTTP_PROXY': os.environ.get('HTTP_PROXY'),

            'HTTPS_PROXY': os.environ.get('HTTPS_PROXY'),

            'ALL_PROXY': os.environ.get('ALL_PROXY')

        }

        os.environ['HTTP_PROXY'] = self.proxy_url

        os.environ['HTTPS_PROXY'] = self.proxy_url

        if self.proxy_url.startswith('socks'):

            os.environ['ALL_PROXY'] = self.proxy_url

        return self



    def __exit__(self, *args):

        for k, v in self.old.items():

            if v is None:

                os.environ.pop(k, None)

            else:

                os.environ[k] = v





# =============================================================================

# GCP核心服务（修复：代理强校验，非法代理自动忽略# =============================================================================

class GCPService:

    def __init__(self, key_path, project_id, email, proxy='', proxy_type='HTTPS'):

        self.key_path = key_path

        self.project_id = project_id

        self.email = email

        self.proxy_url = self._parse_proxy_safe(proxy, proxy_type)

        self.instance_client = compute_v1.InstancesClient.from_service_account_json(key_path)

        self.firewall_client = compute_v1.FirewallsClient.from_service_account_json(key_path)

        self.project_client = compute_v1.ProjectsClient.from_service_account_json(key_path)



    # 安全解析代理：统一复用全局解析逻辑

    def _parse_proxy_safe(self, proxy, proxy_type):

        parsed = parse_proxy_input(proxy, fallback_proxy_type=proxy_type, require_protocol=False)

        return parsed.get('proxy_url', '') if parsed.get('ok') else ""



    def _with_proxy(self, func):

        with ProxyEnvContext(self.proxy_url):

            return func()



    def add_ssh_key(self, pub_key):

        def run():

            meta = self.project_client.get(project=self.project_id).common_instance_metadata

            key_line = f"root:{pub_key.strip()}"

            ssh_item = next((i for i in meta.items if i.key.lower() == "ssh-keys"), None)

            if not ssh_item:

                meta.items.append(compute_v1.Items(key="ssh-keys", value=key_line))

            elif key_line not in ssh_item.value:

                ssh_item.value += "\n" + key_line

            self.project_client.set_common_instance_metadata(project=self.project_id, metadata_resource=meta).result()

            return True



        try:

            return self._with_proxy(run), "公钥注入成功"

        except Exception as e:

            return False, str(e)



    def create_instance(self, zone, name, startup_script=""):

        def run():

            firewall_ok, firewall_msg = self.create_open_firewall_rules()

            if not firewall_ok:

                return False, firewall_msg



            disk = compute_v1.AttachedDisk(

                boot=True, auto_delete=True,

                initialize_params=compute_v1.AttachedDiskInitializeParams(

                    source_image=DEFAULT_IMAGE_FAMILY, disk_size_gb=DEFAULT_DISK_SIZE_GB,

                    disk_type=f"zones/{zone}/diskTypes/{DEFAULT_DISK_TYPE}",

                    resource_policies=[]

                )

            )

            nic = compute_v1.NetworkInterface(

                network=DEFAULT_NETWORK, subnetwork=DEFAULT_SUBNET.format(region=zone.rsplit('-', 1)[0]),

                access_configs=[compute_v1.AccessConfig(network_tier=NETWORK_TIER)]

            )

            instance = compute_v1.Instance(

                name=name, machine_type=f"zones/{zone}/machineTypes/{DEFAULT_MACHINE_TYPE}",

                disks=[disk], network_interfaces=[nic],

                tags=compute_v1.Tags(items=["http-server", "https-server"])

            )

            metadata_items = [

                compute_v1.Items(key="google-logging-enabled", value="false"),

                compute_v1.Items(key="google-monitoring-enabled", value="false")

            ]

            if startup_script:

                metadata_items.append(

                    compute_v1.Items(key="startup-script", value=startup_script)

                )

            instance.metadata = compute_v1.Metadata(items=metadata_items)

            self.instance_client.insert(project=self.project_id, zone=zone, instance_resource=instance).result()

            ip = self.instance_client.get(project=self.project_id, zone=zone, instance=name).network_interfaces[

                0].access_configs[0].nat_i_p

            return True, (ip, zone)



        try:

            return self._with_proxy(run)

        except Exception as e:

            return False, "资源耗尽" if "resource_pool_exhausted" in str(e).lower() else str(e)



    def delete_instance(self, zone, name):

        return self._operate(

            lambda: self.instance_client.delete(project=self.project_id, zone=zone.replace('zones/', ''),

                                                instance=name).result(), "删除")



    def start_instance(self, zone, name):

        return self._operate(

            lambda: self.instance_client.start(project=self.project_id, zone=zone.replace('zones/', ''),

                                               instance=name).result(), "启动")



    def stop_instance(self, zone, name):

        return self._operate(lambda: self.instance_client.stop(project=self.project_id, zone=zone.replace('zones/', ''),

                                                               instance=name).result(), "停止")



    def reset_instance(self, zone, name):

        return self._operate(

            lambda: self.instance_client.reset(project=self.project_id, zone=zone.replace('zones/', ''),

                                               instance=name).result(), "重启")



    def _operate(self, func, act):

        try:

            self._with_proxy(func)

            return True, f"{act}成功"

        except Exception as e:

            return False, f"{act}失败：{str(e)}"



    def list_instances(self):

        def run():

            res = []

            for zone, resp in self.instance_client.aggregated_list(project=self.project_id):

                if resp.instances:

                    for inst in resp.instances:

                        if inst.network_interfaces and inst.network_interfaces[0].access_configs:

                            res.append({

                                'name': inst.name,

                                'ip': inst.network_interfaces[0].access_configs[0].nat_i_p,

                                'zone': zone

                            })

            return res



        return self._with_proxy(run)



    def create_open_firewall_rules(self):

        def make_allow_all():

            allow_all = compute_v1.Allowed()

            allow_all.I_p_protocol = "all"

            return allow_all



        def build_ingress_firewall():

            return compute_v1.Firewall(

                name="allow-all-ingress",

                network=DEFAULT_NETWORK,

                direction="INGRESS",

                priority=1000,

                source_ranges=["0.0.0.0/0"],

                allowed=[make_allow_all()]

            )



        def build_egress_firewall():

            return compute_v1.Firewall(

                name="allow-all-egress",

                network=DEFAULT_NETWORK,

                direction="EGRESS",

                priority=1000,

                destination_ranges=["0.0.0.0/0"],

                allowed=[make_allow_all()]

            )



        def upsert_firewall(rule_name, firewall):

            try:

                self.firewall_client.insert(project=self.project_id, firewall_resource=firewall).result()

                return True, f"{rule_name} 创建成功"

            except Exception as e:

                err = str(e)

                if "already exists" not in err.lower():

                    return False, f"{rule_name} 创建失败：{err}"



                try:

                    self.firewall_client.update(

                        project=self.project_id,

                        firewall=rule_name,

                        firewall_resource=firewall

                    ).result()

                    return True, f"{rule_name} 已存在，已按全开放规则更新"

                except Exception as update_err:

                    return False, f"{rule_name} 已存在但更新失败：{str(update_err)}"



        def run():

            ingress_ok, ingress_msg = upsert_firewall("allow-all-ingress", build_ingress_firewall())

            egress_ok, egress_msg = upsert_firewall("allow-all-egress", build_egress_firewall())



            if ingress_ok and egress_ok:

                return True, f"入站+出站全开放防火墙配置完成 | {ingress_msg} | {egress_msg}"



            return False, f"防火墙配置未完全成功 | {ingress_msg} | {egress_msg}"



        try:

            return self._with_proxy(run)

        except Exception as e:

            return False, f"防火墙创建失败：{str(e)}"





# =============================================================================

# 异步线程

# =============================================================================

class InstanceLoader(QThread):

    finished = pyqtSignal(list)

    error = pyqtSignal(str)



    def __init__(self, gcp):

        super().__init__()

        self.gcp = gcp



    def run(self):

        try:

            self.finished.emit(self.gcp.list_instances())

        except Exception as e:

            self.error.emit(str(e))





class InstanceOperator(QThread):

    log = pyqtSignal(str)

    finished = pyqtSignal()



    def __init__(self, gcp, instances, action):

        super().__init__()

        self.gcp = gcp

        self.instances = instances

        self.action = action



    def run(self):

        act_map = {

            'delete': self.gcp.delete_instance,

            'start': self.gcp.start_instance,

            'stop': self.gcp.stop_instance,

            'reset': self.gcp.reset_instance

        }

        func = act_map[self.action]

        action_names = {

            'delete': '删除',

            'start': '启动',

            'stop': '停止',

            'reset': '重启'

        }

        action_name = action_names.get(self.action, self.action)

        for idx, inst in enumerate(self.instances, 1):

            success, msg = func(inst['zone'], inst['name'])

            prefix = ' if success else '

            self.log.emit(f"{prefix} 第{idx}台{action_name}{'成功' if success else '失败'} | {inst['name']} | {msg}")

        self.finished.emit()





# =============================================================================

# 主GUI

# =============================================================================


API_HOST = "127.0.0.1"
API_PORT = 18765
API_VERSION = "v7.6"


class LocalAPIRequestHandler(BaseHTTPRequestHandler):

    server_version = "GCPManagerLocalAPI/7.6"

    def log_message(self, format, *args):
        return

    @property
    def app(self):
        return self.server.app

    def _send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode('utf-8'))

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == '/api/status':
                self._send_json(self.app.api_status())
            elif parsed.path == '/api/accounts':
                self._send_json({'ok': True, 'accounts': self.app.api_accounts()})
            elif parsed.path == '/api/logs':
                since = int((query.get('since') or ['0'])[0])
                limit = int((query.get('limit') or ['200'])[0])
                self._send_json({'ok': True, 'logs': self.app.api_get_logs(since, limit)})
            elif parsed.path == '/api/instances':
                self._send_json({'ok': True, 'instances': self.app.api_instances()})
            elif parsed.path == '/api/tasks':
                self._send_json({'ok': True, 'tasks': self.app.api_tasks_snapshot()})
            elif parsed.path == '/api/automation':
                self._send_json(self.app.api_automation_status())
            elif parsed.path == '/api/task_report':
                self._send_json(self.app.api_task_report())
            else:
                self._send_json({'ok': False, 'error': 'unknown endpoint'}, 404)
        except Exception as exc:
            self._send_json({'ok': False, 'error': str(exc)}, 500)

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            payload = self._read_json()
            if parsed.path == '/api/create':
                self._send_json(self.app.api_enqueue_create(payload))
            elif parsed.path == '/api/refresh':
                self._send_json(self.app.api_enqueue_refresh(payload))
            elif parsed.path == '/api/execute':
                self._send_json(self.app.api_enqueue_execute(payload))
            elif parsed.path == '/api/watch_task':
                self._send_json(self.app.api_set_watch_task(payload))
            elif parsed.path == '/api/automation':
                self._send_json(self.app.api_set_automation(payload))
            elif parsed.path == '/api/automation/stop':
                self._send_json(self.app.api_stop_automation(payload))
            elif parsed.path == '/api/automation/run_existing':
                self._send_json(self.app.api_run_existing_accounts(payload))
            else:
                self._send_json({'ok': False, 'error': 'unknown endpoint'}, 404)
        except Exception as exc:
            self._send_json({'ok': False, 'error': str(exc)}, 500)



class AutoTaskScheduler:

    def __init__(self, app):
        self.app = app
        self.lock = threading.RLock()
        self.queue = deque()
        self.executor = None
        self.enabled = False
        self.template = {}
        self.max_workers = 5
        self.active = 0
        self.seen_account_ids = set()
        self.submitted_account_ids = set()
        self.task_seq = 1

    def configure(self, template):
        template = dict(template or {})
        max_workers = int(template.get('max_workers', 5) or 5)
        self.max_workers = max(1, min(max_workers, 20))
        with self.lock:
            self.template = template
            self.enabled = bool(template.get('enabled', True))
            current_ids = {str(acc[0]) for acc in self.app.db.get_all()}
            if template.get('reset_seen'):
                self.seen_account_ids = set()
                self.submitted_account_ids = set()
            elif not self.seen_account_ids:
                self.seen_account_ids = set(current_ids)
            if self.executor:
                self.executor.shutdown(wait=False, cancel_futures=False)
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='gcp-auto-task')
        self.app.log_signal.emit(f"Auto task configured: enabled={self.enabled}, max_workers={self.max_workers}")
        return self.snapshot()

    def stop(self):
        with self.lock:
            self.enabled = False
            self.queue.clear()
        self.app.log_signal.emit("Auto task stopped")
        return self.snapshot()

    def snapshot(self):
        with self.lock:
            return {
                'ok': True,
                'enabled': self.enabled,
                'max_workers': self.max_workers,
                'queued': len(self.queue),
                'active': self.active,
                'seen_accounts': len(self.seen_account_ids),
                'submitted_accounts': len(self.submitted_account_ids),
                'template': self.app._api_safe_payload(self.template),
            }

    def enqueue_existing(self, account_ids=None):
        accounts = self.app.db.get_all()
        wanted = {str(item) for item in (account_ids or [])}
        added = 0
        for account in accounts:
            if wanted and str(account[0]) not in wanted:
                continue
            if self.enqueue_account(account, reason='manual'):
                added += 1
        self.pump()
        return {'ok': True, 'added': added, 'automation': self.snapshot()}

    def scan_new_accounts(self):
        if not self.enabled:
            return {'ok': True, 'added': 0}
        accounts = self.app.db.get_all()
        added = 0
        current_ids = set()
        with self.lock:
            for account in accounts:
                account_id = str(account[0])
                current_ids.add(account_id)
                if account_id not in self.seen_account_ids:
                    self.seen_account_ids.add(account_id)
                    if self.enqueue_account(account, reason='new_account'):
                        added += 1
            self.seen_account_ids.update(current_ids)
        if added:
            self.app.log_signal.emit(f"Auto task queued {added} new account(s)")
            self.pump()
        return {'ok': True, 'added': added}

    def enqueue_account(self, account, reason='manual'):
        account_id = str(account[0])
        with self.lock:
            if account_id in self.submitted_account_ids and not self.template.get('allow_repeat'):
                return False
            task_id = f"auto-{self.task_seq}"
            self.task_seq += 1
            payload = {
                'task_id': task_id,
                'account_id': account_id,
                'account_email': account[1],
                'project_id': account[2],
                'reason': reason,
            }
            self.queue.append((task_id, account, dict(self.template), payload))
            self.submitted_account_ids.add(account_id)
            self.app._api_register_external_task(task_id, 'auto_create_install', payload)
        return True

    def pump(self):
        with self.lock:
            if not self.executor:
                self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='gcp-auto-task')
            while self.enabled and self.queue and self.active < self.max_workers:
                task_id, account, template, payload = self.queue.popleft()
                self.active += 1
                self.executor.submit(self._run_task_safe, task_id, account, template, payload)

    def _run_task_safe(self, task_id, account, template, payload):
        try:
            self.app._api_update_task(task_id, 'running', 'creating instance')
            result = self.app.run_auto_account_task(account, template, task_id)
            status = 'success' if result.get('ok') else 'failed'
            self.app._api_update_task(task_id, status, result.get('message', ''))
            with self.app.api_lock:
                task = self.app.api_tasks.get(task_id)
                if task is not None:
                    task['result'] = result
        except Exception as exc:
            self.app._api_update_task(task_id, 'failed', str(exc))
            self.app.log_signal.emit(f"Auto task {task_id} failed: {exc}")
        finally:
            with self.lock:
                self.active = max(0, self.active - 1)
            self.pump()

class LocalAPIServer:

    def __init__(self, app, host=API_HOST, port=API_PORT):
        self.app = app
        self.host = host
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        self.httpd = ThreadingHTTPServer((self.host, self.port), LocalAPIRequestHandler)
        self.httpd.app = self.app
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


class GCPManagerApp(QMainWindow):

    log_signal = pyqtSignal(str)

    create_btn_signal = pyqtSignal(bool)

    firewall_btn_signal = pyqtSignal(bool)

    refresh_instances_signal = pyqtSignal()

    api_create_signal = pyqtSignal(dict)

    api_refresh_signal = pyqtSignal(dict)

    api_execute_signal = pyqtSignal(dict)



    exec_result_signal = pyqtSignal(str, bool, str)  # name, success, output

    exec_finished_signal = pyqtSignal()

    def __init__(self):

        super().__init__()

        self.setWindowTitle("GCP批量管理工具v7.6 - 渔夫出品 - Telegram：@yufu220")

        self.setWindowIcon(QIcon(resource_path(APP_ICON_FILE)))

        self.resize(1250, 880)



        self.config = ConfigManager()

        self.config_file = self.config.ini_file  # 布局配置文件路径

        self.db = AccountDB()

        self.ssh_public_key = ""

        self.ssh_key_filename = "未选择公钥"

        self.current_json_path = None

        self.nezha_ip_map = {}

        self.current_instances = []

        self.instance_password_cache = {}
        self.post_create_result_cache = {}

        self.api_lock = threading.Lock()

        self.api_log_seq = 0

        self.api_logs = []

        self.api_tasks = {}

        self.api_next_task_id = 1

        self.api_account_ids = set()

        self.api_watch_task = None

        self.auto_scheduler = AutoTaskScheduler(self)

        self.api_account_snapshot = []

        self.api_instance_snapshot = []

        self.api_server = None

        self._ssh_stop_flag = False



        self.ssh_keepalive = SSH_DEFAULT_KEEPALIVE

        self.ssh_connect_timeout = SSH_DEFAULT_CONNECT_TIMEOUT

        self.ssh_idle_timeout = SSH_DEFAULT_IDLE_TIMEOUT

        self.ssh_total_timeout = SSH_DEFAULT_TOTAL_TIMEOUT



        self.log_signal.connect(self.append_log)

        self.init_ui()

        self.create_btn_signal.connect(self.create_btn.setEnabled)

        self.firewall_btn_signal.connect(self.firewall_btn.setEnabled)

        self.refresh_instances_signal.connect(self.query_instances)

        self.api_create_signal.connect(self.api_handle_create)

        self.api_refresh_signal.connect(self.api_handle_refresh)

        self.api_execute_signal.connect(self.api_handle_execute)

        self.exec_result_signal.connect(self.update_exec_result)

        self.exec_finished_signal.connect(lambda: (self.execute_btn.setEnabled(True), self.stop_btn.setEnabled(False)))

        self.load_layout_config()

        self.load_nezha_config()

        # 从数据库加载已保存的VM密码

        for name, ip, pwd in self.db.get_all_vm_passwords():

            self.instance_password_cache[name] = pwd

        self.api_refresh_snapshots()

        self.api_account_ids = {item['id'] for item in self.api_account_snapshot}

        self.start_local_api_server()

        self.api_account_timer = QTimer(self)

        self.api_account_timer.timeout.connect(self.api_check_new_accounts)

        self.api_account_timer.start(3000)

        self.log_signal.emit("GCP Manager v7.6 started | post-create command enabled | local API enabled")



    def apply_227_style(self):

        self.setStyleSheet("""

            /* ===== 全局基础 ===== */

            QMainWindow, QWidget {

                background: #f0f2f5;

                color: #202124;

                font-size: 13px;

                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;

            }

            QMainWindow {

                background: #eef1f5;

            }



            /* ===== 卡片容器 ===== */

            QFrame {

                background: #ffffff;

                border: 1px solid #e4e7ed;

                border-radius: 10px;

            }



            /* ===== GroupBox ===== */

            QGroupBox {

                background: #f8f9fc;

                border: 1px solid #e8eaef;

                border-radius: 8px;

                margin-top: 12px;

                font-weight: 600;

                font-size: 13px;

                color: #3c4043;

                padding: 16px 12px 12px 12px;

            }

            QGroupBox::title {

                subcontrol-origin: margin;

                left: 12px;

                padding: 2px 8px;

                background: #ffffff;

                border: 1px solid #e8eaef;

                border-radius: 4px;

            }



            /* ===== 标签 ===== */

            QLabel {

                background: transparent;

                border: none;

                color: #3c4043;

            }



            /* ===== 输入& 下拉===== */

            QLineEdit, QComboBox {

                background: #ffffff;

                border: 1.5px solid #dadce0;

                border-radius: 6px;

                padding: 7px 10px;

                font-size: 13px;

                color: #202124;

                selection-background-color: #d2e3fc;

            }

            QLineEdit:focus, QComboBox:focus {

                border: 1.5px solid #1a73e8;

                background: #ffffff;

            }

            QLineEdit:hover, QComboBox:hover {

                border: 1.5px solid #a8c7fa;

            }

            QLineEdit:disabled {

                background: #f1f3f4;

                color: #80868b;

            }

            QComboBox::drop-down {

                border: none;

                padding-right: 8px;

            }

            QComboBox QAbstractItemView {

                border: 1px solid #dadce0;

                border-radius: 6px;

                background: #ffffff;

                selection-background-color: #e8f0fe;

                selection-color: #1a73e8;

                padding: 4px;

            }



            /* ===== 表格 ===== */

            QTableWidget {

                background: #ffffff;

                border: 1px solid #e0e0e0;

                border-radius: 6px;

                gridline-color: #f0f0f0;

                selection-background-color: #e8f0fe;

                selection-color: #202124;

                outline: none;

                font-size: 12.5px;

            }

            QTableWidget::item {

                padding: 4px 8px;

                border-bottom: 1px solid #f5f5f5;

            }

            QTableWidget::item:selected {

                background: #e8f0fe;

                color: #202124;

            }

            QTableWidget QLineEdit {

                border: none;

                background: transparent;

                padding: 0px;

                margin: 0px;

            }

            QHeaderView::section {

                background: #f8f9fa;

                color: #5f6368;

                border: none;

                border-bottom: 2px solid #e8eaed;

                border-right: 1px solid #f0f0f0;

                padding: 8px 6px;

                font-weight: 600;

                font-size: 12px;

            }

            QHeaderView::section:hover {

                background: #eef1f5;

            }



            /* ===== 按钮体系 ===== */

            QPushButton {

                background: #ffffff;

                border: 1.5px solid #dadce0;

                border-radius: 7px;

                padding: 7px 16px;

                font-size: 13px;

                font-weight: 500;

                color: #3c4043;

                min-height: 20px;

            }

            QPushButton:hover {

                background: #f1f3f4;

                border: 1.5px solid #c6c9cd;

            }

            QPushButton:pressed {

                background: #e8eaed;

            }

            QPushButton:disabled {

                color: #9aa0a6;

                background: #f1f3f4;

                border: 1.5px solid #e8eaed;

            }



            /* ===== 主操作按钮（蓝色===== */

            QPushButton#primaryBtn {

                background: #1a73e8;

                color: #ffffff;

                border: none;

                font-weight: 600;

            }

            QPushButton#primaryBtn:hover {

                background: #1557b0;

            }

            QPushButton#primaryBtn:pressed {

                background: #0d47a1;

            }

            QPushButton#primaryBtn:disabled {

                background: #c4d7f5;

                color: #ffffff;

            }



            /* ===== 成功按钮（绿色） ===== */

            QPushButton#successBtn {

                background: #34a853;

                color: #ffffff;

                border: none;

                font-weight: 600;

            }

            QPushButton#successBtn:hover {

                background: #2d8e47;

            }

            QPushButton#successBtn:pressed {

                background: #1e6e33;

            }

            QPushButton#successBtn:disabled {

                background: #b7dfc4;

                color: #ffffff;

            }



            /* ===== 危险按钮（红色） ===== */

            QPushButton#dangerBtn {

                background: #ea4335;

                color: #ffffff;

                border: none;

                font-weight: 600;

            }

            QPushButton#dangerBtn:hover {

                background: #c5221f;

            }

            QPushButton#dangerBtn:pressed {

                background: #a50e0e;

            }

            QPushButton#dangerBtn:disabled {

                background: #f5c8c5;

                color: #ffffff;

            }



            /* ===== 警告按钮（橙色） ===== */

            QPushButton#warningBtn {

                background: #fa7b17;

                color: #ffffff;

                border: none;

                font-weight: 600;

            }

            QPushButton#warningBtn:hover {

                background: #d96b0e;

            }

            QPushButton#warningBtn:pressed {

                background: #b85a0a;

            }

            QPushButton#warningBtn:disabled {

                background: #fad2a8;

                color: #ffffff;

            }



            /* ===== 日志区域 ===== */

            QTextEdit {

                background-color: #1a1d23;

                color: #00ff66;

                border: 1px solid #2d3139;

                border-radius: 8px;

                font-family: "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;

                font-size: 12.5px;

                padding: 10px;

                selection-background-color: #3b4049;

            }

            /* ===== 命令输入框（强制黑底绿字，避免被外部主题覆盖） ===== */
            QTextEdit#commandInput {
                background-color: #1a1d23;
                color: #00ff66;
                border: 1px solid #2d3139;
                border-radius: 8px;
                font-family: "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
                font-size: 12.5px;
                padding: 10px;
                selection-background-color: #3b4049;
            }

            QTextEdit:focus {

                border: 1px solid #4c8bf5;

            }



            /* ===== 滚动===== */

            QScrollBar:vertical {

                background: transparent;

                width: 8px;

                margin: 0;

            }

            QScrollBar::handle:vertical {

                background: #c4c7cc;

                border-radius: 4px;

                min-height: 30px;

            }

            QScrollBar::handle:vertical:hover {

                background: #a8abb0;

            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {

                height: 0;

            }

            QScrollBar:horizontal {

                background: transparent;

                height: 8px;

            }

            QScrollBar::handle:horizontal {

                background: #c4c7cc;

                border-radius: 4px;

                min-width: 30px;

            }

            QScrollBar::handle:horizontal:hover {

                background: #a8abb0;

            }

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {

                width: 0;

            }



            /* ===== RadioButton & CheckBox ===== */

            QRadioButton, QCheckBox {

                spacing: 6px;

                color: #3c4043;

                font-size: 13px;

            }

            QRadioButton::indicator, QCheckBox::indicator {

                width: 16px;

                height: 16px;

            }



            /* ===== Splitter ===== */

            QSplitter::handle {

                background: #e0e3e8;

                margin: 0;

            }

            QSplitter::handle:vertical {

                height: 3px;

            }

            QSplitter::handle:horizontal {

                width: 3px;

            }

            QSplitter::handle:hover {

                background: #1a73e8;

            }



            /* ===== SpinBox ===== */

            QSpinBox {

                background: #ffffff;

                border: 1.5px solid #dadce0;

                border-radius: 6px;

                padding: 4px 6px;

                font-size: 13px;

            }

            QSpinBox:focus {

                border: 1.5px solid #1a73e8;

            }

        """)



    def init_ui(self):

        central = QWidget()

        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        main_layout.setContentsMargins(18, 18, 18, 18)

        main_layout.setSpacing(14)





        self.v_splitter = QSplitter(Qt.Orientation.Vertical)

        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)



        self.init_account_panel()

        self.init_instance_panel()

        self.init_bottom_panel()



        self.v_splitter.addWidget(self.h_splitter)

        main_layout.addWidget(self.v_splitter)

        self.refresh_account_table()

        self.apply_227_style()



    def init_account_panel(self):

        widget = QFrame()
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)
        self.account_drop_widget = widget

        # QFrame now uses global style

        layout = QVBoxLayout(widget)

        layout.setContentsMargins(6, 4, 6, 4)

        layout.setSpacing(4)

        title = QLabel("👤 账号管理")

        title.setStyleSheet("font-size: 12px; font-weight: 700; color: #1a73e8; padding: 2px 0;")

        layout.addWidget(title)



        self.search_edit = QLineEdit()

        self.search_edit.setPlaceholderText("🔍 搜索账号/项目/代理")

        self.search_edit.textChanged.connect(self.filter_accounts)

        layout.addWidget(self.search_edit)



        row = QHBoxLayout()

        self.email_edit = QLineEdit(placeholderText="邮箱")

        self.key_btn = QPushButton("选择JSON密钥")

        self.key_btn.clicked.connect(self.select_json)

        self.proxy_edit = QLineEdit(placeholderText="无需代理留空 | 格式：IP:Port:User:Pass")

        self.proxy_edit.textChanged.connect(self.auto_detect_proxy_type)

        self.proxy_type = QComboBox()

        self.proxy_type.addItems(["HTTPS", "SOCKS5"])

        self.add_btn = QPushButton("添加账号")

        self.add_btn.setObjectName("primaryBtn")

        self.add_btn.clicked.connect(self.add_account)

        row.addWidget(self.email_edit, 2)

        row.addWidget(self.key_btn)

        row.addWidget(QLabel("代理:"))

        row.addWidget(self.proxy_edit)

        row.addWidget(self.proxy_type)

        row.addWidget(self.add_btn)

        layout.addLayout(row)

        self.account_drop_targets = (widget, self.email_edit, self.key_btn, self.proxy_edit, self.proxy_type, self.add_btn)

        for drop_widget in self.account_drop_targets:
            drop_widget.setAcceptDrops(True)
            drop_widget.installEventFilter(self)



        self.account_table = QTableWidget(0, 6)

        self.account_table.setHorizontalHeaderLabels(["选择", "ID", "邮箱", "ProjectID", "代理", "协议"])

        self.account_table.setColumnHidden(1, True)

        self.account_table.verticalHeader().setDefaultSectionSize(28)

        self.account_table.itemChanged.connect(self.on_account_edit)

        self.account_table.cellDoubleClicked.connect(self.on_account_table_double_click)

        self.account_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)

        # 弱化单元格编辑框，保留编辑功能但尽量贴近原单元格外观
        self.account_table.setStyleSheet(
            "QTableWidget QLineEdit { "
            "border: none; "
            "background: transparent; "
            "padding: 0px; "
            "margin: 0px; "
            "selection-background-color: transparent; "
            "outline: none; "
            "}"
            "QTableWidget QLineEdit:focus { "
            "border: none; "
            "background: transparent; "
            "outline: none; "
            "}"
        )

        layout.addWidget(self.account_table)



        self.query_btn = QPushButton("🔍查询选中账号实例")

        self.query_btn.setObjectName("primaryBtn")

        self.query_btn.clicked.connect(self.query_instances)

        self.firewall_btn = QPushButton("🔥 一键全开防火墙")

        self.firewall_btn.setObjectName("warningBtn")

        self.firewall_btn.clicked.connect(self.open_firewall)



        row = QHBoxLayout()

        self.select_all_btn = QPushButton("✅ 全选/反选")

        self.select_all_btn.setObjectName("warningBtn")

        self.select_all_btn.clicked.connect(self.toggle_select_all)

        self.batch_import_btn = QPushButton("📂 批量导入")

        self.batch_import_btn.setObjectName("primaryBtn")

        self.batch_import_btn.clicked.connect(self.batch_import)

        row.addWidget(self.select_all_btn, 1)

        row.addWidget(self.batch_import_btn, 1)

        row.addWidget(self.query_btn, 1)

        row.addWidget(self.firewall_btn, 1)

        self.del_account_btn = QPushButton("🗑删除选中账号")

        self.del_account_btn.setObjectName("dangerBtn")

        self.del_account_btn.clicked.connect(self.delete_selected_account)

        row.addWidget(self.del_account_btn, 1)

        layout.addLayout(row)



        self.h_splitter.addWidget(widget)



    def init_instance_panel(self):

        frame = QFrame()

        # QFrame now uses global style

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(6, 4, 6, 4)

        layout.setSpacing(4)



        title = QLabel("📋 实例列表 · 哪吒监控")

        title.setStyleSheet("font-size: 12px; font-weight: 700; color: #1a73e8; padding: 2px 0;")

        layout.addWidget(title)



        url_row = QHBoxLayout()

        url_row.setSpacing(4)

        url_label = QLabel("面板地址:")

        url_label.setFixedWidth(60)

        self.nezha_url = QLineEdit(placeholderText="面板地址 如：https://nezha.example.com")

        self.nezha_save = QPushButton("保存")

        self.nezha_save.setObjectName("primaryBtn")

        self.nezha_save.clicked.connect(self.save_nezha)

        self.nezha_refresh = QPushButton("刷新")

        self.nezha_refresh.clicked.connect(self.fetch_nezha)

        self.nezha_test = QPushButton("测试")

        self.nezha_test.clicked.connect(self.test_nezha)

        url_row.addWidget(url_label)

        url_row.addWidget(self.nezha_url, 1)

        url_row.addWidget(self.nezha_save)

        url_row.addWidget(self.nezha_refresh)

        url_row.addWidget(self.nezha_test)

        layout.addLayout(url_row)



        token_row = QHBoxLayout()

        token_row.setSpacing(4)

        token_label = QLabel("Token:")

        token_label.setFixedWidth(60)

        self.nezha_token = QLineEdit(placeholderText="Token")

        token_row.addWidget(token_label)

        token_row.addWidget(self.nezha_token, 1)

        layout.addLayout(token_row)



        self.instances_table = QTableWidget(0, 6)

        self.instances_table.verticalHeader().setDefaultSectionSize(28)

        self.instances_table.setHorizontalHeaderLabels(["实例名称", "IP", "可用性", "监控名称", "Root密码", "执行结果"])

        self.instances_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.instances_table.cellDoubleClicked.connect(self.on_instance_table_double_click)

        self.instances_table.itemChanged.connect(self.on_instance_table_edit)

        self.instances_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)

        # 弱化单元格编辑框，保留编辑功能但尽量贴近原单元格外观
        self.instances_table.setStyleSheet(
            "QTableWidget QLineEdit { "
            "border: none; "
            "background: transparent; "
            "padding: 0px; "
            "margin: 0px; "
            "selection-background-color: transparent; "
            "outline: none; "
            "}"
            "QTableWidget QLineEdit:focus { "
            "border: none; "
            "background: transparent; "
            "outline: none; "
            "}"
        )

        layout.addWidget(self.instances_table)








        btn_row = QHBoxLayout()

        self.del_inst_btn = QPushButton("🗑删除实例")

        self.del_inst_btn.setObjectName("dangerBtn")

        self.start_inst_btn = QPushButton("▶️ 启动实例")

        self.start_inst_btn.setObjectName("successBtn")

        self.stop_inst_btn = QPushButton("⏹️ 停止实例")

        self.stop_inst_btn.setObjectName("warningBtn")

        self.reset_inst_btn = QPushButton("🔄 重启实例")

        self.reset_inst_btn.setObjectName("warningBtn")

        self.del_inst_btn.clicked.connect(lambda: self.operate_instances('delete'))

        self.start_inst_btn.clicked.connect(lambda: self.operate_instances('start'))

        self.stop_inst_btn.clicked.connect(lambda: self.operate_instances('stop'))

        self.reset_inst_btn.clicked.connect(lambda: self.operate_instances('reset'))

        for btn in [self.del_inst_btn, self.start_inst_btn, self.stop_inst_btn, self.reset_inst_btn]:

            btn.setEnabled(False)

        btn_row.addWidget(self.del_inst_btn)

        btn_row.addWidget(self.start_inst_btn)

        btn_row.addWidget(self.stop_inst_btn)

        btn_row.addWidget(self.reset_inst_btn)

        layout.addLayout(btn_row)



        self.h_splitter.addWidget(frame)

        self.h_splitter.setStretchFactor(0, 1)

        self.h_splitter.setStretchFactor(1, 2)



    def init_bottom_panel(self):

        bottom_frame = QFrame()

        # QFrame now uses global style

        bottom_layout = QVBoxLayout(bottom_frame)

        bottom_layout.setContentsMargins(6, 4, 6, 4)

        bottom_layout.setSpacing(4)



        create_frame = QFrame()

                # QFrame now uses global style

        create_layout = QVBoxLayout(create_frame)

        create_layout.setContentsMargins(4, 1, 4, 1)

        create_layout.setSpacing(2)



        region_row = QHBoxLayout()

        region_row.setSpacing(2)

        self.free_radio = QRadioButton("🆓 免费", checked=True)

        self.paid_radio = QRadioButton("💰 付费")

        self.free_radio.toggled.connect(self.update_regions)

        self.region_box = QComboBox()

        self.count_edit = QLineEdit("1", placeholderText="数量")

        self.count_edit.setMaximumWidth(70)

        self.pubkey_btn = QPushButton("上传SSH公钥")

        self.pubkey_btn.setObjectName("primaryBtn")

        self.pubkey_btn.clicked.connect(self.upload_pubkey)

        self.pubkey_label = QLabel("未选择公钥")

        self.pubkey_label.setStyleSheet("color: #0066cc; font-weight: bold;")

        self.create_btn = QPushButton("开始部署")

        self.create_btn.setObjectName("successBtn")

        self.create_btn.setMinimumHeight(28)

        self.create_btn.clicked.connect(self.start_create)



        region_row.addWidget(self.free_radio)

        region_row.addWidget(self.paid_radio)

        region_row.addWidget(QLabel("区域:"))

        region_row.addWidget(self.region_box, 1)

        region_row.addWidget(QLabel("数量:"))

        region_row.addWidget(self.count_edit)

        region_row.addWidget(self.pubkey_btn)

        region_row.addWidget(self.pubkey_label, 1)

        region_row.addWidget(self.create_btn)

        create_layout.addLayout(region_row)



        root_row = QHBoxLayout()

        root_row.setSpacing(2)

        self.normal_login_radio = QRadioButton("SSH密钥模式", checked=True)

        self.root_login_radio = QRadioButton("Root密码模式")

        self.login_mode_group = QButtonGroup(self)

        self.login_mode_group.addButton(self.normal_login_radio)

        self.login_mode_group.addButton(self.root_login_radio)



        self.custom_password_radio = QRadioButton("用户自定义密码", checked=True)

        self.random_password_radio = QRadioButton("自动随机密码")

        self.password_mode_group = QButtonGroup(self)

        self.password_mode_group.addButton(self.custom_password_radio)

        self.password_mode_group.addButton(self.random_password_radio)



        self.root_password_edit = QLineEdit()

        self.root_password_edit.setPlaceholderText("Root自定义密?")

        self.root_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.root_login_radio.toggled.connect(self.update_root_mode_ui)

        self.custom_password_radio.toggled.connect(self.update_root_mode_ui)

        self.random_password_radio.toggled.connect(self.update_root_mode_ui)



        root_row.addWidget(QLabel("登录模式:"))

        root_row.addWidget(self.normal_login_radio)

        root_row.addWidget(self.root_login_radio)

        root_row.addSpacing(10)

        root_row.addWidget(self.custom_password_radio)

        root_row.addWidget(self.random_password_radio)

        root_row.addWidget(self.root_password_edit, 1)

        create_layout.addLayout(root_row)

        # ?????????????????????????????????

        log_frame = QFrame()

                # QFrame now uses global style

        log_layout = QVBoxLayout(log_frame)

        log_layout.setContentsMargins(6, 2, 6, 2)

        log_layout.setSpacing(2)



        log_head = QHBoxLayout()

        log_head.setContentsMargins(0, 0, 0, 0)

        log_head.setSpacing(4)

        lbl_log = QLabel("<b>📜 日志</b>")

        lbl_log.setStyleSheet("font-size: 12px; padding: 0;")

        log_head.addWidget(lbl_log)

        log_head.addStretch()

        clear_log_btn = QPushButton("清空")

        clear_log_btn.setFixedHeight(20)

        clear_log_btn.setStyleSheet("font-size: 11px; padding: 0 6px;")

        clear_log_btn.clicked.connect(lambda: self.log_area.clear())

        log_head.addWidget(clear_log_btn)

        log_layout.addLayout(log_head)



        self.log_area = QTextEdit()

        self.log_area.setReadOnly(True)

        # 无最低高度限制，用户可自由拖动
        self.log_area.setPlaceholderText("运行日志会显示在这里... [7.4 创建后自动执行命令 · 无备份 · HTTP/HTTPS开放 · 全开防火墙]")

        log_layout.addWidget(self.log_area)



        command_frame = QFrame()

                # QFrame now uses global style

        command_layout = QVBoxLayout(command_frame)

        command_layout.setContentsMargins(6, 2, 6, 2)

        command_layout.setSpacing(2)

        command_layout.addWidget(QLabel("<b>💻 命令执行</b>"))



        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_row.addWidget(QLabel("模式:"))

        self.cmd_mode_normal = QRadioButton("普通执行", checked=True)
        self.cmd_mode_post_create = QRadioButton("创建后执行")
        self.cmd_mode_group = QButtonGroup(self)
        self.cmd_mode_group.addButton(self.cmd_mode_normal)
        self.cmd_mode_group.addButton(self.cmd_mode_post_create)

        mode_row.addWidget(self.cmd_mode_normal)
        mode_row.addWidget(self.cmd_mode_post_create)
        mode_row.addStretch()
        command_layout.addLayout(mode_row)

        self.command_input = QTextEdit()
        self.command_input.setObjectName("commandInput")

        self.command_input.setPlaceholderText("输入要在选中实例上执行的命令，例如：uname -a")

        self.command_input.installEventFilter(self)

        # 无最低高度限制，用户可自由拖动
        command_layout.addWidget(self.command_input)



        btn_row = QHBoxLayout()

        self.execute_btn = QPushButton("执行命令")

        self.execute_btn.setObjectName("primaryBtn")

        self.execute_btn.setMinimumHeight(28)

        self.execute_btn.clicked.connect(self.execute_commands)

        self.stop_btn = QPushButton("停止")

        self.stop_btn.setObjectName("dangerBtn")

        self.stop_btn.setMinimumHeight(28)

        self.stop_btn.clicked.connect(self.stop_execution)

        self.stop_btn.setEnabled(False)

        btn_row.addWidget(self.execute_btn)

        btn_row.addWidget(self.stop_btn)

        self.clear_log_btn = QPushButton("清空")
        self.clear_log_btn.setFixedHeight(22)
        self.clear_log_btn.setStyleSheet("font-size: 11px; padding: 0 8px;")
        self.clear_log_btn.clicked.connect(self.clear_logs)
        btn_row.addWidget(self.clear_log_btn)

        hint = QLabel("Shift + Enter  ↩️ 换行")

        hint.setStyleSheet("color: #888; font-size: 11px; padding-left: 6px;")

        btn_row.addWidget(hint)

        btn_row.addStretch()

        command_layout.addLayout(btn_row)



        # 命令分割器：日志+命令执行区
        self.command_splitter = QSplitter(Qt.Orientation.Vertical)

        # 按你的要求：日志区放在命令执行区上边

        self.command_splitter.addWidget(log_frame)

        self.command_splitter.addWidget(command_frame)

        self.command_splitter.setStretchFactor(0, 2)

        self.command_splitter.setStretchFactor(1, 3)

        self.command_splitter.setHandleWidth(8)

        self.command_splitter.setChildrenCollapsible(True)



        bottom_layout.addWidget(create_frame)

        bottom_layout.addWidget(self.command_splitter)



        self.v_splitter.addWidget(bottom_frame)

        self.v_splitter.setStretchFactor(0, 3)

        self.v_splitter.setStretchFactor(1, 5)



        self.update_regions()

        self.update_root_mode_ui()



    def auto_detect_proxy_type(self, text):

        parsed = parse_proxy_input(text, fallback_proxy_type=self.proxy_type.currentText(), require_protocol=False)

        if parsed.get('ok') and not parsed.get('empty'):

            self.proxy_type.setCurrentText(parsed.get('proxy_type', 'HTTPS'))



    def upload_pubkey(self):

        path, _ = QFileDialog.getOpenFileName()

        if path:

            with open(path, 'r', encoding='utf-8') as f:

                self.ssh_public_key = f.read().strip()

            self.pubkey_label.setText(os.path.basename(path))

            self.log_signal.emit("SSH公钥加载成功")



    def select_json(self):

        path, _ = QFileDialog.getOpenFileName(filter="JSON (*.json)")

        if path:

            self.current_json_path = path

            self.key_btn.setText(os.path.basename(path))

            self.email_edit.setText(os.path.splitext(os.path.basename(path))[0])



    def _normalize_json_paths(self, paths):

        normalized = []
        seen = set()

        for path in paths:
            if not path:
                continue

            full_path = os.path.abspath(path)
            lower_path = full_path.lower()

            if lower_path in seen or not os.path.isfile(full_path):
                continue

            if not lower_path.endswith('.json'):
                continue

            seen.add(lower_path)
            normalized.append(full_path)

        return normalized


    def import_json_accounts(self, paths, source_label="批量导入"):

        json_paths = self._normalize_json_paths(paths)

        if not json_paths:
            QMessageBox.warning(self, "提示", "未找到可导入的 JSON 文件")
            return

        count = 0
        skipped = 0
        existing_paths = {str(acc[3]).lower() for acc in self.db.get_all()}

        for path in json_paths:
            if path.lower() in existing_paths:
                skipped += 1
                continue

            filename = os.path.basename(path)

            try:
                pid = self.load_project_id_from_json(path)
                self.db.add_account(os.path.splitext(filename)[0], pid, path)
                existing_paths.add(path.lower())
                count += 1
            except Exception as e:
                skipped += 1
                self.log_signal.emit(f"{source_label}跳过 {filename}：{e}")

        if count:
            self.current_json_path = None
            self.email_edit.clear()
            self.key_btn.setText("选择JSON密钥")
            self.email_edit.setFocus()

        self.refresh_account_table()
        self.log_signal.emit(f"{source_label}完成：新增 {count} 个，跳过 {skipped} 个")


    def load_project_id_from_json(self, json_path):

        with open(json_path, 'r', encoding='utf-8') as f:

            data = json.load(f)

        project_id = data.get('project_id', '').strip()

        if not project_id:

            raise ValueError("JSON密钥中缺project_id")

        return project_id



    def add_account(self):

        if not self.email_edit.text() or not self.current_json_path:

            QMessageBox.warning(self, "提示", "请填写邮箱并选择JSON密钥")

            return

        try:

            project_id = self.load_project_id_from_json(self.current_json_path)

        except Exception as e:

            QMessageBox.critical(self, "错误", f"读取JSON密钥失败：{e}")

            return



        proxy_text = self.proxy_edit.text().strip()

        parsed_proxy = parse_proxy_input(proxy_text, fallback_proxy_type=self.proxy_type.currentText(), require_protocol=bool(proxy_text))

        if not parsed_proxy.get('ok'):

            QMessageBox.warning(self, "代理格式错误", parsed_proxy.get('error', proxy_formats_help_text()))

            self.log_signal.emit(f"新增账号时代理格式无法识别\n{parsed_proxy.get('error', proxy_formats_help_text())}")

            return



        if not parsed_proxy.get('empty'):

            self.proxy_type.setCurrentText(parsed_proxy.get('proxy_type', 'HTTPS'))



        self.db.add_account(

            self.email_edit.text(), project_id, self.current_json_path,

            proxy_text, parsed_proxy.get('proxy_type', self.proxy_type.currentText())

        )

        self.refresh_account_table()
        self.current_json_path = None
        self.email_edit.clear()
        self.proxy_edit.clear()
        self.key_btn.setText("选择JSON密钥")
        self.email_edit.setFocus()

        self.log_signal.emit("账号添加成功")



    def refresh_account_table(self):

        self.account_table.setRowCount(0)

        self._is_refreshing = True  # 标记刷新

        for acc in self.db.get_all():

            row = self.account_table.rowCount()

            self.account_table.insertRow(row)

            self.account_table.setCellWidget(row, 0, QCheckBox())

            # 修正映射关系：ID(0), Email(1), Project ID(2), Proxy(4), ProxyType(5)

            # 跳过 key_path 列（索引3）

            mapping = [acc[0], acc[1], acc[2], acc[4], acc[5]]

            for col, val in enumerate(mapping, 1):

                table_item = QTableWidgetItem(str(val))

                if col == 4:

                    table_item.setFlags(table_item.flags() | Qt.ItemFlag.ItemIsEditable)

                else:

                    table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.account_table.setItem(row, col, table_item)

        self._is_refreshing = False



    def emit_account_proxy_status(self, account, gcp, action_label):

        account_label = account[1] if isinstance(account, tuple) else account.get('email', '未知账号')

        if gcp.proxy_url:

            proto = "SOCKS5" if gcp.proxy_url.startswith('socks5') else "HTTP"

            self.log_signal.emit(f"[{account_label}] 🌐 {action_label} | 使用代理 [{proto}]：{gcp.proxy_url}")

        else:

            self.log_signal.emit(f"[{account_label}] 🌐 {action_label} | 未使用代理，直连 GCP")



    def query_instances(self):

        acc = self.get_selected_account()

        if not acc:

            QMessageBox.warning(self, "提示", "请选择账号")

            return


        self.query_btn.setEnabled(False)

        gcp = GCPService(acc[3], acc[2], acc[1], acc[4], acc[5])

        self.emit_account_proxy_status(acc, gcp, "查询实例")

        self.loader = InstanceLoader(gcp)

        self.loader.finished.connect(self.update_instance_table)

        self.loader.finished.connect(lambda _: self.query_btn.setEnabled(True))

        self.loader.error.connect(self.on_query_error)

        self.loader.start()



    def update_instance_table(self, instances):

        self.current_instances = instances

        if hasattr(self, 'api_lock'):
            self.api_refresh_snapshots()

        self.instances_table.setRowCount(0)

        for inst in instances:

            row = self.instances_table.rowCount()

            self.instances_table.insertRow(row)

            name = inst.get('name', '')

            name_item = QTableWidgetItem(name)

            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.instances_table.setItem(row, 0, name_item)

            ip_item = QTableWidgetItem(inst.get('ip', ''))

            ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.instances_table.setItem(row, 1, ip_item)

            zone_item = QTableWidgetItem(inst.get('zone', ''))

            zone_item.setFlags(zone_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.instances_table.setItem(row, 2, zone_item)

            # 精准匹配哪吒面板的IP-名称

            monitor_name = self.nezha_ip_map.get(inst.get('ip', ''), '未配制')

            monitor_item = QTableWidgetItem(monitor_name)

            monitor_item.setFlags(monitor_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.instances_table.setItem(row, 3, monitor_item)

            password_item = QTableWidgetItem(self.instance_password_cache.get(name, ''))

            password_item.setFlags(password_item.flags() | Qt.ItemFlag.ItemIsEditable)

            self.instances_table.setItem(row, 4, password_item)

            # 执行结果列（初始化为空）

            result_item = QTableWidgetItem("")

            result_item.setFlags(result_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.instances_table.setItem(row, 5, result_item)

            cached = self.post_create_result_cache.get(name)
            if cached:
                ok, short = cached
                result_text = f"{chr(9989) if ok else chr(10060)} {short}"
                cached_item = QTableWidgetItem(result_text)
                cached_item.setFlags(cached_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cached_item.setForeground(QColor("#34a853") if ok else QColor("#ea4335"))
                self.instances_table.setItem(row, 5, cached_item)


        self.log_signal.emit(f"查询完成：{len(instances)}台实例")

        self.query_btn.setEnabled(True)

        for btn in [self.del_inst_btn, self.start_inst_btn, self.stop_inst_btn, self.reset_inst_btn]:

            btn.setEnabled(len(instances) > 0)



    def on_query_error(self, error_text):


        self.query_btn.setEnabled(True)

        self.log_signal.emit(f"查询失败：{error_text}")



    def on_instance_table_double_click(self, row, col):

        if col == 4:

            item = self.instances_table.item(row, col)

            if item:

                self.instances_table.editItem(item)

            return

        if col == 1:

            ip_item = self.instances_table.item(row, 1)

            if ip_item and ip_item.text():

                QApplication.clipboard().setText(ip_item.text())

                self.log_signal.emit(f"IP {ip_item.text()} 已复制")

        elif col == 0:

            name_item = self.instances_table.item(row, 0)

            if name_item and name_item.text():

                QApplication.clipboard().setText(name_item.text())

                self.log_signal.emit(f"实例名称 {name_item.text()} 已复制")

        elif col == 2:

            zone_item = self.instances_table.item(row, 2)

            if zone_item and zone_item.text():

                QApplication.clipboard().setText(zone_item.text())

                self.log_signal.emit(f"可用性 {zone_item.text()} 已复制")

        elif col == 3:

            monitor_item = self.instances_table.item(row, 3)

            if monitor_item and monitor_item.text():

                QApplication.clipboard().setText(monitor_item.text())

                self.log_signal.emit(f"监控名称 {monitor_item.text()} 已复制")

        elif col == 5:

            result_item = self.instances_table.item(row, 5)

            if result_item and result_item.text():

                QApplication.clipboard().setText(result_item.text())

                self.log_signal.emit("执行结果已复制")



    def on_instance_table_edit(self, item):

        if getattr(self, '_is_refreshing', False):

            return

        if item.column() != 4:

            return

        row = item.row()

        name_item = self.instances_table.item(row, 0)

        ip_item = self.instances_table.item(row, 1)

        if not name_item:

            return

        name = name_item.text().strip()

        ip = ip_item.text().strip() if ip_item else ''

        password = item.text().strip()

        self.instance_password_cache[name] = password

        self.db.save_vm_password(name, ip, password)

        self.log_signal.emit(f"实例 {name} 的 Root 密码已保存")



    def operate_instances(self, action):

        selected = self.get_selected_instances()

        if not selected:

            QMessageBox.warning(self, "提示", "请选择实例")

            return

        

        # 二次确认弹窗

        action_names = {

            'delete': '删除',

            'start': '启动',

            'stop': '停止',

            'reset': '重启'

        }

        action_name = action_names.get(action, action)

        instance_names = ', '.join([s['name'] for s in selected[:3]])

        if len(selected) > 3:

            instance_names += f' 等{len(selected)}台实例'

        

        reply = QMessageBox.question(

            self, 

            f"确认{action_name}", 

            f"确认{action_name}以下 {len(selected)} 台实例？\n\n{instance_names}",

            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

        )

        if reply != QMessageBox.StandardButton.Yes:

            return

        

        self.log_signal.emit(f"{action_name}中：{len(selected)} 台实例..")

        

        acc = self.get_selected_account()

        gcp = GCPService(acc[3], acc[2], acc[1], acc[4], acc[5])

        self.emit_account_proxy_status(acc, gcp, f"{action_name}实例")

        self.operator = InstanceOperator(gcp, selected, action)

        self.operator.log.connect(self.log_signal.emit)

        self.operator.finished.connect(lambda: self.log_signal.emit("🔄 实例操作完成，正在自动刷新实例列表.."))

        self.operator.finished.connect(self.query_instances)

        self.operator.start()



    def is_root_password_mode(self):

        return self.root_login_radio.isChecked()



    def update_root_mode_ui(self):

        root_mode = self.root_login_radio.isChecked()

        self.custom_password_radio.setEnabled(root_mode)

        self.random_password_radio.setEnabled(root_mode)

        self.root_password_edit.setEnabled(root_mode and self.custom_password_radio.isChecked())

        if not root_mode:

            self.root_password_edit.setEnabled(False)



    def generate_random_root_password(self, length=16):

        alphabet = string.ascii_letters + string.digits + '@#_-+='

        return ''.join(secrets.choice(alphabet) for _ in range(length))



    def build_root_startup_script(self, root_password):

        safe_password = root_password.replace("'", "'\"'\"'")

        return f"""#!/bin/bash

set -euxo pipefail

mkdir -p /root

LOG_FILE=/root/gcp_root_mode.log

exec > >(tee -a "$LOG_FILE") 2>&1



echo "[INFO] starting root password mode setup"

export DEBIAN_FRONTEND=noninteractive



echo 'root:{safe_password}' | chpasswd

passwd -u root || true



if [ -f /etc/ssh/sshd_config ]; then

  sed -i 's/^\\s*#\\?\\s*PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config || true

  sed -i 's/^\\s*#\\?\\s*PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config || true

  sed -i 's/^\\s*#\\?\\s*KbdInteractiveAuthentication.*/KbdInteractiveAuthentication yes/g' /etc/ssh/sshd_config || true

  sed -i 's/^\\s*#\\?\\s*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication yes/g' /etc/ssh/sshd_config || true

  grep -q '^PermitRootLogin yes$' /etc/ssh/sshd_config || echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config

  grep -q '^PasswordAuthentication yes$' /etc/ssh/sshd_config || echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config

  grep -q '^KbdInteractiveAuthentication yes$' /etc/ssh/sshd_config || echo 'KbdInteractiveAuthentication yes' >> /etc/ssh/sshd_config

  grep -q '^ChallengeResponseAuthentication yes$' /etc/ssh/sshd_config || echo 'ChallengeResponseAuthentication yes' >> /etc/ssh/sshd_config

fi



rm -rf /etc/ssh/sshd_config.d/* /etc/ssh/ssh_config.d/* || true



mkdir -p /etc/ssh/sshd_config.d /etc/ssh/ssh_config.d

cat >/etc/ssh/sshd_config.d/99-root-password.conf <<'EOF'

PermitRootLogin yes

PasswordAuthentication yes

KbdInteractiveAuthentication yes

ChallengeResponseAuthentication yes

UsePAM yes

EOF



sshd -t || sshd -T || true

systemctl restart ssh || systemctl restart sshd || service ssh restart || service sshd restart || true

sleep 2



echo "[INFO] root password mode setup finished"

touch /root/.gcp_root_mode_ok

"""

    def get_post_create_command(self):
        # Reuse the command execution textbox as the source of post-create commands.
        cmd_edit = getattr(self, 'command_input', None)
        if not cmd_edit:
            return ""
        try:
            return cmd_edit.toPlainText().strip()
        except Exception:
            return ""

    def run_post_create_command(self, account_label, instance_name, ip, password, cmd=""):
        cmd = (cmd or "").strip()
        if not cmd:
            cmd = self.get_post_create_command()
        if not cmd:
            return

        # password may be empty in SSH key mode; run_ssh_command will fall back to agent/system keys
        username = "root"

        wait_port_deadline = time.time() + 180
        while time.time() < wait_port_deadline:
            try:
                s = socket.create_connection((ip, 22), timeout=2)
                s.close()
                break
            except Exception:
                time.sleep(2)
        else:
            msg = "SSH端口超时未就绪"
            self.log_signal.emit(f"[{account_label}] [{instance_name}] ❌ {msg}")
            self.exec_result_signal.emit(instance_name, False, msg)
            return

        # Wait until SSH authentication is usable (startup-script needs time)
        wait_ssh_deadline = time.time() + 240
        last_err = ""
        while time.time() < wait_ssh_deadline:
            ok, out = self.run_ssh_command(
                ip,
                username,
                password,
                "echo __SSH_OK__",
                connect_timeout=8,
                idle_timeout=8,
                total_timeout=15,
                log_callback=None,
            )
            if ok and "__SSH_OK__" in (out or ""):
                break
            last_err = out or ""
            time.sleep(3)
        else:
            msg = f"SSH未就绪或认证失败：{last_err}".strip()
            self.log_signal.emit(f"[{account_label}] [{instance_name}] ❌ {msg}")
            self.exec_result_signal.emit(instance_name, False, msg)
            return

        self.log_signal.emit(f"[{account_label}] [{instance_name}] ▶ 创建后命令开始执行")

        def _cb(text):
            if text:
                self.log_signal.emit(f"[{account_label}] [{instance_name}] {text.rstrip()}")

        ok, out = self.run_ssh_command(
            ip,
            username,
            password,
            cmd,
            log_callback=_cb,
        )

        short = (out or "").strip()
        if len(short) > 200:
            short = short[:200] + "..."
        self.post_create_result_cache[instance_name] = (ok, short)

        self.exec_result_signal.emit(instance_name, ok, out)
        self.log_signal.emit(f"[{account_label}] [{instance_name}] {'✅' if ok else '❌'} 创建后命令执行{'成功' if ok else '失败'}")



    def start_create(self):

        accounts = [acc for i, acc in enumerate(self.db.get_all()) if self.account_table.cellWidget(i, 0).isChecked()]

        if not accounts:

            QMessageBox.warning(self, "提示", "请选择账号")

            return

        count = int(self.count_edit.text()) if self.count_edit.text().isdigit() else 1

        if count <= 0:

            QMessageBox.warning(self, "提示", "创建数量必须大于 0")

            return



        root_mode = self.is_root_password_mode()

        custom_password_mode = self.custom_password_radio.isChecked()

        custom_root_password = self.root_password_edit.text().strip()

        if root_mode and custom_password_mode and not custom_root_password:

            QMessageBox.warning(self, "提示", "请选择 Root密码模式后，请填写自定义密码")

            return



        create_config = {

            'root_mode': root_mode,

            'custom_password_mode': custom_password_mode,

            'custom_root_password': custom_root_password,

            'use_free_regions': self.free_radio.isChecked(),

            'selected_region_text': self.region_box.currentText().strip(),

        }

        post_create_cmd = ""
        if getattr(self, 'cmd_mode_post_create', None) and self.cmd_mode_post_create.isChecked():
            post_create_cmd = self.get_post_create_command()
        if post_create_cmd and not check_paramiko():
            QMessageBox.warning(self, "提示", "创建后自动执行命令需要 paramiko，请先安装：pip install paramiko")
            return



        create_config['post_create_cmd'] = post_create_cmd
        self.create_btn_signal.emit(False)

        self.log_signal.emit("=== 开始批量部署===")



        def worker():

            try:

                for acc in accounts:

                    try:

                        self.process_account(acc, count, create_config)

                    except Exception as e:

                        self.log_signal.emit(f"[{acc[1]}] 处理账号时发生未捕获异常：{e}")

                self.log_signal.emit("=== 全部部署完成 ===")

            finally:

                self.create_btn_signal.emit(True)

                self.log_signal.emit("🔄 批量部署完成，正在自动刷新实例..")

                self.refresh_instances_signal.emit()



        threading.Thread(target=worker, daemon=True).start()



    def get_region_zones(self, region):

        zones = ZONE_OPTIONS.get(region, [])

        if not zones:

            zones = [f"{region}-{s}" for s in ['a', 'b', 'c', 'd']]

        return zones



    def robust_create_instance(self, gcp, primary_region, instance_name, tried_zones, candidate_regions, startup_script=""):

        ordered_regions = [primary_region] + [r for r in candidate_regions if r != primary_region]

        if len(ordered_regions) > 1:

            remaining = ordered_regions[1:]

            random.shuffle(remaining)

            ordered_regions = [ordered_regions[0]] + remaining



        for region in ordered_regions:

            region_zones = [z for z in self.get_region_zones(region) if z not in tried_zones]

            random.shuffle(region_zones)

            for zone in region_zones:

                success, result = gcp.create_instance(zone, instance_name, startup_script=startup_script)

                if success:

                    return True, result

                if str(result) != "资源耗尽":

                    return False, result

                tried_zones.add(zone)



        return False, "所有可用区资源耗尽"



    def process_account(self, acc, count, create_config):

        gcp = GCPService(acc[3], acc[2], acc[1], acc[4], acc[5])

        post_cmd_for_label = (create_config.get("post_create_cmd", "") or "").strip()
        action_label = "批量创建实例"
        if post_cmd_for_label:
            action_label = "批量创建实例 🧾并执行命令"
        self.emit_account_proxy_status(acc, gcp, action_label)

        if self.ssh_public_key:

            ssh_ok, ssh_msg = gcp.add_ssh_key(self.ssh_public_key)

            self.log_signal.emit(f"[{acc[1]}] {'成功' if ssh_ok else '失败: ' + ssh_msg}")



        root_mode = create_config.get('root_mode', False)

        custom_password_mode = create_config.get('custom_password_mode', True)

        custom_root_password = create_config.get('custom_root_password', '')

        pool = FREE_REGIONS if create_config.get('use_free_regions', True) else PAID_REGIONS

        pool_regions = list(pool.values())

        selected_region_text = create_config.get('selected_region_text', '').strip()

        selected_region = pool.get(selected_region_text)



        try:

            instances = gcp.list_instances()

            region_count = defaultdict(int)

            for inst in instances:

                zone = inst['zone']

                region = zone.lstrip('zones/').rsplit('-', 1)[0]

                if region in pool_regions:

                    region_count[region] += 1

        except Exception as e:

            self.log_signal.emit(f"[{acc[1]}] 实例清点失败：{e}")

            return



        def calc_available_regions():

            return [r for r in pool_regions if region_count[r] < 4]



        available_regions = calc_available_regions()

        if not available_regions:

            self.log_signal.emit(f"[{acc[1]}] 当前模式下所有区域配额已满，跳过该账")

            return



        self.log_signal.emit(f"[{acc[1]}] 📊 当前配额: {dict(region_count)} | 可用区域: {len(available_regions)} | 开始创建{count} 台")



        created = 0
        created_lock = threading.Lock()
        planning_lock = threading.Lock()
        max_workers = max(1, min(12, count))

        post_cmd = create_config.get("post_create_cmd", "")

        def calc_available_locked():
            return [r for r in pool_regions if region_count[r] < 4]

        def reserve_region():
            with planning_lock:
                available = calc_available_locked()
                if not available:
                    return None, []
                if selected_region_text == "随机选择 (Random)" or not selected_region:
                    chosen = random.choice(available)
                    candidates = available[:]
                else:
                    if selected_region in available:
                        chosen = selected_region
                        candidates = [selected_region]
                    else:
                        chosen = random.choice(available)
                        candidates = available[:]
                region_count[chosen] += 1
                return chosen, candidates

        def release_region(reserved):
            if not reserved:
                return
            with planning_lock:
                region_count[reserved] = max(0, region_count.get(reserved, 0) - 1)

        def run_one(idx):
            nonlocal created
            reserved_region, candidate_regions = reserve_region()
            if not reserved_region:
                return False, "无可用区域"

            name = f"vm-{acc[0]}-{idx}-{random.randint(1000, 9999)}"
            tried_zones = set()
            root_password = ""
            password_log_part = ""
            startup_script = ""

            if root_mode:
                if custom_password_mode:
                    root_password = custom_root_password
                    password_log_part = f"Root密码：{root_password}"
                else:
                    root_password = self.generate_random_root_password()
                    password_log_part = f"Root密码：{root_password}"
                startup_script = self.build_root_startup_script(root_password)

            success, res = self.robust_create_instance(
                gcp, reserved_region, name, tried_zones, candidate_regions, startup_script=startup_script
            )
            if not success:
                release_region(reserved_region)
                return False, res

            ip, zone = res
            actual_region = zone.rsplit("-", 1)[0]
            if actual_region != reserved_region and actual_region in pool_regions:
                with planning_lock:
                    region_count[reserved_region] = max(0, region_count.get(reserved_region, 0) - 1)
                    region_count[actual_region] += 1

            if root_mode:
                with created_lock:
                    self.instance_password_cache[name] = root_password
                self.db.save_vm_password(name, ip, root_password)

            with created_lock:
                created += 1

            if post_cmd:
                ssh_password = root_password if root_mode else ""
                self.run_post_create_command(acc[1], name, ip, ssh_password, cmd=post_cmd)

            if root_mode:
                self.log_signal.emit(
                    f"[{acc[1]}] 第{idx}台创建成功 | 区域：{actual_region} ({zone}) | IP：{ip} | 登录：root | {password_log_part}"
                )
            else:
                self.log_signal.emit(
                    f"[{acc[1]}] 第{idx}台创建成功 | 区域：{actual_region} ({zone}) | IP：{ip}"
                )

            return True, (ip, zone)

        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(1, count + 1):
                futures.append(executor.submit(run_one, i))
            for fut in as_completed(futures):
                ok, res = fut.result()
                if not ok:
                    self.log_signal.emit(f"[{acc[1]}] ⚠️ 创建/执行失败：{res}")

        self.log_signal.emit(f"[{acc[1]}] 📈 创建完成：{created}/{count} 台成功")



    def get_selected_account(self):

        for i in range(self.account_table.rowCount()):

            checkbox = self.account_table.cellWidget(i, 0)

            id_item = self.account_table.item(i, 1)

            if checkbox and checkbox.isChecked() and id_item:

                return self.db.get_by_id(id_item.text())

        return None



    def get_selected_instances(self):

        instances = []

        for r in self.instances_table.selectionModel().selectedRows():

            name_item = self.instances_table.item(r.row(), 0)

            ip_item = self.instances_table.item(r.row(), 1)

            zone_item = self.instances_table.item(r.row(), 2)

            if not (name_item and ip_item and zone_item):

                continue

            instances.append({

                'name': name_item.text(),

                'zone': zone_item.text(),

                'ip': ip_item.text()

            })

        return instances



    def append_log(self, msg):

        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")

        if hasattr(self, 'api_lock'):

            with self.api_lock:

                self.api_log_seq += 1

                self.api_logs.append({'seq': self.api_log_seq, 'time': timestamp, 'message': str(msg)})

                if len(self.api_logs) > 2000:

                    self.api_logs = self.api_logs[-2000:]

        if hasattr(self, 'log_area') and self.log_area is not None:

            self.log_area.append(f"[{timestamp}] {msg}")

        else:

            print(f"[{timestamp}] {msg}")



    def api_refresh_snapshots(self):
        accounts = []
        for acc in self.db.get_all():
            accounts.append({
                'id': str(acc[0]),
                'email': acc[1],
                'project_id': acc[2],
                'key_file': os.path.basename(acc[3] or ''),
                'proxy': acc[4] or '',
                'proxy_type': acc[5] or '',
            })
        instances = []
        for inst in getattr(self, 'current_instances', []) or []:
            name = inst.get('name', '')
            ok, output = self.post_create_result_cache.get(name, (None, ''))
            instances.append({
                'name': name,
                'ip': inst.get('ip', ''),
                'zone': inst.get('zone', ''),
                'root_password': self.instance_password_cache.get(name, ''),
                'post_create_success': ok,
                'post_create_output': output,
            })
        with self.api_lock:
            self.api_account_snapshot = accounts
            self.api_instance_snapshot = instances

    def start_local_api_server(self):
        try:
            self.api_server = LocalAPIServer(self)
            self.api_server.start()
            self.log_signal.emit(f"Local API started: http://{API_HOST}:{API_PORT}")
        except Exception as exc:
            self.log_signal.emit(f"Local API start failed: {exc}")

    def _api_new_task(self, action, payload=None):
        with self.api_lock:
            task_id = str(self.api_next_task_id)
            self.api_next_task_id += 1
            self.api_tasks[task_id] = {
                'id': task_id,
                'action': action,
                'status': 'queued',
                'payload': self._api_safe_payload(payload or {}),
                'created_at': time.time(),
                'updated_at': time.time(),
                'message': '',
            }
            return task_id

    def _api_update_task(self, task_id, status=None, message=None):
        if not task_id:
            return
        with self.api_lock:
            task = self.api_tasks.get(str(task_id))
            if not task:
                return
            if status:
                task['status'] = status
            if message is not None:
                task['message'] = message
            task['updated_at'] = time.time()

    def _api_safe_payload(self, payload):
        safe = dict(payload or {})
        for key in list(safe.keys()):
            if key.lower() in ('key', 'json', 'credentials', 'secret', 'token'):
                safe[key] = '***'
        return safe

    def api_status(self):
        accounts = self.api_accounts()
        with self.api_lock:
            last_log_seq = self.api_log_seq
            tasks = list(self.api_tasks.values())[-20:]
        return {
            'ok': True,
            'version': API_VERSION,
            'api': {'host': API_HOST, 'port': API_PORT},
            'account_count': len(accounts),
            'instance_count': len(getattr(self, 'current_instances', []) or []),
            'last_log_seq': last_log_seq,
            'tasks': tasks,
        }

    def api_accounts(self):
        with self.api_lock:
            return list(self.api_account_snapshot)

    def api_instances(self):
        with self.api_lock:
            return list(self.api_instance_snapshot)

    def api_get_logs(self, since=0, limit=200):
        limit = max(1, min(int(limit), 1000))
        with self.api_lock:
            logs = [item for item in self.api_logs if item['seq'] > int(since)]
            return logs[-limit:]

    def api_tasks_snapshot(self):
        with self.api_lock:
            return list(self.api_tasks.values())[-500:]

    def _api_register_external_task(self, task_id, action, payload=None):
        with self.api_lock:
            self.api_tasks[str(task_id)] = {
                'id': str(task_id),
                'action': action,
                'status': 'queued',
                'payload': self._api_safe_payload(payload or {}),
                'created_at': time.time(),
                'updated_at': time.time(),
                'message': '',
            }

    def api_automation_status(self):
        return self.auto_scheduler.snapshot()

    def api_set_automation(self, payload):
        payload = payload or {}
        status = self.auto_scheduler.configure(payload)
        if payload.get('run_existing'):
            return self.auto_scheduler.enqueue_existing(payload.get('account_ids'))
        return status

    def api_stop_automation(self, payload):
        return self.auto_scheduler.stop()

    def api_run_existing_accounts(self, payload):
        payload = payload or {}
        return self.auto_scheduler.enqueue_existing(payload.get('account_ids'))

    def api_task_report(self):
        with self.api_lock:
            tasks = list(self.api_tasks.values())
        summary = defaultdict(int)
        for task in tasks:
            summary[task.get('status', 'unknown')] += 1
        return {'ok': True, 'summary': dict(summary), 'tasks': tasks[-500:]}

    def api_enqueue_create(self, payload):
        task_id = self._api_new_task('create', payload)
        payload = dict(payload or {})
        payload['task_id'] = task_id
        self.api_create_signal.emit(payload)
        return {'ok': True, 'task_id': task_id, 'message': 'create queued'}

    def api_enqueue_refresh(self, payload):
        task_id = self._api_new_task('refresh', payload)
        payload = dict(payload or {})
        payload['task_id'] = task_id
        self.api_refresh_signal.emit(payload)
        return {'ok': True, 'task_id': task_id, 'message': 'refresh queued'}

    def api_enqueue_execute(self, payload):
        task_id = self._api_new_task('execute', payload)
        payload = dict(payload or {})
        payload['task_id'] = task_id
        self.api_execute_signal.emit(payload)
        return {'ok': True, 'task_id': task_id, 'message': 'execute queued'}

    def api_set_watch_task(self, payload):
        task_id = self._api_new_task('watch_task', payload)
        with self.api_lock:
            self.api_watch_task = dict(payload or {})
            self.api_watch_task['task_id'] = task_id
            self.api_watch_task['armed_at'] = time.time()
        return {'ok': True, 'task_id': task_id, 'message': 'watch task armed'}

    def api_check_new_accounts(self):
        self.api_refresh_snapshots()
        current_ids = {item['id'] for item in self.api_account_snapshot}
        new_ids = sorted(current_ids - getattr(self, 'api_account_ids', set()))
        self.api_account_ids = current_ids
        if new_ids:
            self.log_signal.emit(f"Local API detected {len(new_ids)} new JSON account(s)")
        try:
            self.auto_scheduler.scan_new_accounts()
        except Exception as exc:
            self.log_signal.emit(f"Auto task scan failed: {exc}")
        if not new_ids:
            return
        with self.api_lock:
            watch_task = dict(self.api_watch_task or {})
            self.api_watch_task = None
        if watch_task:
            watch_task['account_ids'] = new_ids
            self.log_signal.emit("Local API triggered pending watch task")
            self.api_handle_create(watch_task)

    def _api_select_accounts(self, account_ids=None):
        wanted = {str(item) for item in (account_ids or [])}
        selected = []
        for row in range(self.account_table.rowCount()):
            checkbox = self.account_table.cellWidget(row, 0)
            id_item = self.account_table.item(row, 1)
            if not checkbox or not id_item:
                continue
            should_select = (not wanted) or (id_item.text() in wanted)
            checkbox.setChecked(should_select)
            if should_select:
                selected.append(id_item.text())
        return selected

    def _api_select_instances(self, names=None, all_instances=False):
        wanted = {str(item) for item in (names or [])}
        self.instances_table.clearSelection()
        selected = []
        for row in range(self.instances_table.rowCount()):
            name_item = self.instances_table.item(row, 0)
            if not name_item:
                continue
            should_select = all_instances or (name_item.text() in wanted)
            if should_select:
                self.instances_table.selectRow(row)
                selected.append(name_item.text())
        return selected

    def api_handle_create(self, payload):
        task_id = payload.get('task_id')
        try:
            selected = self._api_select_accounts(payload.get('account_ids'))
            if not selected:
                self._api_update_task(task_id, 'failed', 'no account selected')
                self.log_signal.emit("Local API create failed: no account selected")
                return
            if payload.get('count') is not None:
                self.count_edit.setText(str(max(1, int(payload.get('count')))))
            if payload.get('zone'):
                zone = str(payload.get('zone'))
                index = self.region_box.findText(zone)
                if index >= 0:
                    self.region_box.setCurrentIndex(index)
            if payload.get('root_password'):
                self.custom_password_radio.setChecked(True)
                self.root_password_edit.setText(str(payload.get('root_password')))
            command = (payload.get('post_command') or payload.get('command') or '').strip()
            if command:
                self.cmd_mode_post_create.setChecked(True)
                self.command_input.setPlainText(command)
            self._api_update_task(task_id, 'running', f"creating with {len(selected)} account(s)")
            self.log_signal.emit(f"Local API create started, task_id={task_id}")
            self.start_create()
        except Exception as exc:
            self._api_update_task(task_id, 'failed', str(exc))
            self.log_signal.emit(f"Local API create exception: {exc}")

    def api_handle_refresh(self, payload):
        task_id = payload.get('task_id')
        self._api_update_task(task_id, 'running', 'refreshing instances')
        self.query_instances()
        self._api_update_task(task_id, 'done', 'refresh requested')

    def api_handle_execute(self, payload):
        task_id = payload.get('task_id')
        command = (payload.get('command') or '').strip()
        if not command:
            self._api_update_task(task_id, 'failed', 'empty command')
            return
        self.cmd_mode_normal.setChecked(True)
        self.command_input.setPlainText(command)
        selected = self._api_select_instances(payload.get('instance_names'), bool(payload.get('all', True)))
        if not selected:
            self._api_update_task(task_id, 'failed', 'no instances selected')
            self.log_signal.emit("Local API execute failed: no instance selected")
            return
        self._api_update_task(task_id, 'running', f"executing on {len(selected)} instance(s)")
        self.log_signal.emit(f"Local API execute started, task_id={task_id}")
        self.execute_commands()

    def run_auto_account_task(self, account, template, task_id):
        account_label = account[1]
        count = max(1, int(template.get('count', 1) or 1))
        root_password = (template.get('root_password') or '').strip() or self.generate_random_root_password()
        post_command = (template.get('post_command') or template.get('command') or '').strip()
        verify_command = (template.get('verify_command') or '').strip()
        retries = max(0, min(int(template.get('retry_count', 2) or 2), 5))
        use_free_regions = bool(template.get('use_free_regions', True))
        selected_region = (template.get('region') or '').strip()
        pool = FREE_REGIONS if use_free_regions else PAID_REGIONS
        candidate_regions = list(pool.keys())
        if selected_region and selected_region in pool:
            primary_region = selected_region
        else:
            primary_region = random.choice(candidate_regions)
        gcp = GCPService(account[3], account[2], account[1], account[4], account[5])
        startup_script = self.build_root_startup_script(root_password)
        results = []
        for index in range(1, count + 1):
            instance_name = f"auto-{account[0]}-{int(time.time())}-{index}-{random.randint(1000, 9999)}"
            tried_zones = set()
            self._api_update_task(task_id, 'creating', f"{account_label}: creating {instance_name}")
            create_ok = False
            create_result = None
            for attempt in range(retries + 1):
                ok, result = self.robust_create_instance(
                    gcp,
                    primary_region,
                    instance_name,
                    tried_zones,
                    candidate_regions,
                    startup_script=startup_script,
                )
                if ok:
                    create_ok = True
                    create_result = result
                    break
                create_result = result
                self.log_signal.emit(f"[{account_label}] Auto create retry {attempt + 1}/{retries + 1}: {result}")
                time.sleep(5)
            if not create_ok:
                results.append({'name': instance_name, 'ok': False, 'stage': 'create', 'error': str(create_result)})
                continue
            ip, zone = create_result
            self.db.save_vm_password(instance_name, ip, root_password)
            self.instance_password_cache[instance_name] = root_password
            instance_result = {'name': instance_name, 'zone': zone, 'ip': ip, 'ok': True, 'stage': 'created'}
            self._api_update_task(task_id, 'waiting_ssh', f"{account_label}: waiting ssh {ip}")
            ssh_ok, ssh_msg = self.wait_auto_ssh(ip, 'root', root_password, timeout=int(template.get('ssh_timeout', 300) or 300))
            instance_result['ssh_ok'] = ssh_ok
            instance_result['ssh_message'] = ssh_msg
            if not ssh_ok:
                instance_result.update({'ok': False, 'stage': 'ssh'})
                results.append(instance_result)
                continue
            if post_command:
                self._api_update_task(task_id, 'installing', f"{account_label}: installing on {ip}")
                cmd_ok, cmd_out = self.run_ssh_command(
                    ip,
                    'root',
                    root_password,
                    post_command,
                    connect_timeout=12,
                    idle_timeout=int(template.get('idle_timeout', 180) or 180),
                    total_timeout=int(template.get('command_timeout', 1800) or 1800),
                    log_callback=lambda text, label=account_label, name=instance_name: self.log_signal.emit(f"[{label}] [{name}] {text.rstrip()}"),
                )
                instance_result['command_ok'] = cmd_ok
                instance_result['command_output_tail'] = (cmd_out or '')[-2000:]
                if not cmd_ok:
                    instance_result.update({'ok': False, 'stage': 'command'})
                    results.append(instance_result)
                    continue
            if verify_command:
                self._api_update_task(task_id, 'verifying', f"{account_label}: verifying {ip}")
                verify_ok, verify_out = self.run_ssh_command(
                    ip,
                    'root',
                    root_password,
                    verify_command,
                    connect_timeout=12,
                    idle_timeout=60,
                    total_timeout=int(template.get('verify_timeout', 180) or 180),
                )
                instance_result['verify_ok'] = verify_ok
                instance_result['verify_output'] = verify_out
                if not verify_ok:
                    instance_result.update({'ok': False, 'stage': 'verify'})
            instance_result['stage'] = 'done' if instance_result.get('ok') else instance_result.get('stage')
            results.append(instance_result)
        success_count = sum(1 for item in results if item.get('ok'))
        return {
            'ok': success_count == len(results) and bool(results),
            'message': f"{account_label}: {success_count}/{len(results)} instance(s) completed",
            'account_id': str(account[0]),
            'account_email': account_label,
            'project_id': account[2],
            'results': results,
        }

    def wait_auto_ssh(self, ip, username, password, timeout=300):
        deadline = time.time() + max(30, timeout)
        last_error = ''
        while time.time() < deadline:
            try:
                sock = socket.create_connection((ip, 22), timeout=5)
                sock.close()
            except Exception as exc:
                last_error = str(exc)
                time.sleep(5)
                continue
            ok, out = self.run_ssh_command(
                ip,
                username,
                password,
                'echo __SSH_READY__',
                connect_timeout=8,
                idle_timeout=8,
                total_timeout=15,
            )
            if ok and '__SSH_READY__' in (out or ''):
                return True, 'ready'
            last_error = out or 'ssh auth failed'
            time.sleep(5)
        return False, last_error

    def load_nezha_config(self):

        data = self.config.load_json()

        self.nezha_url.setText(data.get('url', ''))

        self.nezha_token.setText(data.get('token', ''))

        if self.nezha_url.text() and self.nezha_token.text():

            self.fetch_nezha()



    def save_nezha(self):

        self.config.save_json({'url': self.nezha_url.text(), 'token': self.nezha_token.text()})

        self.log_signal.emit("哪吒配置保存成功")

        self.fetch_nezha()



    def fetch_nezha(self):

        if not self.nezha_url.text() or not self.nezha_token.text():

            return

        self.fetcher = NezhaFetcher(self.nezha_url.text(), self.nezha_token.text())

        self.fetcher.finished.connect(self.on_nezha_fetch_finished)

        self.fetcher.start()



    def on_nezha_fetch_finished(self, mapping, status):

        self.nezha_ip_map = mapping

        if status != "OK":

            self.log_signal.emit(f"⚠️ 哪吒数据刷新异常：{status}")

        if self.current_instances:

            self.update_instance_table(self.current_instances)



    def open_firewall(self):

        acc = self.get_selected_account()

        if not acc:

            QMessageBox.warning(self, "提示", "请选择账号")

            return



        self.firewall_btn_signal.emit(False)

        self.log_signal.emit(f"[{acc[1]}] 开始配置全开放防火墙...")



        def worker():

            try:

                gcp = GCPService(acc[3], acc[2], acc[1], acc[4], acc[5])

                self.emit_account_proxy_status(acc, gcp, "配置全开放防火墙")

                success, msg = gcp.create_open_firewall_rules()

                prefix = " if success else "

                self.log_signal.emit(f"[{acc[1]}] {prefix} {msg}")

            except Exception as e:

                self.log_signal.emit(f"[{acc[1]}] 防火墙处理异常：{e}")

            finally:

                self.firewall_btn_signal.emit(True)



        threading.Thread(target=worker, daemon=True).start()



    def load_layout_config(self):

        self.config.load_layout()

        if self.config.config.has_section('Layout'):

            data = self.config.config['Layout']

            try:

                w = int(data.get('width', 1250))

                h = int(data.get('height', 880))

                self.resize(w, h)

                

                # Splitter sizes

                if data.get('v_splitter'):

                    v_raw = data.get('v_splitter', '')

                    v_sizes = [int(x) for x in v_raw.split('|') if x]

                    if v_sizes:

                        self.v_splitter.setSizes(v_sizes)

                if data.get('h_splitter'):

                    h_raw = data.get('h_splitter', '')

                    h_sizes = [int(x) for x in h_raw.split('|') if x]

                    if h_sizes:

                        self.h_splitter.setSizes(h_sizes)

                

                if data.get('command_splitter') and hasattr(self, 'command_splitter'):

                    c_sizes = [int(x) for x in data.get('command_splitter').split('|') if x]

                    if c_sizes:

                        self.command_splitter.setSizes(c_sizes)

                

                # Column widths - account table

                if data.get('account_col_widths'):

                    widths = [int(x) for x in data.get('account_col_widths').split('|')]

                    for i, w in enumerate(widths):

                        if i < self.account_table.columnCount():

                            self.account_table.setColumnWidth(i, w)

                

                # Column widths - instances table

                if data.get('instances_col_widths'):

                    inst_widths = [int(x) for x in data.get('instances_col_widths').split('|')]

                    for i, w in enumerate(inst_widths):

                        if i < self.instances_table.columnCount():

                            self.instances_table.setColumnWidth(i, w)

                

                # Row height

                if data.get('row_height'):

                    rh = int(data.get('row_height', 28))

                    self.account_table.verticalHeader().setDefaultSectionSize(rh)

                    self.instances_table.verticalHeader().setDefaultSectionSize(rh)

                    self.log_signal.emit(f"[布局] 已加载记 行高 {rh}px")

                    

                self.log_signal.emit("[布局] 布局加载成功")

            except Exception as e:

                self.log_signal.emit(f"[布局] 加载异常: {e}")



    def closeEvent(self, event):

        try:

            if getattr(self, 'api_server', None):

                self.api_server.stop()

        except Exception:

            pass

        try:

            col_widths = [str(self.account_table.columnWidth(i)) for i in range(self.account_table.columnCount())]

            inst_col_widths = [str(self.instances_table.columnWidth(i)) for i in range(self.instances_table.columnCount())]

            self.config.save_layout({

                'width': self.width(),

                'height': self.height(),

                'v_splitter': '|'.join(map(str, self.v_splitter.sizes())),

                'h_splitter': '|'.join(map(str, self.h_splitter.sizes())),

                'command_splitter': '|'.join(map(str, self.command_splitter.sizes())) if hasattr(self, 'command_splitter') else '',

                'account_col_widths': '|'.join(col_widths),

                'instances_col_widths': '|'.join(inst_col_widths)

            })

            self.log_signal.emit("[布局] 布局已保")

        except Exception as e:

            self.log_signal.emit(f"[布局] 保存失败: {e}")

        try:

            if hasattr(self, 'db') and getattr(self.db, 'conn', None):

                self.db.conn.close()

        except Exception:

            pass

        event.accept()



    def update_regions(self):

        self.region_box.clear()

        regions = FREE_REGIONS if self.free_radio.isChecked() else PAID_REGIONS

        self.region_box.addItems(list(regions.keys()) + ["随机选择 (Random)"])



    def filter_accounts(self, text):

        keyword = text.lower()

        for i in range(self.account_table.rowCount()):

            values = []

            for j in range(2, 6):

                item = self.account_table.item(i, j)

                values.append(item.text().lower() if item else '')

            match = any(keyword in value for value in values)

            self.account_table.setRowHidden(i, not match)



    def on_account_table_double_click(self, row, col):

        if col == 4:

            item = self.account_table.item(row, col)

            if item:

                self.account_table.editItem(item)

            return

        elif col == 2:

            email_item = self.account_table.item(row, 2)

            if email_item and email_item.text():

                QApplication.clipboard().setText(email_item.text())

                self.log_signal.emit(f"邮箱 {email_item.text()} 已复制")

        elif col == 3:

            project_item = self.account_table.item(row, 3)

            if project_item and project_item.text():

                QApplication.clipboard().setText(project_item.text())

                self.log_signal.emit(f"ProjectID {project_item.text()} 已复制")



    def toggle_select_all(self):

        if self.account_table.rowCount() == 0:

            return

        state = not self.account_table.cellWidget(0, 0).isChecked()

        for i in range(self.account_table.rowCount()):

            self.account_table.cellWidget(i, 0).setChecked(state)



    def delete_selected_account(self):

        deleted = 0

        for i in range(self.account_table.rowCount() - 1, -1, -1):

            checkbox = self.account_table.cellWidget(i, 0)

            id_item = self.account_table.item(i, 1)

            if checkbox and checkbox.isChecked() and id_item:

                self.db.delete_account(id_item.text())

                deleted += 1

        self.refresh_account_table()

        if deleted:

            self.log_signal.emit(f"🗑已删{deleted} 个账号")



    def on_account_edit(self, item):

        # 避免在刷新表格时触发死循环
        if not hasattr(self, '_is_refreshing') or not self._is_refreshing:

            row = item.row()

            col = item.column()

            id_item = self.account_table.item(row, 1)

            if not id_item:

                return

            acc_id = id_item.text()

            

            if col == 4:  # 代理
                proxy_text = item.text().strip()

                previous_type_item = self.account_table.item(row, 5)

                previous_type = previous_type_item.text().strip() if previous_type_item else 'HTTPS'

                parsed_proxy = parse_proxy_input(proxy_text, fallback_proxy_type=previous_type, require_protocol=bool(proxy_text))



                if not parsed_proxy.get('ok'):

                    QMessageBox.warning(self, "代理格式错误", parsed_proxy.get('error', proxy_formats_help_text()))

                    self.log_signal.emit(f"账号代理格式无法识别\n{parsed_proxy.get('error', proxy_formats_help_text())}")

                    self.account_table.blockSignals(True)

                    try:

                        item.setText('')

                    finally:

                        self.account_table.blockSignals(False)

                    self.db.update_account(acc_id, proxy='')

                    return



                new_type = parsed_proxy.get('proxy_type', previous_type)

                

                # 更新数据库（代理和协议类型同时更新）

                self.db.update_account(acc_id, proxy=proxy_text, proxy_type=new_type)

                

                # 更新协议列显示（临时屏蔽信号以防递归）
                self.account_table.blockSignals(True)

                try:

                    type_item = self.account_table.item(row, 5)

                    if type_item:

                        type_item.setText(new_type)

                finally:

                    self.account_table.blockSignals(False)

                

            elif col == 5:  # 协议                proxy_type = item.text().strip()

                self.db.update_account(acc_id, proxy_type=proxy_type)



    def batch_import(self):

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择 JSON 密钥文件",
            "",
            "JSON (*.json)"
        )

        if not paths:
            return

        self.import_json_accounts(paths, source_label="批量导入")


    def test_nezha(self):

        """修复测试连接，适配真实面板结构"""

        if not self.nezha_url.text() or not self.nezha_token.text():

            QMessageBox.warning(self, "提示", "请填写面板地址和Token")

            return



        try:

            api = NezhaAPI(self.nezha_url.text(), self.nezha_token.text())

            success, res = api.get_server_list()

            if success:

                # 显示正确的服务器数量（你的面板有7台）

                QMessageBox.information(self, "成功", f"连接成功！服务器数量：{len(res)}")

                # 自动刷新IP-名称映射

                self.fetch_nezha()

            else:

                QMessageBox.critical(self, "失败", f"连接失败：{res}")

        except Exception as e:

            QMessageBox.critical(self, "严重错误", f"测试连接时出错：{str(e)}")





    def clear_logs(self):
        """清空命令输入框"""
        self.command_input.clear()

    def update_exec_result(self, name, success, output):

        """在主线程中更新实例列表中的执行结果"""



        for row in range(self.instances_table.rowCount()):

            name_item = self.instances_table.item(row, 0)

            if name_item and name_item.text() == name:

                short_output = output[:200].replace('\n', ' | ') if output else "无输出"

                result_text = f"{chr(9989) if success else chr(10060)} {short_output}"

                result_item = QTableWidgetItem(result_text)

                result_item.setForeground(QColor("#34a853") if success else QColor("#ea4335"))

                self.instances_table.setItem(row, 5, result_item)

                break



    def execute_commands(self):

        """执行命令"""

        if getattr(self, 'cmd_mode_post_create', None) and self.cmd_mode_post_create.isChecked():
            QMessageBox.information(self, "提示", "当前为“创建后执行”模式：命令会在创建实例成功后自动执行。\n如需对已有实例执行，请切换到“普通执行”。")
            return

        if not check_paramiko():

            QMessageBox.warning(self, "提示", "paramiko未安装，请运 pip install paramiko")

            return

            

        selected = self.get_selected_instances()

        if not selected:

            QMessageBox.warning(self, "提示", "请先在实例列表中选择要执行命令的实例")

            return

        

        cmd = self.command_input.toPlainText().strip()

        if not cmd:

            QMessageBox.warning(self, "提示", "请输入要执行的命")

            return

        

        self.execute_btn.setEnabled(False)

        self.stop_btn.setEnabled(True)

        

        self.log_signal.emit(f"开始执行命令 {cmd} (实例 {len(selected)})")

        

        # 在后台线程执行SSH，避免阻塞UI

        def ssh_worker():

            try:

                # 先统一预取所有实例的密码（避免多线程竞争UI状态）

                tasks = []

                for inst in selected:

                    ip = inst.get('ip', '')

                    name = inst.get('name', '')

                    

                    password = self.instance_password_cache.get(name, '')

                    if not password:

                        password = self.db.get_vm_password(name) or ''

                    if not password:

                        acc = self.get_selected_account()

                        if acc and self.is_root_password_mode():

                            password = self.root_password_edit.text() or 'root'

                        else:

                            password = 'root'

                    

                    tasks.append((name, ip, password))

                

                self._ssh_stop_flag = False

                

                # 并发执行SSH命令

                with ThreadPoolExecutor(max_workers=20) as executor:

                    def _make_callback(inst_name):

                        """闭包——避lambda 循环变量捕获陷阱"""

                        def _cb(text):

                            self.log_signal.emit(f"[{inst_name}] {text.rstrip()}")

                        return _cb



                    future_to_task = {

                        executor.submit(self.run_ssh_command, ip, 'root', pwd, cmd,

                                        log_callback=_make_callback(name)): (name, ip)

                        for name, ip, pwd in tasks

                    }

                    

                    for future in as_completed(future_to_task):

                        if self._ssh_stop_flag:

                            # 停止标志触发，取消剩余任务
                            for f in future_to_task:

                                f.cancel()

                            break

                        

                        name, ip = future_to_task[future]

                        try:

                            success, output = future.result()

                            # 实时输出已在 run_ssh_command log_callback 中流过，不再汇总重复打印
                            self.exec_result_signal.emit(name, success, output)

                        except Exception as e:

                            self.log_signal.emit(f"[{name}] ❌异常 {str(e)}")

                

                if not self._ssh_stop_flag:

                    self.log_signal.emit(f"命令执行完成")

            finally:

                self._ssh_stop_flag = False

                self.exec_finished_signal.emit()

        

        threading.Thread(target=ssh_worker, daemon=True).start()

    

    def run_ssh_command(self, ip, username, password, command,
                        connect_timeout=None, idle_timeout=None, total_timeout=None,
                        keepalive_interval=None, log_callback=None):
        """增强版 SSH 执行函数 v6.9
        - TCP Keepalive：防止 NAT 防火墙自动断开连接
        - 流式读取 0ms 高频轮询，实时捕捉所有输出
        - 三级超时保护：连接超时 / 空闲超时 / 总计超时
        - 自动 ANSI 清理 + 输出结果截断
        """
        import paramiko
        import select
        import time
        import socket
        import re

        # 使用用户参数或回退到全局默认值
        connect_timeout = connect_timeout if connect_timeout is not None else self.ssh_connect_timeout
        idle_timeout = idle_timeout if idle_timeout is not None else self.ssh_idle_timeout
        total_timeout = total_timeout if total_timeout is not None else self.ssh_total_timeout
        keepalive = keepalive_interval if keepalive_interval is not None else self.ssh_keepalive

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            connect_kwargs = dict(
                hostname=ip,
                port=22,
                username=username,
                timeout=connect_timeout,
                banner_timeout=connect_timeout,
                auth_timeout=connect_timeout,
            )
            if password:
                # Prefer password auth when a password is provided, to avoid extra delays from key lookups.
                connect_kwargs["password"] = password
                connect_kwargs["allow_agent"] = False
                connect_kwargs["look_for_keys"] = False
            else:
                # SSH key mode: try system keys / ssh-agent (if available).
                connect_kwargs["password"] = None
                connect_kwargs["allow_agent"] = True
                connect_kwargs["look_for_keys"] = True

            ssh.connect(**connect_kwargs)

            transport = ssh.get_transport()
            if transport:
                transport.set_keepalive(keepalive)
                try:
                    sock = transport.sock
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except Exception:
                    pass

            stdin, stdout, stderr = ssh.exec_command(command, timeout=total_timeout)
            channel = stdout.channel
            channel.settimeout(idle_timeout)

            start_time = time.time()
            last_data_time = time.time()
            output_chunks = []
            error_chunks = []
            log_buffer = []
            last_flush_time = time.time()

            SSH_POLL_INTERVAL = 0.01
            SSH_BUF_SIZE = 65536

            while True:
                if time.time() - start_time > total_timeout:
                    channel.close()
                    return False, f"命令执行超过{total_timeout}秒总限制，已强制断开"
                if time.time() - last_data_time > idle_timeout:
                    channel.close()
                    return False, f"命令{idle_timeout}秒无新输出，已断开"

                r, _, _ = select.select([channel], [], [], SSH_POLL_INTERVAL)
                if r:
                    try:
                        data = channel.recv(SSH_BUF_SIZE)
                        if data:
                            last_data_time = time.time()
                            output_chunks.append(data)
                            if log_callback:
                                try:
                                    decoded = data.decode('utf-8', errors='ignore')
                                    if decoded:
                                        log_buffer.append(decoded)
                                        if time.time() - last_flush_time > 0.1 or sum(len(s) for s in log_buffer) > 1024:
                                            log_callback("".join(log_buffer))
                                            log_buffer.clear()
                                            last_flush_time = time.time()
                                except Exception: pass
                        else: break

                        if stderr.channel.recv_ready():
                            err = stderr.read(SSH_BUF_SIZE)
                            if err:
                                error_chunks.append(err)
                                if log_callback:
                                    try:
                                        decoded = err.decode('utf-8', errors='ignore')
                                        if decoded:
                                            log_buffer.append(decoded)
                                            if time.time() - last_flush_time > 0.1 or sum(len(s) for s in log_buffer) > 1024:
                                                log_callback("".join(log_buffer))
                                                log_buffer.clear()
                                                last_flush_time = time.time()
                                    except Exception: pass
                    except socket.timeout: continue
                    except Exception: break

            if log_buffer and log_callback:
                log_callback("".join(log_buffer))
                log_buffer.clear()

            time.sleep(0.1)
            try:
                while channel.recv_ready():
                    rest = channel.recv(SSH_BUF_SIZE)
                    if rest: output_chunks.append(rest)
                    else: break
            except Exception: pass
            try:
                while stderr.channel.recv_ready():
                    rest = stderr.read(SSH_BUF_SIZE)
                    if rest: error_chunks.append(rest)
                    else: break
            except Exception: pass

            output = b''.join(output_chunks).decode('utf-8', errors='ignore')
            error = b''.join(error_chunks).decode('utf-8', errors='ignore')
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output).strip()
            error = ansi_escape.sub('', error).strip()

            exit_status = channel.recv_exit_status()
            return (exit_status == 0), output if output else error
        except Exception as e:
            return False, str(e)
        finally:
            ssh.close()

    def stop_execution(self):

        """停止执行"""

        self._ssh_stop_flag = True

        self.log_signal.emit("正在停止并发任务...")

        self.execute_btn.setEnabled(True)

        self.stop_btn.setEnabled(False)



    def eventFilter(self, obj, event):

        """命令输入框：Enter 执行命令，Shift+Enter 换行"""

        if obj in getattr(self, 'account_drop_targets', ()):
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                mime_data = event.mimeData()
                json_paths = []

                if mime_data and mime_data.hasUrls():
                    json_paths = [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]

                if self._normalize_json_paths(json_paths):
                    event.acceptProposedAction()
                    return True

            elif event.type() == QEvent.Type.Drop:
                mime_data = event.mimeData()
                json_paths = []

                if mime_data and mime_data.hasUrls():
                    json_paths = [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]

                if self._normalize_json_paths(json_paths):
                    self.import_json_accounts(json_paths, source_label="拖拽导入")
                    event.acceptProposedAction()
                    return True

        if obj == getattr(self, 'command_input', None) and event.type() == QEvent.Type.KeyPress:

            key = event.key()

            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:

                if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):

                    self.execute_commands()

                    return True

        return super().eventFilter(obj, event)


if __name__ == "__main__":

    import traceback

    import io

    try:

        if getattr(sys.stdout, 'buffer', None):

            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

        if getattr(sys.stderr, 'buffer', None):

            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

    except Exception:

        pass


    print("=" * 60)

    print("GCP Manager v7.6 (基于v7.3 + HTTP/HTTPS开放 + 全开防火墙)")

    print("=" * 60)
    if not check_pysocks():
        print("[!] SOCKS5: PySocks 未安装，如需 SOCKS5 代理请运行: pip install pysocks")
    else:
        print("[✓] SOCKS5: PySocks 已安装，SOCKS5 代理可用")


    try:

        print("[1] Creating QApplication...")

        set_windows_app_user_model_id()

        app = QApplication(sys.argv)

        app.setWindowIcon(QIcon(resource_path(APP_ICON_FILE)))

        print("    OK")

        

        print("[2] Creating main window...")

        window = GCPManagerApp()

        print("    OK")

        

        print("[3] Showing window...")

        window.show()

        print("    OK")

        

        print("=" * 60)

        print("All OK, entering event loop...")

        print("=" * 60)

        sys.exit(app.exec())

        

    except Exception as e:

        print(f"\nFAILED: {e}")

        traceback.print_exc()

        input("Press Enter to exit...")

        sys.exit(1)

