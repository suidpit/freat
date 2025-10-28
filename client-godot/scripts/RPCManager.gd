extends Node

signal connected
signal disconnected
signal message_received(data: Dictionary)
signal error_received(message: String)

var _client := WebSocketPeer.new()
var _is_connected := false

func connect_to_server(url: String):
	_client.connect_to_url(url)

func _process(_delta: float):
	_client.poll()
	var state = _client.get_ready_state()
	match state:
		WebSocketPeer.STATE_CONNECTING:
			pass
		WebSocketPeer.STATE_OPEN:
			if not _is_connected:
				_is_connected = true
				_on_connected()
			while _client.get_available_packet_count() > 0:
				_on_message()
		WebSocketPeer.STATE_CLOSED:
			if _is_connected:
				_is_connected = false
				_on_disconnected()

func _on_connected():
	_is_connected = true
	connected.emit()

func _on_disconnected():
	disconnected.emit()

func _on_message():
	var packet = _client.get_packet()
	var message_str = packet.get_string_from_utf8()
	var json = JSON.new()
	var error = json.parse(message_str)
	if error != OK:
		print("Error parsing JSON: ", message_str)
		error_received.emit("Error received", "Bad JSON from the server")
		return
	var data: Dictionary = json.get_data()
	message_received.emit(data)

func send_message(data: Dictionary):
	if not _is_connected:
		print("Not connected, can't send a message.")
		return
	var message_str = JSON.stringify(data)
	_client.put_packet(message_str.to_utf8_buffer())
