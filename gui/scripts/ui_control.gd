extends Panel

@onready var item_list: ItemList = $MainUI/PanelContainer/Left/VBoxContainer/ScrollContainer/ItemList
@onready var splash_screen: CenterContainer = $SplashScreen
@onready var main_ui: HSplitContainer = $MainUI

@onready var process_list: PopupPanel = $"ProcessList"
@onready var write_dialog: PopupPanel = $WriteDialog
@onready var found_address_context_menu: PopupMenu = $FoundAddressContextMenu
@onready var scan_value: LineEdit = $MainUI/PanelContainer2/Right/VBoxContainer/HBoxContainer/ScanValue
@onready var next_scan_button: Button = $MainUI/PanelContainer2/Right/VBoxContainer/NextScanButton
@onready var address_list_label: Label = $MainUI/PanelContainer/Left/VBoxContainer/AddressListLabel
@onready var detach_button: Button = $MainUI/PanelContainer2/Right/VBoxContainer/DetachButton
@onready var address_write_value: LineEdit = $WriteDialog/MarginContainer/VBoxContainer/AddressWriteValue

var current_scan_addresses_number: int = 0
var right_clicked_found_address_index: int = -1

func _ready() -> void:
	# Ensure only the initial view is visible at the start
	splash_screen.visible = true
	main_ui.visible = false
	process_list.visible = false
	print("UI Ready. Initial view shown.")
	process_list.connect("process_selected", self._on_process_selected)
	WebsocketManager.processes_received.connect(self._on_websocket_process_received)
	WebsocketManager.attach_confirmed.connect(self._on_websocket_attach_confirmed)
	WebsocketManager.scan_metadata_received.connect(self._on_websocket_scan_metadata_received)
	WebsocketManager.scan_results_received.connect(self._on_websocket_scan_results_received)

func _on_attach_button_pressed() -> void:
	print("Attach button pressed. Requesting process list...")
	WebsocketManager.send_message({
		"command": "get_processes"
	})

func _on_websocket_process_received(processes: Array) -> void:
	print("Received process list from websocket")
	process_list.populate_process_list(processes)
	print("Process list populated. Popupping...")
	# Get the parent size and position the popup on the right
	process_list.popup()

func _on_process_selected(process_info: Dictionary) -> void:
	print("Process selected: ", process_info)
	var pid = int(process_info["pid"])
	WebsocketManager.send_message({
		"command": "attach",
		"target": pid
	})
	process_list.visible = false
	main_ui.visible = true

func _on_websocket_attach_confirmed(data: Dictionary) -> void:
	print("Attach confirmed: ", data)
	splash_screen.visible = false
	main_ui.visible = true
	process_list.hide()


func _on_first_scan_button_pressed() -> void:
	var scan_value_text = scan_value.text
	if !scan_value_text.is_valid_int():
		print("Invalid scan value: ", scan_value_text)
		return
	var scan_value_int = int(scan_value_text)
	WebsocketManager.send_message({
		"command": "scan_memory",
		"value": scan_value_int,
		"scan_type": "first",
		"width": 4,
		"signed": false
	})


func _on_next_scan_button_pressed() -> void:
	var scan_value_text = scan_value.text
	if !scan_value_text.is_valid_int():
		print("Invalid scan value: ", scan_value_text)
		return
	var scan_value_int = int(scan_value_text)
	WebsocketManager.send_message({
		"command": "scan_memory",
		"value": scan_value_int,
		"scan_type": "next",
		"width": 4,
		"signed": false
	})

func _on_websocket_scan_metadata_received(metadata: Dictionary) -> void:
	print("Scan metadata received: ", metadata)
	current_scan_addresses_number = metadata["result"]
	address_list_label.text = "Address List (%s found)" % current_scan_addresses_number
	next_scan_button.disabled = false
	
func _on_websocket_scan_results_received(results: Dictionary) -> void:
	if results["status"] == "success":
		var scan_data = results["result"]
		item_list.clear()
		
		for item in scan_data["results"]:
			var text = "Address: %s \t Value: %s" % [item["address"], item["value"]]
			var index = item_list.add_item(text)
			item_list.set_item_metadata(index, item["address"])


func _on_detach_button_pressed() -> void:
	WebsocketManager.send_message({
		"command": "detach"
	})
	main_ui.visible = false
	current_scan_addresses_number = 0
	splash_screen.visible = true


func _on_poll_scan_results_timer_timeout() -> void:
	if current_scan_addresses_number > 0:
		WebsocketManager.send_message({
			"command": "get_scan_results",
			"page": 1,
			"page_size": 100
		})


func _on_item_list_item_clicked(index: int, _at_position: Vector2, mouse_button_index: int) -> void:
	if mouse_button_index == MOUSE_BUTTON_RIGHT:
		right_clicked_found_address_index = index
		found_address_context_menu.position = get_global_mouse_position()
		found_address_context_menu.popup()


func _on_ok_button_pressed() -> void:
	var value = address_write_value.text
	if !value.is_valid_int():
		print("Invalid value: ", value)
		return
	var address = item_list.get_item_metadata(right_clicked_found_address_index)
	if address == null:
		print("No address found for selected item")
		return
	write_dialog.hide()
	WebsocketManager.send_message({
		"command": "write_memory",
		"address": address,
		"value": int(value),
		"width": 4,
		"signed": false
	})



func _on_found_address_context_menu_id_pressed(id: int) -> void:
	match id:
		0:
			write_dialog.popup_centered()
