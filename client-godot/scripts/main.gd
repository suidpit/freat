extends Control
@onready var process_list: ItemList = $UI/PickProcess/PanelContainer/MarginContainer/VBoxContainer/ProcessList
@onready var pick_process: PopupPanel = $UI/PickProcess
@onready var hub: VBoxContainer = $UI/Hub

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	RPCManager.connected.connect(_on_connected)
	RPCManager.disconnected.connect(_on_disconnected)
	RPCManager.message_received.connect(_on_message)
	process_list.item_activated.connect(_on_process_activated)
	
	RPCManager.connect_to_server("ws://localhost:8765")
	
func _process(_delta: float) -> void:
	if not RPCManager.connected:
		RPCManager.connect_to_server("ws://localhost:8765")
		
func populate_list(data: Array) -> void:
	for proc in data:
		process_list.add_item("%s %s" % [int(proc.pid), proc.name])

func _on_process_activated(index: int):
	var process_text = process_list.get_item_text(index)	
	var pid = int(process_text.split(" ")[0])
	print("Attaching to %s" % pid)
	RPCManager.send_message({"command": "attach", "params": {"pid": pid}})
	

func _on_connected() -> void:
	print("CONNECTED!")
	RPCManager.send_message({"command": "list-processes"})

func _on_disconnected() -> void:
	print("Disconnected from the WS. Let's retry...")
	
	
func _on_message(data: Dictionary) -> void:
	if not data.has("event"):
		return
	var event = data["event"]
	var payload = data["data"]
	
	match event:
		"list-processes":
			populate_list(payload)
		"attach":
			print("Successfully attached to %s!" % payload)
			pick_process.hide()
			hub.show()
			
