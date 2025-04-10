# WebSocketManager.md

extends Node

signal connection_status_changed(is_connected: bool)

signal processes_received(processes: Array)
signal attach_confirmed(data: Dictionary)
signal attach_failed(error_data: Dictionary)
signal memory_write(data: Dictionary)

signal scan_metadata_received(metadata: Dictionary)
signal scan_results_received(results: Dictionary)

const SERVER_URL = "ws://localhost:8888"

var socket := WebSocketPeer.new()
var _is_connected := false

func _ready() -> void:
	var err = socket.connect_to_url(SERVER_URL)
	if err != OK:
		print("Failed to connect to server: ", err)
		return

	_is_connected = true
	emit_signal("connection_status_changed", _is_connected)

func set_connection_status(status: bool) -> void:
	if _is_connected != status:
		_is_connected = status
		print("Connection status changed to: ", _is_connected)
		emit_signal("connection_status_changed", _is_connected)

func _process(_delta: float) -> void:
	socket.poll()
	var state = socket.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		set_connection_status(true)
		while socket.get_available_packet_count():
			var packet = socket.get_packet()
			var message = packet.get_string_from_utf8()
			var data = JSON.parse_string(message)
			if data != null:
				_process_message(data)
	elif state == WebSocketPeer.STATE_CLOSING:
		pass
	elif state == WebSocketPeer.STATE_CLOSED:
		var code = socket.get_close_code()
		var reason = socket.get_close_reason()
		print("WebSocket closed with code: ", code, " and reason: ", reason)
		set_connection_status(false)

func _process_message(data: Dictionary) -> void:
	if "status" not in data:
		print("Received message without status field: ", data)
		return
		
	if data["status"] == "error":
		print("Error from server: ", data.get("error", "Unknown error"))
		return
		
	# Handle different message types based on the command or response type
	if "command" in data:
		# Handle command responses
		match data["command"]:
			"attach":
				if data["status"] == "success":
					emit_signal("attach_confirmed", data)
				else:
					emit_signal("attach_failed", data)
			"scan_memory":
				if data["status"] == "success":
					emit_signal("scan_metadata_received", data)
			"get_scan_results":
				if data["status"] == "success":
					emit_signal("scan_results_received", data)
			"get_memory_maps":
				if data["status"] == "success":
					emit_signal("memory_maps_received", data)
			"read_memory":
				if data["status"] == "success":
					emit_signal("memory_read", data)
			"write_memory":
				if data["status"] == "success":
					emit_signal("memory_write", data)
			"get_processes":
				if data["status"] == "success":
					emit_signal("processes_received", data.get("result", []))
	else:
		print("Received message without command field: ", data)

func send_message(message: Dictionary) -> void:
	if not _is_connected:
		print("Cannot send message: Not connected to server")
		return
		
	var json_string = JSON.stringify(message)
	var error = socket.send(json_string.to_utf8_buffer())
	
	if error != OK:
		print("Failed to send message: ", error)
