import _thread
import gzip
import json
import logging
import re
import time
from queue import Queue

import requests
import websocket

import urllib
from google.protobuf import json_format

import main
from .dy_pb2 import PushFrame
from .dy_pb2 import Response
from .dy_pb2 import MatchAgainstScoreMessage
from .dy_pb2 import LikeMessage
from .dy_pb2 import MemberMessage
from .dy_pb2 import GiftMessage
from .dy_pb2 import ChatMessage
from .dy_pb2 import SocialMessage
from .dy_pb2 import RoomUserSeqMessage

liveRoomId = None
ttwid = None
roomStore = None
liveRoomTitle = None
q = None
ws = None
isCloseWss = True


def onMessage(ws: websocket.WebSocketApp, message: bytes):
    wssPackage = PushFrame()
    wssPackage.ParseFromString(message)
    logId = wssPackage.logId
    decompressed = gzip.decompress(wssPackage.payload)
    payloadPackage = Response()
    payloadPackage.ParseFromString(decompressed)
    # 发送ack包
    if payloadPackage.needAck:
        sendAck(ws, logId, payloadPackage.internalExt)
    # WebcastGiftMessage
    for msg in payloadPackage.messagesList:
        if msg.method == 'WebcastMatchAgainstScoreMessage':
            unPackMatchAgainstScoreMessage(msg.payload)
            continue

        if msg.method == 'WebcastLikeMessage':
            unPackWebcastLikeMessage(msg.payload)
            continue

        if msg.method == 'WebcastMemberMessage':
            unPackWebcastMemberMessage(msg.payload)
            continue
        if msg.method == 'WebcastGiftMessage':
            unPackWebcastGiftMessage(msg.payload)
            continue
        if msg.method == 'WebcastChatMessage':
            unPackWebcastChatMessage(msg.payload)
            continue

        if msg.method == 'WebcastSocialMessage':
            unPackWebcastSocialMessage(msg.payload)
            continue

        if msg.method == 'WebcastRoomUserSeqMessage':
            unPackWebcastRoomUserSeqMessage(msg.payload)
            continue

        logging.info('[onMessage] [⌛️方法' + msg.method + '等待解析～] [房间Id：' + liveRoomId + ']')


# 直播间人数消息
def unPackWebcastRoomUserSeqMessage(data):
    roomUserSeqMessage = RoomUserSeqMessage()
    roomUserSeqMessage.ParseFromString(data)
    data = json_format.MessageToDict(roomUserSeqMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[WebcastRoomUserSeqMessage] [直播间人数信息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    q.put(json.dumps(data))
    return data


# 关注消息
def unPackWebcastSocialMessage(data):
    socialMessage = SocialMessage()
    socialMessage.ParseFromString(data)
    data = json_format.MessageToDict(socialMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackWebcastSocialMessage] [➕直播间关注消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    # q.put(json.dumps(data))
    return data


# 普通消息
def unPackWebcastChatMessage(data):
    chatMessage = ChatMessage()
    chatMessage.ParseFromString(data)
    data = json_format.MessageToDict(chatMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackWebcastChatMessage] [📧直播间弹幕消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    q.put(json.dumps(data))
    return data


# 礼物消息
def unPackWebcastGiftMessage(data):
    giftMessage = GiftMessage()
    giftMessage.ParseFromString(data)
    data = json_format.MessageToDict(giftMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackWebcastGiftMessage] [🎁直播间礼物消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    # q.put(json.dumps(data))
    return data


# xx成员进入直播间消息
def unPackWebcastMemberMessage(data):
    memberMessage = MemberMessage()
    memberMessage.ParseFromString(data)
    data = json_format.MessageToDict(memberMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackWebcastMemberMessage] [🚹🚺直播间成员加入消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    q.put(json.dumps(data))
    return data


# 点赞
def unPackWebcastLikeMessage(data):
    likeMessage = LikeMessage()
    likeMessage.ParseFromString(data)
    data = json_format.MessageToDict(likeMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackWebcastLikeMessage] [👍直播间点赞消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    q.put(json.dumps(data))
    return data


# 解析WebcastMatchAgainstScoreMessage消息包体
def unPackMatchAgainstScoreMessage(data):
    matchAgainstScoreMessage = MatchAgainstScoreMessage()
    matchAgainstScoreMessage.ParseFromString(data)
    data = json_format.MessageToDict(matchAgainstScoreMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackMatchAgainstScoreMessage] [🤷不知道是啥的消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


# 发送Ack请求
def sendAck(ws, logId, internalExt):
    obj = PushFrame()
    obj.payloadType = 'ack'
    obj.logId = logId
    sdata = bytes(internalExt, encoding="utf8")
    obj.payloadType = sdata
    data = obj.SerializeToString()
    ws.send(data, websocket.ABNF.OPCODE_BINARY)
    logging.info('[sendAck] [🌟发送Ack] [房间Id：' + liveRoomId + '] ====> 房间🏖标题【' + liveRoomTitle + '】')


def onError(ws, error):
    print("error", error)
    logging.error('[onError] [webSocket Error事件] [房间Id：' + liveRoomId + ']')


def onClose(ws, a, b):
    logging.info('[onClose] [webSocket Close事件] [房间Id：' + liveRoomId + ']')


def onOpen(ws):
    q.put(json.dumps(roomStore))
    _thread.start_new_thread(ping, (ws,))
    logging.info('[onOpen] [webSocket Open事件] [房间Id：' + liveRoomId + ']')


# 发送ping心跳包
def ping(ws):
    while isCloseWss:
        obj = PushFrame()
        obj.payloadType = 'hb'
        data = obj.SerializeToString()
        ws.send(data, websocket.ABNF.OPCODE_BINARY)
        logging.info('[ping] [💗发送ping心跳] [房间Id：' + liveRoomId + '] ====> 房间🏖标题【' + liveRoomTitle + '】')
        time.sleep(10)


def wssServerStart(roomId, signature):
    global liveRoomId, ws, isCloseWss, ttwid
    isCloseWss = True
    liveRoomId = roomId
    websocket.enableTrace(False)
    webSocketUrl = f"wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/?app_name=douyin_web&version_code=180800&webcast_sdk_version=1.0.7&update_version_code=1.0.7&compress=gzip&device_platform=web&cookie_enabled=true&screen_width=2560&screen_height=1440&browser_language=zh-CN&browser_platform=MacIntel&browser_name=Mozilla&browser_version=5.0%20(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/114.0.0.0%20Safari/537.36&browser_online=true&tz_name=Asia/Shanghai&cursor=t-1689910648216_r-1_d-1_u-1_h-1&internal_ext=internal_src:dim|" \
                   f"wss_push_room_id:" + roomId + "|wss_push_did:7252246626075444791|dim_log_id:20230721113728D4784D39ABD1808DDE56|first_req_ms:1689910648120|fetch_time:1689910648216|seq:1|wss_info:0-1689910648216-0-0|wrds_kvs:WebcastRoomStatsMessage-1689910647064988492_WebcastRoomRankMessage-1689910635114178600_WebcastInRoomBannerMessage-GrowthCommonBannerSubSyncKey-1689902463050407648_HighlightContainerSyncData-1_InputPanelComponentSyncData-1689896823190593251&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1&user_unique_id=&im_path=/webcast/im/fetch/" \
                                                   f"&room_id=" + roomId + "&identity=audience&heartbeatDuration=0&signature=" + signature
    h = {
        'Cookie': 'ttwid=' + ttwid,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    }
    # 创建一个长连接
    ws = websocket.WebSocketApp(
        webSocketUrl, on_message=onMessage, on_error=onError, on_close=onClose,
        on_open=onOpen,
        header=h
    )
    ws.run_forever()


def wssStop():
    global isCloseWss
    isCloseWss = False
    ws.close()


def parseLiveRoomUrl(url, q1: Queue):
    h = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'cookie': '__ac_nonce=0638733a400869171be51',
    }
    res = requests.get(url=url, headers=h)
    global ttwid, roomStore, liveRoomId, liveRoomTitle, q
    q = q1
    data = res.cookies.get_dict()
    ttwid = data['ttwid']
    res = res.text
    res = re.search(r'<script id="RENDER_DATA" type="application/json">(.*?)</script>', res)
    res = res.group(1)
    res = urllib.parse.unquote(res, encoding='utf-8', errors='replace')
    res = json.loads(res)
    roomStore = res['app']['initialState']['roomStore']
    liveRoomId = roomStore['roomInfo']['roomId']
    liveRoomTitle = roomStore['roomInfo']['room']['title']
    signature_str = roomStore['roomInfo']["room"]['cover']['url_list'][0]
    last_equal_index = signature_str.rfind('=')
    signature = signature_str[last_equal_index + 1:]
    wssServerStart(liveRoomId, signature)
