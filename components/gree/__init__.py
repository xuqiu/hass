"""
文件名：gree.py.
格力云控的控件,通过逆向gree+ 模拟app控制格力中央空调
"""
import time
import json
import datetime
import hashlib
import requests
import logging
import voluptuous as vol
import cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "gree"
GREE_KEY = "d15cb842b7fd704ebcf8276f34cbd771"
SEP = "_"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required('user'): cv.string,
                vol.Required('password'): cv.string,
            }),
    },
    extra=vol.ALLOW_EXTRA)

def setup(hass, config):
    _LOGGER.info("初始化格力云控")
    conf = config[DOMAIN]
    # 获得具体配置项信息
    user = conf.get('user')
    password = conf.get('password')
    client = GreeCloud(hass, config, user, password)

    print("aaa")

    def start_scene(call):
        client._start_scene(call.data.get("id"))

    hass.services.register(DOMAIN, 'start_scene', start_scene)

    _LOGGER.info("初始化gree完毕")
    return True


class GreeCloud:
    def __init__(self, hass, config, user=None, password=None):
        self._user = user
        self._password = password
        self._request = requests.session()
        self._cookies = {}
        self._headers = {'Host': 'account.xiaomi.com',
                         'Connection': 'keep-alive',
                         'Upgrade-Insecure-Requests': '1',
                         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                         'Accept-Encoding': 'gzip, deflate, br',
                         'Accept-Language': 'zh-CN,zh;q=0.9'}
        if not self._login():
            _LOGGER.error("登录失败")
            return
        self._get_home_dev()
        self._get_scenes(hass)
        # self._start_scenes(2)

    def _login(self):
        url = 'https://grih.gree.com/App/UserLoginV2'
        request = UserLoginRequest.gen(self._user, self._password)
        response = self._post(url, request)
        if response['r'] != 200:
            return False
        self._uid = response['uid']
        self._token = response['token']
        return True

    def _get_home_dev(self):
        url = 'https://grih.gree.com/App/GetDevsOfUserHomes'
        request = HomeDevRequest.gen(self._uid, self._token)
        response = self._post(url, request)
        if response['r'] != 200:
            return False
        self._home_id = response['homes'][0]['homeId']
        self._home_name = response['homes'][0]['homeName']
        self._devs = response['homes'][0]['devs']
        return True

    def _get_scenes(self, hass):
        url = 'https://grih.gree.com/App/GetScenes'
        request = GetScenesRequest.gen(self._uid, self._home_id, self._token)
        response = self._post(url, request)
        if response['r'] != 200:
            return False
        scene_list = response['scene']
        attr = {}
        for scene in scene_list:
            attr[scene['sceneName']] = scene['sceneId']
        hass.states.set(DOMAIN+".scene_list", len(scene_list), attributes=attr)
        return True

    def _start_scene(self, scene_id):
        url = 'https://grih.gree.com/App/StartOrCancelScene'
        request = SceneRequest.gen(self._uid, self._home_id, scene_id, self._token)
        response = self._post(url, request)
        if response['r'] != 200:
            #登陆超时重登陆
            if response['r'] == 402:
                self._login()
                response = self._post(url, request)
                if response['r'] == 200:
                    return True
            return False
        return True

    def _post(self, url, data):
        _LOGGER.info(data.to_json())
        r = self._request.post(url, headers=self._headers, data=data.to_json(), timeout=30, cookies=self._cookies, verify=False)
        _LOGGER.info(r.text)
        return json.loads(r.text)


class JsonObject:
    def to_dict(self):
        _dict = {}
        _dict.update(self.__dict__)
        for i in _dict:
            _v = _dict[i]
            if isinstance(_v, JsonObject):
                _dict[i] = _v.to_dict()
        return _dict

    def to_json(self):
        return json.dumps(self.to_dict())


class Api(JsonObject):
    def __init__(self):
        self.appId = "5686063144437916735"
        self.r = 0
        self.t = ""
        self.vc = ""

    @staticmethod
    def gen():
        api = Api()
        now = datetime.datetime.utcnow()
        api.t = now.strftime("%Y-%m-%d %H:%M:%S")
        api.r = (int(round(time.time() * 1000)))
        api.vc = md5(api.appId + SEP + GREE_KEY + SEP + api.t + SEP + str(api.r))
        return api


class UserLoginRequest(JsonObject):
    @staticmethod
    def gen(user, pwd):
        request = UserLoginRequest()
        request.app = "æ ¼å\u008A\u009B+"
        request.appver = "201901178"
        request.devId = "ffffffff-f534-9766-ffff-ffffc2e834d9"
        request.devModel = "MuMu"
        request.api = Api.gen()
        request.user = user
        request.t = request.api.t
        request.psw = md5(md5(md5(pwd) + pwd) + request.t)
        request.datVc = get_dat_vc(request.user, request.psw, request.t)
        return request


class HomeDevRequest(JsonObject):

    @staticmethod
    def gen(uid, token):
        request = HomeDevRequest()
        request.api = Api.gen()
        request.uid = uid
        request.token = token
        request.datVc = get_dat_vc(request.token, request.uid)
        return request


class GetScenesRequest(JsonObject):
    @staticmethod
    def gen(uid, home_id, token):
        request = GetScenesRequest()
        request.api = Api.gen()
        request.uid = uid
        request.homeId = home_id
        request.token = token
        request.datVc = get_dat_vc(request.token, request.uid, request.homeId)
        return request


class SceneRequest(JsonObject):
    @staticmethod
    def gen(uid, home_id, sceneId, token):
        request = GetScenesRequest()
        request.api = Api.gen()
        request.uid = uid
        request.homeId = home_id
        request.sceneId = sceneId
        request.opt = 1
        request.token = token
        request.datVc = get_dat_vc(request.token, request.uid, request.homeId, request.sceneId, request.opt)
        return request


def get_dat_vc(*datas):
    result = GREE_KEY
    for data in datas:
        result = result + SEP + str(data)
    return md5(result)


def md5(raw):
    m = hashlib.md5()
    m.update(raw.encode("utf8"))
    return m.hexdigest()
