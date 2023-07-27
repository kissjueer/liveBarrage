import json
import logging
import sys
from queue import Queue

from douyin import dy
from kuaishou import KsLive

from PyQt6 import QtCore
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QHBoxLayout, QComboBox, QPushButton, QTextBrowser, QMainWindow, QCheckBox, QLineEdit
from PyQt6.QtCore import Qt, QThread

ks = KsLive.Tool()

class BarrageHelper(QWidget):

    def __init__(self):
        super().__init__()
        self.layout = None
        self.topWinCheckBox = None
        self.noticeLabel = None
        self.r = None
        self.dyThread = None
        self.win = None
        self.liveAddrLabel = None
        self.liveAddrEdit = None
        self.protcolLabel = None
        self.protcoComboBox = None
        self.connectButton = None
        self.initUI()
        global win
        win = self

    def initUI(self):
        self.setWindowTitle('直播弹幕助手')
        self.resize(400, 160)
        self.liveAddrLabel = QLabel('直播地址：', self)
        self.liveAddrEdit = QLineEdit('', self)
        self.protcolLabel = QLabel('平台：', self)
        self.protcoComboBox = QComboBox(self)
        self.connectButton = QPushButton('进入房间', self)
        self.protcoComboBox.addItem("抖音")
        self.protcoComboBox.addItem("快手")
        self.protcoComboBox.resize(50, 20)
        self.liveAddrEdit.setFixedSize(210, 20)
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.protcolLabel)
        self.layout.addWidget(self.protcoComboBox)
        self.layout.addWidget(self.liveAddrLabel)
        self.layout.addWidget(self.liveAddrEdit)
        self.setContentsMargins(0, 40, 0, 100)
        self.connectButton.move(50, 130)
        self.setLayout(self.layout)
        self.connectButton.clicked.connect(self.click)
        self.connectButton.setStyleSheet(
            '''QPushButton{background:#1E90FF;border-radius:5px;}QPushButton:hover{background:#00BFFF;}''')
        self.topWinCheckBox = QCheckBox('顶置弹幕窗口', self)
        self.topWinCheckBox.move(280, 130)
        self.show()

    def click(self):
        winT = self.protcoComboBox.currentText()
        global winTitle
        winTitle = winT
        self.win = BarrageWin(winTitle=winT, protoType=winT)
        if self.topWinCheckBox.isChecked():
            self.win.setWindowFlags(
                QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.FramelessWindowHint)

        title = self.connectButton.text().title()
        if title == '进入房间':
            self.win.show()
            self.connectButton.setText('退出房间')
            self.connectButton.setStyleSheet(
                '''QPushButton{background:#fe2a00;border-radius:5px;}QPushButton:hover{background:#fe2a00;}''')
            global url
            url = self.liveAddrEdit.text()
            self.r = printThread(textWritten=self.win.outputWritten)
            index = self.protcoComboBox.currentIndex()
            if index == 0:
                self.dyThread = douyinMsgThread()
            if index == 1:
                self.dyThread = kuaishouMsgThread()
            self.dyThread.start()
            self.r.start()
            return
        self.connectButton.setText('进入房间')
        self.connectButton.setStyleSheet(
            '''QPushButton{background:#1E90FF;border-radius:5px;}QPushButton:hover{background:#00BFFF;}''')
        self.win.close()
        self.dyThread.exit()
        self.r.exit()


class BarrageWin(QMainWindow):

    def __init__(self, winTitle, protoType):
        super().__init__()
        self.liveLabel = None
        self.mflag = None
        self.textBrowser = None
        self.winTitle = winTitle
        self.protoType = protoType
        self.initUI()

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(self.winTitle)
        self.resize(300, 600)
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.resize(100, 100)
        self.textBrowser.move(0, 35)
        self.outputWritten('Notice ==> 正在建立直播通道请稍等～～～')
        self.liveLabel = QLabel(self.winTitle, self)
        self.liveLabel.resize(300, 30)
        self.liveLabel.setStyleSheet('color:red')
        self.liveLabel.setStyleSheet('font:20pt')
        self.liveLabel.setStyleSheet('background-color: #3B2667')

    def outputWritten(self, text):
        if self.protoType is not None and self.liveLabel is not None:
            self.liveLabel.setText(self.protoType + " | " + winTitle)

        self.textBrowser.append('\n')
        self.textBrowser.insertHtml(text)
        self.textBrowser.append('\n')
        #### 滚动到底部
        self.textBrowser.ensureCursorVisible()  # 游标可用
        cursor = self.textBrowser.textCursor()  # 设置游标
        pos = len(self.textBrowser.toPlainText())  # 获取文本尾部的位置
        cursor.setPosition(pos)  # 游标位置设置为尾部
        self.textBrowser.setTextCursor(cursor)  # 滚动到游标位置

    def resizeEvent(self, event):
        self.textBrowser.resize(event.size())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mflag = True
            self.mPosition = event.pos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            # self.setCursor(QCursor(Qt.MouseButton.OpenHandCursor))  # 更改鼠标图标

    def mouseMoveEvent(self, QMouseEvent):
        if Qt.MouseButton.LeftButton and self.mflag:
            self.move(QMouseEvent.pos() - self.mPosition)  # 更改窗口位置
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.mflag = False
        # self.setCursor(QCursor(Qt.MouseButton.ArrowCursor))


class douyinMsgThread(QThread):

    def run(self):
        dy.parseLiveRoomUrl(url, q)

    def exit(self, returnCode: int = ...):
        dy.wssStop()


class kuaishouMsgThread(QThread):
    def run(self):
        c ='didv=1684305615000; kuaishou.live.bfb1s=3e261140b0cf7444a0ba411c6f227d88; clientid=3; did=web_2e8316aa084f4072ac3bb903bec897f4; client_key=65890b29; kpn=GAME_ZONE; ksliveShowClipTip=true; did=web_ff250abd4d8fea83b57d696a73f0c105; kuaishou.live.web_st=ChRrdWFpc2hvdS5saXZlLndlYi5zdBKgAVWH7XxQSrzOgbZy7tVN7oIArNYN8OlTuho3JxWo5_qtyZYmq7MNGieNEVBb5kOcQs-ohruBuhiDuKscYy0yEYzfAZDnvN8UBjgIe7HnthTryDeMPw_0DwlYYx3nVoDNeJqoxyasRRSBCl_uKbzr6hDLdssRUbM6h0q62_LWSphAaqbvD_zl6D6Cyp-NbRGFAeaDV5D68fb5xk8Baj3EB4UaEiTUdhIhLkqeuKi4MmqrjKj9xSIgMneUMrX947c1l_mf7mgdq4V9Sf79P-jdHyUebOzVmQQoBTAB; kuaishou.live.web_ph=a6720cb88ffc1ffe546c0306dd11d75d2bf7; userId=1707554780; userId=1967769632; needLoginToWatchHD=1'
        ks.init(url, c)
        ks.wssServerStart(q)

    def exit(self, returnCode: int = ...):
        ks.wssStop()


class printThread(QThread):
    textWritten = QtCore.pyqtSignal(str)

    def run(self):
        while True:
            data = q.get()
            self.printF(data)

    def printF(self, data):
        global winTitle
        data = json.loads(data)
        if 'commentFeeds' in data.keys():
            for com in data['commentFeeds']:
                nickname = com['user']['userName']
                self.textWritten.emit('💬 <font color="pink">' + nickname + '</font>: ' + com['content'])
        if 'displayWatchingCount' in data.keys():
            total = data['displayWatchingCount']
            text = "👀当前观看人数：" + str(total)
            winTitle = text
        if 'common' not in data.keys():
            return

        if data['common']['method'] == 'WebcastMemberMessage':
            nickname = data['user']['nickName']
            self.textWritten.emit('👏 <font color="red">' + nickname + '</font>: 进入直播间')
            return

        if data['common']['method'] == 'WebcastLikeMessage':
            nickname = data['user']['nickName']
            self.textWritten.emit('💗 <font color="green">' + nickname + '</font>: 点亮了爱心')
            return

        if data['common']['method'] == 'WebcastGiftMessage':
            describe = data['common']['describe']
            self.textWritten.emit('🎁 <font color="red">' + describe + '</font>')
            return

        if data['common']['method'] == 'WebcastChatMessage':
            nickname = data['user']['nickName']
            self.textWritten.emit('💬 <font color="pink">' + nickname + '</font>: ' + data['content'])
            return

        if data['common']['method'] == 'WebcastRoomUserSeqMessage':
            total = data['total']
            totalStr = data['totalStr']
            text = "👀当前观看人数：" + str(total) + " (" + totalStr + ")"
            winTitle = text
            return


url = None
win = None
winTitle = None
q = Queue(100)


def main():
    print(sys.argv)
    app = QApplication(sys.argv)
    ex = BarrageHelper()
    sys.exit(app.exec())


if __name__ == '__main__':
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    main()
