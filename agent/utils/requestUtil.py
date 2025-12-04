import re
from hashlib import md5

import requests
import warnings

from urllib3 import encode_multipart_formdata

from config import config

# import test65_nsa

warnings.filterwarnings("ignore")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
}

proxy = {
    "http": "http://127.0.0.1:8083",
    "https": "http://127.0.0.1:8083",
}

# cookies = "test65_nsa.cookies"
cookies = """
_ga=GA1.1.359324340.1717387655; __cf_bm=jfeIgH7hOmgX46.4Ph3VnTHyKyi02C8s0Z_zCcLBEow-1717387722-1.0.1.1-.ACysxXm1Y3cTIWQ6l.C76NDMXR19Geb6RBz4Jn.h_hLsUEHQLIlkbdUBDHKBakQ2B.rpVmTmpI7.y1H6dWTMQ; jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MTczODc3NDEsImV4cCI6MTcyMDA2NjE0MSwicm9sZXMiOlsiUk9MRV9VU0VSIl0sImVtYWlsIjpudWxsLCJpZCI6IjU4NzYxMzI0LWE1MGItNGEzNi1hYWVlLWNiNjEzZTc0MjdlYyIsInBybyI6ZmFsc2UsImFkZHJlc3MiOiIweGZiRTYxNzE2MTU2N2ZBQ0JCRGIxYWE2ZEZmMTBBRTc1YjdmZjNhRjkiLCJzYWx0IjoiNTYzOGJkNzI4ZSJ9.r3f3nxmA4YoqRUei3Gc1HjHm3mVgg_mX-x_ShIkakt2JGDZKA97blb-k965ucaW4DIelWhNdhJb3HEixWrI2xSU3-vjFSbkNXRmUX-rNrZ4ipHz1gUolgLvZawl-YSdZxKSXdR73DFPZwNNb2rOvGUXAwPpx-PrM5BYYAJ0AFOer3dhSOUxBaGa8osrcILXsbkSeK1bJsh_TCivXE1p_b6jEm1mOKP5yqOIPdAN2I_q0EB8ZF5K6kx2_nSg8vkwcL90wGDDP0CAhhmDVa9GF87R3hf3vXunImuGG8Ot7iuLvKPdTeWkBh3Kkh42ADxYXXIQqC3aTUfXyA6rFUnf78Dyyp3TsT_eDyALTwzlHbqQsyeSFodG3DGTUYMWp9z1lU2hKuY_XNt6TU5d6EB1Cg-vnaIO385W5srIdFou1M6LUnVkMqa5RxbLIrZ17VyOdpvirXyODdyJ230d8qahLJH8Iz_iLklpZwWzCwJflzOx67XP573dJDn1LDtMAaMj95VZty3wukYImPX5orW0-x6ucUGVrBALQktU5AqcXyKzVg6h5ygwiinjdTSvZnhqJIbB_Wl-xHAMb2emUFyZ6tVXJ0CLdhW4TbqGJyNxm_BJ2AxaLry2QcNLaNfYeBBe8KBZB_FrY2DONVTjnZdBoodLVP_EmMf9lxUg32-O1wEM; dapp_ga_id=c9c819b2-7534-422b-a96b-ac10bd76af97; cf_clearance=OZ_WuT_5DH6IgenLaUl6JoDzphgxPNzEutHUJgBug18-1717387986-1.0.1.1-xIppU8UC9BNJE0c8FWuXY4Z40A3IY4i87SYYkWHhv5bsyMSi2sjNFCu0elbFEkAO_CZ23CS.zn.8.E3UT0VoDw; _rdt_uuid=1717387727722.57c9c165-d443-4942-9526-f61b13d78733; _ga_BTQFKMW6P9=GS1.1.1717387654.1.1.1717388050.0.0.0
""".strip()


def get_cookies(cookie_str):
    cookie_dict = {i.split("=")[0].strip(): "=".join(i.split("=")[1:]).strip() for i in cookie_str.split(";")}
    return cookie_dict


def get(url, cookies=cookies, header=None, timeout=50, session="", allow_redirects=True, stream=False, proxable=False):
    f_headers = dict.copy(headers)
    if cookies == "":
        cookies = {}
    else:
        cookies = get_cookies(cookies)
    if header == None:
        header = {}
    f_headers = dict(header, **f_headers)
    if proxable:
        proxies = proxy
    else:
        proxies = {}
    try:
        if session == "":
            resp = requests.get(url, verify=False, headers=f_headers, cookies=cookies, timeout=timeout,
                                allow_redirects=allow_redirects, stream=stream, proxies=proxies)
        else:
            resp = session.get(url, cookies=cookies, headers=f_headers, verify=False, timeout=timeout,
                               allow_redirects=allow_redirects, stream=stream, proxies=proxies)
        if resp != None and '<h1>Burp Suite Professional</h1>' in resp.text:
            raise Exception
        return {"content": resp.text, "headers": resp.headers, "status_code": resp.status_code}


    except Exception as e:
        # print(e)
        return None


def post(url, data="", cookies=cookies, header=None, timeout=5, session="", files=None, proxable=False, allow_redirects=True, changeHeader=True):
    f_headers = dict.copy(headers)
    if cookies == "":
        cookies = {}
    else:
        cookies = get_cookies(cookies)
    if header == None:
        header = {}
    if not "Content-Type" in header and not files and changeHeader:
        header = dict(header, **{"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0"})
    if files == None:
        files = {}
    f_headers = dict(header, **f_headers)
    if proxable:
        proxies = proxy
    else:
        proxies = {}
    try:
        if session == "":
            resp = requests.post(url, cookies=cookies, data=data, headers=f_headers, verify=False, timeout=timeout,
                                 files=files, proxies=proxies, allow_redirects=allow_redirects)
        else:
            resp = session.post(url, cookies=cookies, data=data, headers=f_headers, verify=False, timeout=timeout,
                                files=files, proxies=proxies, allow_redirects=allow_redirects)
        # if resp != None and '<h1>Burp Suite Professional</h1>' in resp.text:
        #     print("aa")
        #     raise Exception
        return {"content": resp.text, "headers": resp.headers, "status_code": resp.status_code}


    except Exception as e:
        # raise e
        return None

def put(url, data, headers, cookies):
    if cookies == "":
        cookies = {}
    else:
        cookies = get_cookies(cookies)
    return requests.put(url, data=data, headers=headers, cookies=cookies,verify=False, proxies=proxy, timeout=1)

class FileData:
    def __init__(self, header, data):
        self.header = header
        self.data = data


def get_file_data(filename="", filedata="", param="file", data=None):  # param: 上传文件的POST参数名
    if not data:
        data = {}
    if filename:
        data[param] = (filename, filedata)  # 名称，文件内容
    encode_data = encode_multipart_formdata(data)
    file_data = FileData({"Content-Type": encode_data[1]}, encode_data[0])
    return file_data


def session():
    return requests.session()


def get_title(resp):
    try:
        try:
            content = resp.content.decode()
        except:
            content = resp.content.decode("GBK", "ignored")
        title = re.findall("<title>(.*?)</title>", content)[0]
    except:
        title = "[空标题]"
    return title


def get_ip(url):
    if re.findall("http://(.*?)/", url):
        return re.findall("http://(.*?)/", url)
    else:
        return re.findall("http://(.*)", url)

def print_info(resp):
    if resp != None:
        print (resp.url, resp.status_code, len(resp.text), get_title(resp))

