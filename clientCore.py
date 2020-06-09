
import sys
import re
import select
import socket
import psutil
import threading

SERVER_PORT = 1006
CLIENT_PORT = 1903
LISTEN_MAX  = 5
BUFSIZE     = 4096
# SERVER_IP  = "25.53.181.229"
# SERVER_IP  = "25.10.32.20"
# SERVER_IP  = "25.44.168.204"
# SERVER_IP  = "25.6.9.155"
SERVER_IP  = "172.27.44.23"
EMPTY_NAME = "__EmptY__"
SERVER_NAME= "__sErvEr__"

class ClientCore():

	def __init__(self, parent):
		self.listenMax      = LISTEN_MAX
		self.bufsize        = BUFSIZE
		self.connectingDict = {}
		self.threadDict     = {}
		self.logging        = False
		self.serverIp       = SERVER_IP
		self.parent         = parent
		self.usedPort       = [CLIENT_PORT]
		self.ip             = self.getLocalAddress()
		
	def getLocalAddress(self):
		net = psutil.net_if_addrs()
		return net["ZeroTier One [3efa5cb78a0b0796]"][1].address

	def connectServer(self, ip):
		self.connect(ip, SERVER_NAME)
		self.setUp()

	def connect(self, addr, name):
		thread = threading.Thread(target=self.listening, args=(addr,name), daemon=True)
		thread.start()

	def listening(self, addr, name):
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			if name == SERVER_NAME:
				sock.connect((addr, SERVER_PORT))
				self.connectingDict[f"{addr}:{SERVER_PORT}"] = [name, sock]
			else:
				sock.connect((addr, CLIENT_PORT))
				self.connectingDict[f"{addr}:{CLIENT_PORT}"] = [name, sock]
			while True:
				try:
					data = sock.recv(4096)
					if data:
						self.handleProtocol(sock, data.decode())
				except ConnectionResetError:
					addr = sock.getpeername()
					self.connectingDict.pop(f"{addr[0]}:{addr[1]}", None)
					print("deleted")
					break

		except Exception as f:
			print(f)
			self.parent._listenThread.listenFromThread(self.parent.connectFail)

	def setUp(self):
		try:
			thread = threading.Thread(target=self.handleConnection, daemon=True)
			thread.start()
		except:
			self.socketServer.close()
			sys.exit()
				
	def handleConnection(self):
		self.socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connectingDict[""] = ["", self.socketServer]
		self.socketServer.bind(("", CLIENT_PORT))
		self.socketServer.listen(self.listenMax)
		
		while True:
			read_sockets, write_sockets, error_sockets = \
				select.select([i[1] for i in self.connectingDict.values()], [], [])

			for sock in read_sockets:
				if sock == self.socketServer:
					conn, addr = self.socketServer.accept()
					self.connectingDict[f"{addr[0]}:{CLIENT_PORT}"] = [EMPTY_NAME, conn]
					self.send(conn, "</name_req>")
				else:
					addr = f"{sock.getpeername()[0]}:{CLIENT_PORT}"
					try:
						data = sock.recv(self.bufsize)
						if data:
							self.handleProtocol(sock, data.decode())
						else:
							sock.close()
							self.connectingDict.pop(addr, None)
					except:
						sock.close()
						self.connectingDict.pop(addr, None)


	def handleProtocol(self, sock, protocol):
		pattern_connect_success   = r"</connect_success>"
		pattern_name_req          = r"</name_req>"
		pattern_name_req_accept   = r"</name_req_accept>"
		pattern_signup_req_accept = r"</signup_req_accept>"
		pattern_login_req_refuse  = r"<login_req_refuse>(.+)</login_req_refuse>"
		pattern_login_req_accept  = r"<login_req_accept>(.+)</login_req_accept>"
		pattern_signup_req_refuse = r"<signup_req_refuse>(.+)</signup_req_refuse>"
		pattern_chat_req_refuse   = r"<chat_req_refuse>(.+)</chat_req_refuse>"
		pattern_online_req_accept = r"<online_req_accept>(.+)</online_req_accept>"
		pattern_online_notified   = r"<online_notified>(.+)</online_notified>" #name 
		pattern_offline_notified  = r"<offline_notified>(.+)</offline_notified>" #name 
		pattern_name              = r"<name>(.+)</name>"
		pattern_chat_req_accept   = r"<chat_req_accept>(.+)\|(.+)</chat_req_accept>" #name|addr
		pattern_message_req       = r"<message_req>(.+)\|(.+)</message_req>" #message|sendName
		pattern_message_req_accept = r"<message_req_accept>(.+)\|(.+)</message_req_accept>" #message|recvName
		pattern_file_req_refuse   = r"<file_req_refuse>(.+)\|(.+)</file_req_refuse>" #filename| recvName
		pattern_file_req          = r"<file_req>(.+)\|(.+)\|(.+)\|(.+)</file_req>" #sendPath|sendName|filename|size
		pattern_file_req_accept   = r"<file_req_accept>(.+)\|(.+)\|(.+)\|(.+)\|(.+)</file_req_accept>" #sendPath|filename|recvName|port|addr

		match_connect_success = re.match(pattern_connect_success, protocol)
		if match_connect_success:
			return self.handleConnectSuccess(match_connect_success)

		match_name_req = re.match(pattern_name_req, protocol)
		if match_name_req:
			return self.handleNameReq(sock)

		match_name_req_accept = re.match(pattern_name_req_accept, protocol)
		if match_name_req_accept:
			return self.handleNameReqAccept(sock, match_name_req_accept)

		match_signup_req_accept = re.match(pattern_signup_req_accept, protocol)
		if match_signup_req_accept:
			return self.handleSignupReqAccept(sock)

		match_online_notified = re.match(pattern_online_notified, protocol)
		if match_online_notified:
			return self.handleOnlineNotified(sock, match_online_notified)
		
		match_offline_notified = re.match(pattern_offline_notified, protocol)
		if match_offline_notified:
			return self.handleOfflineNotified(sock, match_offline_notified)
		
		match_file_req = re.match(pattern_file_req, protocol)
		if match_file_req:
			return self.handleFileReq(sock, match_file_req)
		
		match_file_req_accept = re.match(pattern_file_req_accept, protocol)
		if match_file_req_accept:
			return self.handleFileReqAccept(sock, match_file_req_accept)

		match_file_req_refuse = re.match(pattern_file_req_refuse, protocol)
		if match_file_req_refuse:
			return self.handleFileReqRefuse(sock, match_file_req_refuse)
		
		match_message_req = re.match(pattern_message_req, protocol)
		if match_message_req:
			return self.handleMessageReq(sock, match_message_req)
		
		match_message_req_accept = re.match(pattern_message_req_accept, protocol)
		if match_message_req_accept:
			return self.handleMessageReqAccept(sock, match_message_req_accept)

		match_login_req_refuse = re.match(pattern_login_req_refuse, protocol)
		if match_login_req_refuse:
			return self.handleLoginReqRefuse(match_login_req_refuse)

		match_signup_req_refuse = re.match(pattern_signup_req_refuse, protocol)
		if match_signup_req_refuse:
			return self.handleSignupReqRefuse(sock, match_signup_req_refuse)

		match_login_req_accept = re.match(pattern_login_req_accept, protocol)
		if match_login_req_accept:
			return self.handleLoginReqAccept(match_login_req_accept)

		match_chat_req_accept = re.match(pattern_chat_req_accept, protocol)
		if match_chat_req_accept:
			return self.handleChatReqAccept(match_chat_req_accept)

		match_chat_req_refuse = re.match(pattern_chat_req_refuse, protocol)
		if match_chat_req_refuse:
			return self.handleChatRegRefuse(match_chat_req_refuse)
		
		match_name = re.match(pattern_name, protocol)
		if match_name:
			return self.handleName(sock, match_name)

		match_online_req_accept = re.match(pattern_online_req_accept, protocol)
		if match_online_req_accept:
			return self.handleOnlineReqAccept(match_online_req_accept)
	
	def handleOnlineNotified(self, sock, protocol):
		name = protocol.group(1)
		self.parent._listenThread.listenFromThread(self.parent.onlineNotified, args=(name,))

	def handleOfflineNotified(self, sock, protocol):
		name = protocol.group(1)
		self.parent._listenThread.listenFromThread(self.parent.offlineNotified, args=(name,))

	def handleFileReqAccept(self, sock, protocol):
		sendPath = protocol.group(1)
		filename = protocol.group(2)
		recvName = protocol.group(3)
		port = int(protocol.group(4))
		addr = protocol.group(5)
		thread = threading.Thread(target=self.createSendFileHost, args=(sendPath, filename, recvName, port, addr), daemon=True)
		thread.start()

	def handleSignupReqAccept(self, sock):
		self.parent._listenThread.listenFromThread(self.parent.signupReqAccept)

	def handleSignupReqRefuse(self, sock, protocol):
		message = protocol.group(1)
		self.parent._listenThread.listenFromThread(self.parent.signupReqRefuse, args=(message,))

	def handleFileReqRefuse(self, sock, protocol):
		filename = protocol.group(1)
		recvName = protocol.group(2)
		self.parent._listenThread.listenFromThread(self.parent.sendFileRefuse, args=(recvName, filename))

	def handleFileReq(self, sock, protocol):
		sendPath = protocol.group(1)
		sendName = protocol.group(2)
		filename = protocol.group(3)
		size     = protocol.group(4)
		self.parent._listenThread.listenFromThread(self.parent.receiveFile , args=(sendPath, sendName, filename, size, sock))

	def handleMessageReq(self, sock, protocol):
		message = protocol.group(1)
		sendName = protocol.group(2)
		protocol = f"<message_req_accept>{message}|{self.name}</message_req_accept>"
		self.send(sock, protocol)
		self.parent._listenThread.listenFromThread(self.parent.receiveMessage, args=(message, sendName))

	def handleMessageReqAccept(self, sock, protocol):
		message = protocol.group(1)
		recvName = protocol.group(2)
		self.parent._listenThread.listenFromThread(self.parent.sendMessageSuccess, args=(message, recvName))

	def handleConnectSuccess(self, protocol):
		self.parent._listenThread.listenFromThread(self.parent.connectSuccess)

	def handleName(self, sock, protocol):
		idx = [i[1] for i in self.connectingDict.values()].index(sock)
		addr = list(self.connectingDict.keys())[idx]
		self.connectingDict[addr][0] = protocol.group(1)
		self.send(sock, "</name_req_accept>")

	def handleNameReq(self, sock):
		self.send(sock, f"<name>{self.name}</name>")

	def handleNameReqAccept(self, sock, protocol):
		name = [i[0] for i in self.connectingDict.values() if i[1] == sock][0]
		self.parent._listenThread.listenFromThread(self.parent.nameReqAccept, args=(name,))

	def handleOnlineReqAccept(self, protocol):
		online = protocol.group(1).split(",")
		online.remove(self.name)
		self.parent._listenThread.listenFromThread(self.parent.onlineReqAccept, args=(online,))

	def handleChatReqAccept(self, protocol):
		name = protocol.group(1)
		addr = protocol.group(2)
		if name in [i[0] for i in self.connectingDict.values()]:
			self.parent._listenThread.listenFromThread(self.parent.nameReqAccept, args=(name,))
		else:
			self.connect(addr, name)

	def handleChatRegRefuse(self, protocol):
		name = protocol.group(1)
		self.parent._listenThread.listenFromThread(self.parent.chatReqRefuse, args=(name,))
	
	def handleLoginReqAccept(self, protocol):
		self.name = protocol.group(1)
		self.parent._listenThread.listenFromThread(self.parent.loginReqAccept, args=(self.name,))

	def handleLoginReqRefuse(self, protocol):
		message = protocol.group(1)
		self.parent._listenThread.listenFromThread(self.parent.loginReqRefuse, args=(message,))

	def createSendFileHost(self, sendPath, filename, recvName, port, addr):
		message = f"Begin sending {filename} to {recvName}"
		self.parent._listenThread.listenFromThread(self.parent.receiveMessage, args=(message, recvName))		
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((addr, port))
		socket_list = [sock]
		connected = False
		while not connected:
			read_sockets, write_sockets, error_sockets = \
				select.select(socket_list, [], [])

			for sock in read_sockets:
				data = sock.recv(self.bufsize)
				if data.decode() == "connected":
					connected = True
		try:				
			with open(sendPath, "rb") as f:
				data = f.read(BUFSIZE)
				sock.send(data)
				while data != bytes(''.encode()):
					data = f.read(BUFSIZE)
					sock.send(data)
			sock.close()
			self.parent._listenThread.listenFromThread(self.parent.sendFileSuccess, args=(filename, recvName))
		except:
			sock.close()
			self.parent._listenThread.listenFromThread(self.parent.sendFileFail, args=(filename, recvName))

	def createReceiveFileHost(self, path, filename, sendName, port):
		message = f"Begin receving {filename} from {sendName}"
		self.parent._listenThread.listenFromThread(self.parent.receiveMessage, args=(message, sendName))
		
		sock_host = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock_host.bind(("", port))
		sock_host.listen(1)
		socket_list = []
		socket_list.append(sock_host)
		finish = False

		pathFile = f"{path}/{filename}"
		try:
			with open(pathFile, "wb") as f:
				while not finish:
					read_sockets, write_sockets, error_sockets = \
						select.select(socket_list, [], [])

					for sock in read_sockets:
						if sock == sock_host:
							conn, addr = sock_host.accept()
							socket_list.append(conn)
							conn.sendall("connected".encode())
						else:
							data = sock.recv(self.bufsize)
							if data:
								f.write(data)
							else:
								sock.close()
								finish = True
		
			message = f"Finish receiving {filename} form {sendName}"
			self.parent._listenThread.listenFromThread(self.parent.receiveMessage, args=(message, sendName))
			self.usedPort.remove(port)
		except:
			sock.close()
			self.parent._listenThread.listenFromThread(self.parent.recvFileFail, args=(filename, sendName))

	def sendFile(self, path, recvName, size):
		sock = [i[1] for i in self.connectingDict.values() if i[0] == recvName][0]
		filename = path.split("/")[-1]
		protocol = f"<file_req>{path}|{self.name}|{filename}|{size}</file_req>"
		self.send(sock, protocol)
	
	def chatReq(self, name):
		server_sock = [i[1] for i in self.connectingDict.values() if i[0] == SERVER_NAME][0]
		self.send(server_sock, f"<chat_req>{name}</chat_req>")
		
	def signupReq(self, name, pw):
		server_sock = [i[1] for i in self.connectingDict.values() if i[0] == SERVER_NAME][0]
		self.send(server_sock, f"<signup_req>{name}|{pw}</signup_req>")

	def loginReq(self, name, pw):
		server_sock = [i[1] for i in self.connectingDict.values() if i[0] == SERVER_NAME][0]
		self.send(server_sock, f"<login_req>{name}|{pw}</login_req>")
	
	def acceptReceiveFile(self, sendPath, downPath, filename, sendName, sock):
		port = self.usedPort[-1]
		while port in self.usedPort:
			port += 1
		self.usedPort.append(port)
		thread = threading.Thread(target=self.createReceiveFileHost, args=(downPath, filename, sendName, port), daemon=True)
		thread.start()
		self.send(sock, f"<file_req_accept>{sendPath}|{filename}|{self.name}|{port}|{self.ip}</file_req_accept>")

	def refuseReceiveFile(self, filename, sock):
		self.send(sock, f"<file_req_refuse>{filename}|{self.name}</file_req_refuse>")

	def sendMessage(self, message, name):
		sock = [i[1] for i in self.connectingDict.values() if i[0] == name][0]
		self.send(sock, f"<message_req>{message}|{self.name}</message_req>")
	
	def send(self, sock, message):
		sock.sendall(message.encode())

	def sendByName(self, message, name=SERVER_NAME):
		try:
			sock = [i[1] for i in self.connectingDict.values() if i[0] == name][0]
			self.send(sock, message)
		except:
			if name == SERVER_NAME:
				self.parent._listenThread.listenFromThread("<error>Can't connect to server</error>")
			else:
				self.parent._listenThread.listenFromThread("<error>This connection has lost</error>")

	def chatAvailable(self, name):
		if name in [i[0] for i in self.connectingDict.values()]:
			return True
		return False

	# def shutdown(self):
	# 	for ip_port in self.connectingDict.keys():
	# 		self.threadDict[ip_port].join()
	# 		self.connectingDict[ip_port].close()

# server_ip   = "25.53.181.229"
# lenovo_ip   = "25.44.168.204"
# nitro_ip    = "25.6.9.155"
# target_ip   = "25.10.32.20"

