extends Control
@onready var process_list: ItemList = $UI/PickProcess/PanelContainer/MarginContainer/VBoxContainer/ProcessList
@onready var pick_process: PanelContainer = $UI/PickProcess
@onready var hub: VBoxContainer = $UI/Hub
@onready var address_list: ItemList = $UI/Hub/ScanArea/PanelContainer/ScanResults/VBoxContainer/ScrollContainer/AddressList
@onready var first_scan_button: Button = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/FirstScanButton
@onready var scan_value: LineEdit = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/HBoxContainer/GridContainer/ScanValue
@onready var scan_type: OptionButton = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/HBoxContainer/GridContainer/ScanType
@onready var data_type: OptionButton = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/HBoxContainer/GridContainer/DataType
@onready var second_scan_button: Button = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/SecondScanButton
@onready var undo_scan_button: Button = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/UndoScanButton
@onready var search_process: LineEdit = $UI/PickProcess/PanelContainer/MarginContainer/VBoxContainer/SearchProcess
@onready var write_address_dialog: AcceptDialog = $UI/Hub/WriteAddressDialog

var connected = false
var attached = false
var is_scan = false
var process_list_items: Array = []
var write_target_address: String = ""

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	RPCManager.connected.connect(_on_connected)
	RPCManager.disconnected.connect(_on_disconnected)
	RPCManager.message_received.connect(_on_message)
	process_list.item_activated.connect(_on_process_activated)
	first_scan_button.pressed.connect(_on_first_scan_button_pressed)
	second_scan_button.pressed.connect(_on_second_scan_button_pressed)
	undo_scan_button.pressed.connect(_on_undo_scan_button_pressed)
	search_process.text_changed.connect(_filter_process_list)

	hub.hide()
	pick_process.show()
	RPCManager.connect_to_server("ws://localhost:8765")


func _process(_delta: float) -> void:
	if not connected:
		RPCManager.connect_to_server("ws://localhost:8765")
	else:
		RPCManager.send_message({"command": "status"})

func _switch_scan_controls(status: bool) -> void:
	second_scan_button.disabled = !status
	undo_scan_button.disabled = !status

func populate_process_list(data: Array) -> void:
	process_list.clear()
	for proc in data:
		process_list.add_item("%s %s" % [int(proc.pid), proc.name])

func _filter_process_list(new_text: String) -> void:
	print("Filtering!")
	var filtered_processes = []
	for proc in process_list_items:
		if proc.name.containsn(new_text):
			filtered_processes.append(proc)
	populate_process_list(filtered_processes)

func populate_scan_results(data: Array) -> void:
	address_list.clear()
	for scan_result in data:
		address_list.add_item("%s (%d)" % [scan_result.address, scan_result.value])


func _on_process_activated(index: int):
	var process_text = process_list.get_item_text(index)
	var pid = int(process_text.split(" ")[0])
	print("Attaching to %s" % pid)
	RPCManager.send_message({"command": "attach", "params": {"pid": pid}})

func _on_connected() -> void:
	print("CONNECTED!")
	connected = true
	RPCManager.send_message({"command": "list-processes"})

func _on_disconnected() -> void:
	print("Disconnected from the WS.")
	connected = false

func _on_message(data: Dictionary) -> void:
	if not data.has("event"):
		return
	var event = data["event"]
	var payload = data["data"]

	match event:
		"list-processes":
			process_list_items = payload
			populate_process_list(payload)
		"attach":
			print("Successfully attached to %d!" % payload)
			pick_process.hide()
			hub.show()
		"current-scan-results":
			populate_scan_results(payload)
			if not is_scan:
				is_scan = true
				_switch_scan_controls(true)
		"status":
			if payload == "attached":
				attached = true
				hub.show()
				pick_process.hide()
			else:
				attached = false
				hub.hide()
				pick_process.show()

func _on_first_scan_button_pressed() -> void:
	RPCManager.send_message({
		"command": "first-scan",
		"params": {
			"value": int(scan_value.text),
			"data_type": data_type.get_selected_id(),
			"scan_type": scan_type.get_selected_id()
		}
	})

func _on_second_scan_button_pressed() -> void:
	RPCManager.send_message({
		"command": "next-scan",
		"params": {
			"value": int(scan_value.text),
			"data_type": data_type.get_selected_id(),
			"scan_type": scan_type.get_selected_id()
		}
	})

func _on_undo_scan_button_pressed() -> void:
	RPCManager.send_message({"command": "undo-scan"})
	is_scan = false
	_switch_scan_controls(false)


func _on_address_list_item_activated(index: int) -> void:
	var item := address_list.get_item_text(index)
	var address_str := item.split(" ")[0]  # Get "0x128898000" part (as string)
	print("Selected write address: %s from item %s" % [address_str, item])
	write_target_address = address_str  # Keep as string
	write_address_dialog.popup_centered()


func _on_write_address_dialog_confirmed() -> void:
	var write_input = int(write_address_dialog.find_child("WriteValue", true, false).text)
	print("Writing value: %d to address: 0x%x" % [write_input, write_target_address])  # Debug output
	RPCManager.send_message({
		"command": "write-value",
		"params": {
			"address": write_target_address,
			"value": write_input,
			"data_type": data_type.get_selected_id()
		}
	})
