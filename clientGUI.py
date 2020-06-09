
import os
import sys
from PyQt5 import QtWidgets, QtGui, QtCore

import image_rc
from clientCore import ClientCore

class BubbleMessage(QtWidgets.QTextEdit):

	def __init__(self, text, maxWidth):
		super().__init__()
		self.textEdit = QtWidgets.QTextEdit()
		self.setPlainText(text)
		self.setReadOnly(True)
		self.fontMetric = QtGui.QFontMetrics(self.currentFont())
		self.pointSize = self.currentFont().pointSize()
		self.width = self.calculateWidth()
		self.widthChange(maxWidth)
		self.setStyleSheet("border: none;")

	def widthChange(self, width):
		self.realWidth = width - self.pointSize*4
		if self.width > self.realWidth:
			self.setFixedSize(self.realWidth, self.calculateHeightByWidth(width))
		else:
			self.setFixedSize(self.width, self.calculateHeightByWidth(width))

	def calculateHeightByWidth(self, width):
		one_row_height = self.pointSize * 2
		number_of_row = (self.width//self.realWidth)*1.3 + 1.2
		height = number_of_row * one_row_height + self.pointSize*1.2
		return height

	def calculateWidth(self):
		widget_margins  = self.contentsMargins()
		document_margin = self.document().documentMargin()
		width = widget_margins.left()\
			  + document_margin\
			  + self.fontMetric.width(self.toPlainText())\
			  + document_margin\
			  + widget_margins.right()
		return width


class ChatWindow(QtWidgets.QWidget):

	def __init__(self, name, parent, pathDownload):
		super().__init__()
		self.name = name
		self.parent = parent
		self.pathDownload = pathDownload
		self.waittingMessage = ""
		self.waittingFileSend = ""

		self.nameLabel = QtWidgets.QLabel(self.name)
		self.nameLabel.setAlignment(QtCore.Qt.AlignCenter)

		self.messageLayout = QtWidgets.QVBoxLayout()
		self.messageLayout.addStretch()
		self.messageWidget = QtWidgets.QWidget()
		self.messageWidget.setLayout(self.messageLayout)
		self.chatWindow  = QtWidgets.QScrollArea()
		self.chatWindow.setWidgetResizable(True)
		self.chatWindow.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.chatWindow.setWidget(self.messageWidget)

		self.inputLine = QtWidgets.QLineEdit()
		self.inputSendButton = QtWidgets.QPushButton("Send")
		self.sendFileButton = QtWidgets.QPushButton("File")
		self.inputLayout = QtWidgets.QHBoxLayout()
		self.inputLayout.addWidget(self.inputLine)
		self.inputLayout.addWidget(self.inputSendButton)
		self.inputLayout.addWidget(self.sendFileButton)

		self.chatWindowLayout = QtWidgets.QVBoxLayout()
		self.chatWindowLayout.addWidget(self.nameLabel,1)
		self.chatWindowLayout.addWidget(self.chatWindow,6)
		self.chatWindowLayout.addLayout(self.inputLayout,1)
		self.chatWindowLayout.setSpacing(0)
		self.chatWindowLayout.setContentsMargins(0, 0, 0, 0)

		self.setLayout(self.chatWindowLayout)

		self.chatWindow.installEventFilter(self)
		self.inputLine.installEventFilter(self)
		self.inputSendButton.installEventFilter(self)

		self.inputSendButton.clicked.connect(self.sendMessage)
		self.sendFileButton.clicked.connect(self.choosePathFile)
	
	def resizeEvent(self, event):
		for message in [self.messageLayout.itemAt(i) for i in range(1,self.messageLayout.count())]:
			width = event.size().width()
			if self.chatWindow.verticalScrollBar().isVisible():
				width -= 20
			message.widget().widthChange(width)

	def addMessage(self, message, name=None):
		maxWidth = self.frameGeometry().width()
		if name:
			message_buble = BubbleMessage(f"{name}: {message}", maxWidth)
		else:
			message_buble = BubbleMessage(message, maxWidth)
		self.messageLayout.addWidget(message_buble)

	def sendFile(self, path):
		if not self.waittingFileSend:
			self.waittingFileSend = path	
			self.parent.sendFile(path, self.name)

	def choosePathFile(self):
		path = QtWidgets.QFileDialog.getOpenFileName(self, '')[0]
		if path:
			self.sendFile(path)
	
	def receiveFileCheck(self, name, filename, size):
		d = QtWidgets.QMessageBox(self)
		d.setText(f"{name} want to send you {filename}({size})\nDo you want to receive?")
		d.setStandardButtons(QtWidgets.QMessageBox.Yes|
							QtWidgets.QMessageBox.No)
		# d.setWindowTitle("Rec")
		return d.exec_()

	def receiveFileGetPath(self):
		path = str(QtWidgets.QFileDialog.getExistingDirectory(\
			directory=self.pathDownload, caption="Download to directory"))
		if path != "":
			self.pathDownload = path
		return self.pathDownload

	def sendFileSuccess(self, filename, recvName):
		self.waittingFileSend = ""
		self.addMessage(f"Finish sending {filename} to {recvName}", recvName)

	def sendFileRefuse(self, filename, recvName):
		self.waittingFileSend = ""
		self.addMessage(f"{filename} refuse to receive {recvName}", recvName)

	def sendFileFail(self, filename, recvName):
		self.waittingFileSend = ""
		self.addMessage(f"Error happen while sending {filename} to {recvName}", recvName)

	def recvFileFail(self, filename, sendName):
		self.addMessage(f"Error happen while receiving {filename} from {sendName}", sendName)

	def sendMessage(self):
		message = self.inputLine.text()
		self.waittingMessage = message
		self.parent.sendMessage(message, self.name)

	def sendMessageSuccess(self, message):
		self.addMessage(message)
		self.waittingMessage = ""

	def sendMessageFailDialog(self):
		d = QtWidgets.QDialog(self)
		v = QtWidgets.QVBoxLayout()
		l = QtWidgets.QLabel("Can't send message!")
		v.addWidget(l)
		d.setLayout(v)
		d.setWindowTitle("Error")
		d.exec_()

	def sendMessageFail(self):
		self.waittingMessage = ""
		self.sendMessageFailDialog()

	def eventFilter(self, src, e):
		if e.type() == QtCore.QEvent.FocusIn:
			self.parent.eventFilter(src, e)
		elif e.type() == QtCore.QEvent.KeyPress:
			if not self.waittingMessage:
				if e.key() == QtCore.Qt.Key_Return:
					self.sendMessage()
				else:
					e.accept()
		return super().eventFilter(src, e)


class ChatWidget(QtWidgets.QWidget):

	def __init__(self, parent):
		super().__init__()
		self.parent = parent
		self.listOnline = []

		self.onlineSearchLine = QtWidgets.QLineEdit()
		self.listOnlineWidget = QtWidgets.QListWidget()
		self.listChat  = QtWidgets.QListWidget()
		self.listWidget = QtWidgets.QStackedWidget()
		self.listWidget.addWidget(self.listChat)
		self.listWidget.addWidget(self.listOnlineWidget)

		self.tabLayout = QtWidgets.QVBoxLayout()
		self.tabLayout.addWidget(self.onlineSearchLine)
		self.tabLayout.addWidget(self.listWidget)

		self.chatWindowStack = QtWidgets.QStackedWidget()
		self.chatWindowLayout = QtWidgets.QVBoxLayout()
		self.chatWindowLayout.addWidget(self.chatWindowStack)

		self.chatLayout = QtWidgets.QHBoxLayout(self)
		self.chatLayout.addLayout(self.tabLayout, 3)
		self.chatLayout.addLayout(self.chatWindowLayout, 8)
		self.chatLayout.setSpacing(0)
		self.chatLayout.setContentsMargins(0, 0, 0, 0)

		self.setLayout(self.chatLayout)

		self.onlineSearchLine.installEventFilter(self)
		self.listOnlineWidget.installEventFilter(self)
		self.listChat.installEventFilter(self)
		self.chatWindowStack.installEventFilter(self)

		self.listOnlineWidget.itemClicked.connect(self.chatRequestFromOnline)
		self.listChat.itemClicked.connect(self.openChatWindow)
		
	def eventFilter(self, src, e):
		if e.type() == QtCore.QEvent.FocusIn:
			if src not in (self.onlineSearchLine, self.listOnlineWidget):
				self.switchTabWidget(0)
			else:
				self.online()
			e.accept()
		elif e.type() == QtCore.QEvent.KeyRelease:
			e.accept()
			self.searchInOnline()
		return super().eventFilter(src, e)

	def recvListOnline(self, online):
		self.listOnline = online
		self.setListOnline(self.listOnline)

	def recvOnlineName(self, name):
		if name not in self.listOnline:
			self.listOnline.append(name)
			self.setListOnline(self.listOnline)
	
	def recvOfflineName(self, name):
		if name in self.listOnline:
			self.listOnline.remove(name)
			self.setListOnline(self.listOnline)

	def searchInOnline(self):
		name = self.onlineSearchLine.text()
		ls = [user for user in self.listOnline if name in user]
		self.setListOnline(ls)

	def switchTabWidget(self, idx):
		self.listWidget.setCurrentIndex(idx)

	def online(self):
		self.parent.client.sendByName("</online_req>")

	def openChatWindow(self):
		name = self.listChat.currentItem().text()
		ls_name_chat = [self.chatWindowStack.widget(i).name for i in range(self.chatWindowStack.count())]
		self.chatWindowStack.setCurrentIndex(ls_name_chat.index(name))

	def setListOnline(self, ls):
		self.listOnlineWidget.clear()
		self.listOnlineWidget.verticalScrollBar().setValue(0)
		self.listOnlineWidget.horizontalScrollBar().setValue(0)
		for i in ls:
			self.listOnlineWidget.addItem(i)
		self.switchTabWidget(1)

	def chatRequestFromOnline(self):
		for name in self.listOnlineWidget.selectedItems():
			online_window = [self.listChat.item(i) for i in range(self.listChat.count())]
			ls_name_window = [self.listChat.itemWidget(i).name for i in online_window if self.listChat.itemWidget(i)]
			if name.text() in ls_name_window:
				idx = ls_name_window.index(name.text())
				self.chatWindowStack.setCurrentIndex(idx)
			else:
				self.chatReq(name.text())

	def chatReqRefuse(self, name):
		chat_window = self.getChatWindowByName(name)
		chat_window.sendMessageFail()
			
	def chatReq(self, name):
		self.parent.chatReq(name)
		
	def createChatWindow(self, name):
		self.listChat.addItem(name)
		self.listChat.setCurrentRow(self.listChat.count() - 1)
		chatWindow = ChatWindow(name, self, self.parent.path)
		self.chatWindowStack.addWidget(chatWindow)
		self.chatWindowStack.setCurrentWidget(chatWindow)

	def sendFile(self, path, name):
		if self.parent.chatAvailable(name):
			sizeInByte = os.path.getsize(path)
			size = self.formatSize(sizeInByte)
			self.parent.sendFile(path, name, size)
		else:
			self.chatReq(name)

	def formatSize(self, sizeInByte):
		time = -1
		while sizeInByte:
			time += 1
			remain = sizeInByte
			sizeInByte = sizeInByte//1024
		unit = ["bytes", "KB", "MB", "GB"][time]
		return f"{remain} {unit}"

	def receiveFile(self, sendPath, sendName, filename, size, sock):
		if not self.checkInListChat(sendName):
			self.createChatWindow(sendName)
		chat_window = self.getChatWindowByName(sendName)
		receiveCheck = chat_window.receiveFileCheck(sendName, filename, size)
		if receiveCheck == QtWidgets.QMessageBox.Yes:
			downPath = chat_window.receiveFileGetPath()
			self.parent.acceptReceiveFile(sendPath, downPath, filename, sendName, sock)
		else:
			filename = sendPath.split("/")[-1]
			self.parent.refuseReceiveFile(filename, sock)

	def recvFileFail(self, filename, sendName):
		chat_window = self.getChatWindowByName(sendName)
		chat_window.recvFileFail(filename, sendName)

	def sendFileSuccess(self, path, recvName):
		chat_window = self.getChatWindowByName(recvName)
		chat_window.sendFileSuccess(path, recvName)

	def sendFileRefuse(self, path, recvName):
		chat_window = self.getChatWindowByName(recvName)
		chat_window.sendFileRefuse(path, recvName)

	def sendFileFail(self, filename, recvName):
		chat_window = self.getChatWindowByName(recvName)
		chat_window.sendFileFail(filename, recvName)

	def sendMessage(self, message, name):
		if self.parent.chatAvailable(name):
			chat_window = self.getChatWindowByName(name)
			chat_window.inputLine.setText("")
			self.parent.sendMessage(message, name)
		else:
			self.chatReq(name)

	def sendMessageSuccess(self, message, recvName):
		chat_window = self.getChatWindowByName(recvName)
		chat_window.sendMessageSuccess(message)

	def checkInListChat(self, name):
		ls_name_chat = [self.chatWindowStack.widget(i).name for i in range(self.chatWindowStack.count())]
		if name in ls_name_chat:
			return True
		return False

	def getChatWindowByName(self, name):
		ls_chat_window = [self.chatWindowStack.widget(i) for i in range(self.chatWindowStack.count())]
		return [i for i in ls_chat_window if i.name == name][0]

	def connectedSuccess(self, name):
		if not self.checkInListChat(name):
			self.createChatWindow(name)
		else:
			chat_window = self.getChatWindowByName(name)
			if chat_window.waittingMessage:
				self.sendMessage(chat_window.waittingMessage, chat_window.name)
			if chat_window.waittingFileSend:
				self.sendFile(chat_window.waittingFileSend, chat_window.name)

	def receiveMessage(self, message, name):
		if self.checkInListChat(name):
			ls_name_chat = [self.chatWindowStack.widget(i).name for i in range(self.chatWindowStack.count())]
			self.chatWindowStack.widget(ls_name_chat.index(name)).addMessage(message, name)
		else:
			self.createChatWindow(name)
			chat_window = self.chatWindowStack.widget(self.chatWindowStack.count() - 1)
			chat_window.addMessage(message, name)


class LoginWidget(QtWidgets.QWidget):

	def __init__(self, parent):
		super().__init__()
		self.parent = parent

		self.message = QtWidgets.QLabel()
		self.message.setAlignment(QtCore.Qt.AlignCenter)

		self.nameLine = QtWidgets.QLineEdit()
		self.nameLine.setMinimumWidth(180)
		self.nameLine.setMaximumWidth(180)
		self.nameLine.setAlignment(QtCore.Qt.AlignCenter)
		self.nameLayout = QtWidgets.QHBoxLayout()
		self.nameLayout.addStretch()
		self.nameLayout.addWidget(self.nameLine)
		self.nameLayout.addStretch()

		self.pwLine = QtWidgets.QLineEdit()
		self.pwLine.setEchoMode(QtWidgets.QLineEdit.Password)
		self.pwLine.setMinimumWidth(180)
		self.pwLine.setMaximumWidth(180)
		self.pwLine.setAlignment(QtCore.Qt.AlignCenter)
		self.pwLayout = QtWidgets.QHBoxLayout()
		self.pwLayout.addStretch()
		self.pwLayout.addWidget(self.pwLine)
		self.pwLayout.addStretch()

		self.loginButton = QtWidgets.QPushButton("Login")
		self.loginButton.setMinimumWidth(80)
		self.loginButton.setMaximumWidth(80)
		self.signupButton = QtWidgets.QPushButton("Signup")
		self.signupButton.setMinimumWidth(80)
		self.signupButton.setMaximumWidth(80)
		self.buttonLayout = QtWidgets.QHBoxLayout()
		self.buttonLayout.addStretch()
		self.buttonLayout.addWidget(self.loginButton)
		self.buttonLayout.addWidget(self.signupButton)
		self.buttonLayout.addStretch()

		self.loginLayout = QtWidgets.QVBoxLayout(self)
		self.loginLayout.addStretch()
		self.loginLayout.addWidget(self.message)
		self.loginLayout.addLayout(self.nameLayout)
		self.loginLayout.addLayout(self.pwLayout)
		self.loginLayout.addLayout(self.buttonLayout)
		self.loginLayout.addStretch()

		self.setLayout(self.loginLayout)

		self.loginButton.clicked.connect(self.login)
		self.signupButton.clicked.connect(self.signup)

	def signup(self):
		name = self.nameLine.text()
		pw   = self.pwLine.text()
		self.parent.signupReq(name, pw)

	def login(self):
		name = self.nameLine.text()
		pw   = self.pwLine.text()
		self.parent.loginReq(name, pw)

	def signupReqAccept(self):
		message = "Đăng kí thành công"
		self.message.setText(message)
		self.nameLine.setText("")
		self.pwLine.setText("")

	def signupReqRefuse(self, message):
		self.message.setText(message)

	def loginReqRefuse(self, message):
		self.message.setText(message)


class LoadingWidget(QtWidgets.QWidget):

	def __init__(self, parent):
		super().__init__()
		self.parent = parent

		self.loadingGif = QtGui.QMovie(':/loading.gif')
		self.loadingGif.setScaledSize(QtCore.QSize(50, 50))
		self.loadingGif.setSpeed(150)
		self.loadingGif.start()

		self.loadingLabel = QtWidgets.QLabel()
		self.loadingLabel.setAlignment(QtCore.Qt.AlignCenter)
		# self.loadingLabel.setObjectName("loadingGif")
		# self.loadingLabel.setStyleSheet("image: url(:/{}.png);")
		self.loadingLabel.setMovie(self.loadingGif)
		self.loadingLabel.setAlignment(QtCore.Qt.AlignCenter)
	
		self.loadingMessage = QtWidgets.QLabel("Connecting")
		self.loadingMessage.setAlignment(QtCore.Qt.AlignCenter)

		self.loadingLayout = QtWidgets.QVBoxLayout()
		self.loadingLayout.addStretch()
		self.loadingLayout.addWidget(self.loadingLabel)
		self.loadingLayout.addWidget(self.loadingMessage)
		self.loadingLayout.addStretch()

		self.setLayout(self.loadingLayout)

class ConnectServerFailWidget(QtWidgets.QWidget):

	def __init__(self, parent):
		super().__init__()
		self.parent = parent


		self.message_1 = QtWidgets.QLabel("Can't connect to server")
		self.message_1.setAlignment(QtCore.Qt.AlignCenter)

		self.message_2 = QtWidgets.QLabel("Type server ip below")
		self.message_2.setAlignment(QtCore.Qt.AlignCenter)

		self.serverIpLine = QtWidgets.QLineEdit()
		self.serverIpLine.setMinimumWidth(180)
		self.serverIpLine.setMaximumWidth(180)
		self.serverIpLine.setAlignment(QtCore.Qt.AlignCenter)
		self.serverIpLayout = QtWidgets.QHBoxLayout()
		self.serverIpLayout.addStretch()
		self.serverIpLayout.addWidget(self.serverIpLine)
		self.serverIpLayout.addStretch()

		self.reconnectButton = QtWidgets.QPushButton("Reconnect")
		self.buttonLayout = QtWidgets.QHBoxLayout()
		self.buttonLayout.addStretch()
		self.buttonLayout.addWidget(self.reconnectButton)
		self.buttonLayout.addStretch()

		self.failLayout = QtWidgets.QVBoxLayout(self)
		self.failLayout.addStretch()
		self.failLayout.addWidget(self.message_1)
		self.failLayout.addWidget(self.message_2)
		self.failLayout.addLayout(self.serverIpLayout)
		self.failLayout.addLayout(self.buttonLayout)
		self.failLayout.addStretch()

		self.setLayout(self.failLayout)

		self.reconnectButton.clicked.connect(self.reconnect)

	def reconnect(self):
		ip = self.serverIpLine.text()
		self.parent.client.serverIp = ip
		self.parent.stackWidget.setCurrentIndex(0)
		self.parent.setUp()


class ClientGUI(QtWidgets.QWidget):

	def __init__(self):
		super().__init__()
		self.client = ClientCore(self)
		self.path = os.path.dirname(os.path.abspath(__file__))

		self.loadingWidget = LoadingWidget(self)
		self.failWidget    = ConnectServerFailWidget(self)
		self.loginWidget   = LoginWidget(self)
		self.chatWidget    = ChatWidget(self)

		self.stackWidget = QtWidgets.QStackedWidget()
		self.stackWidget.addWidget(self.loadingWidget)
		self.stackWidget.addWidget(self.failWidget)
		self.stackWidget.addWidget(self.loginWidget)
		self.stackWidget.addWidget(self.chatWidget)
		self.stackWidget.setCurrentIndex(0)

		self.mainLayout = QtWidgets.QVBoxLayout(self)
		self.mainLayout.addWidget(self.stackWidget)
		self.mainLayout.setSpacing(0)
		self.mainLayout.setContentsMargins(0, 0, 0, 0)
		self.setLayout(self.mainLayout)
		
		self.listenThread  = QtCore.QThread()
		self._listenThread = ListenThread(protocol=self.handleFromThread)
		self._listenThread.moveToThread(self.listenThread)
		self.listenThread.start()

		self.resize(750, 500)
		self.show()

		self.setUp()

	def setUp(self):
		self.client.connectServer(self.client.serverIp)

	@QtCore.pyqtSlot(list)
	def handleFromThread(self, ls):
		function, args = ls
		if args:
			function(*args)
		else:
			function()

	def sendFile(self, filename, recvName, size):
		self.client.sendFile(filename, recvName, size)

	def sendFileSuccess(self, filename, recvName):
		self.chatWidget.sendFileSuccess(filename, recvName)

	def sendFileRefuse(self, filename, recvName):
		self.chatWidget.sendFileRefuse(recvName, filename)

	def sendFileFail(self, filename, recvName):
		self.chatWidget.sendFileFail(filename, recvName)

	def sendMessage(self, message, sendName):
		self.client.sendMessage(message, sendName)

	def sendMessageSuccess(self, message, recvName):
		self.chatWidget.sendMessageSuccess(message, recvName)

	def chatReq(self, name):
		self.client.chatReq(name)

	def onlineNotified(self, name):
		self.chatWidget.recvOnlineName(name)
	
	def offlineNotified(self, name):
		self.chatWidget.recvOfflineName(name)

	def connectSuccess(self):
		self.stackWidget.setCurrentIndex(2)

	def receiveFile(self, sendPath, sendName, filename, size, sock):
		self.chatWidget.receiveFile(sendPath, sendName, filename, size, sock)

	def recvFileFail(self, filename, sendName):
		self.chatWidget.recvFileFail(filename, sendName)

	def acceptReceiveFile(self, sendPath, downPath, filename, sendName, sock):
		self.client.acceptReceiveFile(sendPath, downPath, filename, sendName, sock)

	def refuseReceiveFile(self, filename, sock):
		self.client.refuseReceiveFile(filename, sock)

	def receiveMessage(self, message, sendName):
		self.chatWidget.receiveMessage(message, sendName)

	def connectFail(self):
		self.stackWidget.setCurrentIndex(1)

	def signupReq(self, name, pw):
		self.client.signupReq(name, pw)

	def signupReqAccept(self):
		self.loginWidget.signupReqAccept()

	def signupReqRefuse(self, message):
		self.loginWidget.signupReqRefuse(message)

	def loginReqRefuse(self, message):
		self.loginWidget.loginReqRefuse(message)

	def loginReq(self, name, pw):
		self.client.loginReq(name, pw)
	
	def loginReqAccept(self, name):
		self.name = name
		self.stackWidget.setCurrentIndex(3)

	def chatReqRefuse(self, name):
		self.chatWidget.chatReqRefuse(name)

	def nameReqAccept(self, name):
		self.chatWidget.connectedSuccess(name)

	def onlineReqAccept(self, online):
		self.chatWidget.recvListOnline(online)

	def chatAvailable(self, name):
		return self.client.chatAvailable(name)


class ListenThread(QtCore.QObject):

	protocol = QtCore.pyqtSignal(list)

	def __init__(self, parent=None, **kwargs):
		super().__init__(parent, **kwargs)

	def listenFromThread(self, function, args=None):
		self.protocol.emit([function, args])

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	ex  = ClientGUI()
	sys.exit(app.exec_())
