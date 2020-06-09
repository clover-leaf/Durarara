import sys
import re
import socket
import select
import pickle
# import psutil

PORT       = 1006
LISTEN_MAX = 5
BUFSIZE    = 4096
EMPTY_NAME = "__EmptY__"

class Server():

	def __init__(self):
		self.port           = PORT
		self.listenMax      = LISTEN_MAX
		self.bufsize        = BUFSIZE
		self.socketServer   = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connectingDict = {self.socketServer: [EMPTY_NAME, ""]}
		self.accountDict    = self.loadAccount()
		self.log            = "" # Logging of server while running

		self.setUp()
		self.handle()

	# def getLocalIp(self):
	# 	addrs = psutil.net_if_addrs()
	# 	return addrs['Hamachi'][1].address

	def loadAccount(self):
		with open("account.pkl", "rb") as f:
			return pickle.load(f)

	def saveAccount(self):
		with open("account.pkl", "wb") as f:
			pickle.dump(self.accountDict, f)

	def setUp(self):
		try:
			self.socketServer.bind(("", self.port))
			self.log += f"Bind to port {self.port}"
			self.socketServer.listen(self.listenMax)
			self.log += f"Maximum of connection: {self.listenMax}"

		except socket.error:
			self.socketServer.close()
			sys.exit()

	def handle(self):
		print("Server start listening")
		self.log += "Server start listening"
		while True:
			read_sockets, write_sockets, error_sockets = \
				select.select(list(self.connectingDict.keys()), [], [])
				
			for socket in read_sockets:
				if socket == self.socketServer:
					conn, addr = self.socketServer.accept()
					print(f"{addr[0]} has connected")
					self.log += f"{addr[0]} has connected"
					self.connectingDict[conn] = [EMPTY_NAME, addr[0]]
					self.send(conn, "</connect_success>")
				else:
					name, addr = self.connectingDict[socket]
					try:
						data = socket.recv(self.bufsize)
						if data:
							self.handleProtocol(socket, data.decode())
						else:
							socket.close()
							self.connectingDict.pop(socket, None)
							print(f"{addrs} has disconnected")
							if name != EMPTY_NAME:
								self.broadcast(f"<offline_notified>{name}</offline_notified>")
					except:
						socket.close()
						print(f"{addr} has disconnected")
						self.log += f"{addr} has disconnected"
						self.connectingDict.pop(socket, None)
						if name != EMPTY_NAME:
							self.broadcast(f"<offline_notified>{name}</offline_notified>")
	
	def broadcast(self, message, socket=[None]):
		for sock in self.connectingDict.keys():
			if sock != self.socketServer:
				if sock not in socket:
					self.send(sock, message)

	def handleProtocol(self, socket, protocol):
		pattern_login_req  = r"<login_req>(.+)\|(.+)</login_req>"
		pattern_chat_req   = r"<chat_req>(.+)</chat_req>"
		pattern_signup_req = r"<signup_req>(.+)\|(.+)</signup_req>"
		pattern_online_req = r"</online_req>"

		match_login_req = re.match(pattern_login_req, protocol)
		if match_login_req:
			return self.handleLoginReq(socket, match_login_req)

		match_signup_req = re.match(pattern_signup_req, protocol)
		if match_signup_req:
			return self.handleSignupReq(socket, match_signup_req)
		
		match_chat_req = re.match(pattern_chat_req, protocol)
		if match_chat_req:
			return self.handleChatReq(socket, match_chat_req)

		match_online_req = re.match(pattern_online_req, protocol)
		if match_online_req:
			return self.handleOnlineReq(socket)

	def handleChatReq(self, socket, match_pattern):
		user_name = match_pattern.group(1)
		if user_name not in [acc[0] for acc in self.connectingDict.values() if acc[0] != EMPTY_NAME]:
			self.send(socket, f"<chat_req_refuse>{user_name}</chat_req_refuse>")
		else:
			addr = [user[1] for user in self.connectingDict.values() if user[0] == user_name][0]
			self.send(socket, f"<chat_req_accept>{user_name}|{addr}</chat_req_accept>")

	def handleLoginReq(self, sock, match_pattern):
		user_name = match_pattern.group(1)
		password  = match_pattern.group(2)
		if user_name not in self.accountDict.keys():
			self.send(sock, "<login_req_refuse>Tài khoản không tồn tại</login_req_refuse>")
		elif password != self.accountDict[user_name]:
			self.send(sock, "<login_req_refuse>Mật khẩu không chính xác</login_req_refuse>")
		elif user_name in [acc[0] for acc in self.connectingDict.values() if acc[0] != EMPTY_NAME]:
			self.send(sock, "<login_req_refuse>Tài khoản đang được đăng nhập từ nơi khác</login_req_refuse>")
		else:
			self.connectingDict[sock][0] = user_name
			self.broadcast(f"<online_notified>{user_name}</online_notified>", socket=[sock])
			self.send(sock, f"<login_req_accept>{user_name}</login_req_accept>")

	def handleSignupReq(self, socket, match_pattern):
		user_name = match_pattern.group(1)
		password  = match_pattern.group(2)
		if user_name in self.accountDict.keys():
			self.send(socket, "<signup_req_refuse>Tên tài khoản đã tồn tại</signup_req_refuse>")
		else:
			self.accountDict[user_name] = password
			self.saveAccount()
			self.send(socket, "</signup_req_accept>")

	def handleOnlineReq(self, socket):
		online_list = [acc[0] for acc in self.connectingDict.values() if acc[0] != EMPTY_NAME]
		online_format = ",".join(online_list)
		self.send(socket, f"<online_req_accept>{online_format}</online_req_accept>")

	def send(self, socket, message):
		socket.sendall(str(message).encode())
		self.log += f"To {self.connectingDict[socket]}: {message}"

		# match_connect_req = re.match(pattern_connect_req, protocol)
		# if match_connect_req:
		# 	a = match_connect_req
		# 	return self.connect(f"{a.group(1)}.{a.group(2)}.{a.group(3)}.{a.group(4)}", int(a.group(5)))

s = Server()

