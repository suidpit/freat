extends Control
@onready var process_list: ItemList = $UI/PickProcess/PanelContainer/MarginContainer/VBoxContainer/ProcessList
@onready var pick_process: PanelContainer = $UI/PickProcess
@onready var hub: VBoxContainer = $UI/Hub
@onready var scan_results_tree: Tree = $UI/Hub/ScanArea/PanelContainer/ScanResults/VBoxContainer/ScanResultsTree
@onready var first_scan_button: Button = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/FirstScanButton
@onready var scan_value: LineEdit = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/HBoxContainer/GridContainer/ScanValue
@onready var scan_type: OptionButton = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/HBoxContainer/GridContainer/ScanType
@onready var data_type: OptionButton = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/HBoxContainer/GridContainer/DataType
@onready var second_scan_button: Button = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/SecondScanButton
@onready var undo_scan_button: Button = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/UndoScanButton
@onready var search_process: LineEdit = $UI/PickProcess/PanelContainer/MarginContainer/VBoxContainer/SearchProcess
@onready var write_address_dialog: AcceptDialog = $UI/Hub/WriteAddressDialog
@onready var scan_progress_bar: ProgressBar = $UI/Hub/ScanArea/PanelContainer2/ScanControls/VBoxContainer/ScanProgressBar
@onready var cheat_table: Tree = $UI/Hub/BottomArea/Table/MarginContainer/VBoxContainer/CheatTable
@onready var cheat_table_context_menu: PopupMenu = $UI/Hub/CheatTableContextMenu
@onready var scan_results_label: Label = $UI/Hub/ScanArea/PanelContainer/ScanResults/VBoxContainer/AddressListLabel
@onready var watchpoint_log: Tree = $UI/Hub/BottomArea/WatchpointPanel/MarginContainer/VBoxContainer/WatchpointLog
@onready var watchpoint_detail_dialog: AcceptDialog = $UI/Hub/WatchpointDetailDialog
@onready var watchpoint_detail_text: RichTextLabel = $UI/Hub/WatchpointDetailDialog/DetailText
@onready var pick_game: PanelContainer = $UI/PickGame
@onready var game_list: ItemList = $UI/PickGame/PanelContainer/MarginContainer/VBoxContainer/GameList
@onready var cheat_table_file_dialog: FileDialog = $UI/Hub/CheatTableFileDialog
@onready var freeze_value_dialog: AcceptDialog = $UI/Hub/FreezeValueDialog

var connected = false
var provider: String = ""
var game_selected: bool = false
var stay_on_hub: bool = false
var game_list_items: Array = []
var file_dialog_saving: bool = false
var attached = false
var is_scan = false
var process_list_items: Array = []
var write_target_address: String = ""
var process_list_timer: Timer
var selected_cheat_table_item: TreeItem = null
var selected_scan_result: Dictionary = {}
var freeze_pending_item: TreeItem = null

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	RPCManager.connected.connect(_on_connected)
	RPCManager.disconnected.connect(_on_disconnected)
	RPCManager.message_received.connect(_on_message)
	process_list.item_activated.connect(_on_process_activated)
	first_scan_button.pressed.connect(_on_first_scan_button_pressed)
	second_scan_button.pressed.connect(_on_second_scan_button_pressed)
	undo_scan_button.pressed.connect(_on_undo_scan_button_pressed)
	search_process.text_changed.connect(_refresh_process_list)
	scan_type.item_selected.connect(_on_scan_type_selected)
	scan_results_tree.item_selected.connect(_on_scan_result_selected)

	process_list_timer = Timer.new()
	process_list_timer.wait_time = 2.0
	process_list_timer.one_shot = false
	process_list_timer.timeout.connect(_on_process_list_timer_timeout)
	add_child(process_list_timer)

	status_timer = Timer.new()
	status_timer.wait_time = 1.0
	status_timer.one_shot = false
	status_timer.timeout.connect(_on_status_timer_timeout)
	add_child(status_timer)

	hub.hide()
	pick_process.hide()
	pick_game.hide()
	RPCManager.connect_to_server("ws://localhost:8765")

	scan_results_tree.set_column_title(0, "Address")
	scan_results_tree.set_column_title(1, "Previous")
	scan_results_tree.set_column_title(2, "Current")
	scan_results_tree.set_column_expand(0, true)
	scan_results_tree.set_column_expand(1, true)
	scan_results_tree.set_column_expand(2, true)
	scan_results_tree.set_column_title_alignment(0, HORIZONTAL_ALIGNMENT_LEFT)
	scan_results_tree.set_column_title_alignment(1, HORIZONTAL_ALIGNMENT_LEFT)
	scan_results_tree.set_column_title_alignment(2, HORIZONTAL_ALIGNMENT_LEFT)
	scan_results_tree.create_item()

	cheat_table.set_column_title(0, "Address")
	cheat_table.set_column_title(1, "Value")
	cheat_table.set_column_title(2, "Type")
	cheat_table.set_column_title(3, "Frozen")
	cheat_table.set_column_expand(0, true)
	cheat_table.set_column_expand(1, true)
	cheat_table.set_column_expand(2, false)
	cheat_table.set_column_expand(3, false)
	cheat_table.set_column_custom_minimum_width(2, 60)
	cheat_table.set_column_custom_minimum_width(3, 60)
	cheat_table.set_column_title_alignment(0, HORIZONTAL_ALIGNMENT_LEFT)
	cheat_table.set_column_title_alignment(1, HORIZONTAL_ALIGNMENT_LEFT)
	cheat_table.set_column_title_alignment(2, HORIZONTAL_ALIGNMENT_LEFT)
	cheat_table.set_column_title_alignment(3, HORIZONTAL_ALIGNMENT_LEFT)
	cheat_table.create_item()

	watchpoint_log.set_column_title(0, "Type")
	watchpoint_log.set_column_title(1, "Instruction")
	watchpoint_log.set_column_title(2, "Address")
	watchpoint_log.set_column_expand(0, false)
	watchpoint_log.set_column_expand(1, true)
	watchpoint_log.set_column_expand(2, true)
	watchpoint_log.set_column_custom_minimum_width(0, 60)
	watchpoint_log.set_column_title_alignment(0, HORIZONTAL_ALIGNMENT_LEFT)
	watchpoint_log.set_column_title_alignment(1, HORIZONTAL_ALIGNMENT_LEFT)
	watchpoint_log.set_column_title_alignment(2, HORIZONTAL_ALIGNMENT_LEFT)
	watchpoint_log.create_item()


var status_timer: Timer

func _input(event: InputEvent) -> void:
	if event is InputEventJoypadButton or event is InputEventJoypadMotion:
		get_viewport().set_input_as_handled()

func _process(_delta: float) -> void:
	if not connected:
		RPCManager.connect_to_server("ws://localhost:8765")

func _switch_scan_controls(status: bool) -> void:
	second_scan_button.disabled = !status
	undo_scan_button.disabled = !status

func populate_process_list(data: Array) -> void:
	process_list_items.clear()
	for proc in data:
		process_list_items.append(proc)

func _refresh_process_list(filter: String) -> void:
	process_list.clear()
	for proc in process_list_items:
		if not search_process.text or proc.name.containsn(filter):
			process_list.add_item("%s %s" % [int(proc.pid), proc.name])

func _is_valueless_scan_type(id: int) -> bool:
	return id == 3 or id == 4 or id == 5  # INCREASED, DECREASED, or UNKNOWN

func _on_scan_type_selected(_index: int) -> void:
	var selected_id = scan_type.get_selected_id()
	scan_value.editable = not _is_valueless_scan_type(selected_id)

func populate_scan_results(data: Array) -> void:
	var root := scan_results_tree.get_root()
	for child in root.get_children():
		child.free()

	for scan_result in data:
		var prev_val = scan_result.get("previousValue", scan_result.value)
		var item := scan_results_tree.create_item(root)
		item.set_metadata(0, scan_result)
		item.set_text(0, scan_result.address)
		item.set_text(1, str(prev_val))
		item.set_text(2, str(scan_result.value))
		if scan_result.value != prev_val:
			item.set_custom_color(0, Color.RED)
			item.set_custom_color(1, Color.RED)
			item.set_custom_color(2, Color.RED)


func _on_process_activated(index: int):
	var process_text = process_list.get_item_text(index)
	var pid = int(process_text.split(" ")[0])
	print("Attaching to %s" % pid)
	RPCManager.send_message({"command": "attach", "params": {"pid": pid}})

func _on_connected() -> void:
	connected = true
	status_timer.start()
	RPCManager.send_message({"command": "status"})

func _on_status_timer_timeout() -> void:
	RPCManager.send_message({"command": "status"})

func _on_process_list_timer_timeout() -> void:
	RPCManager.send_message({"command": "list-processes"})

func _on_disconnected() -> void:
	print("Disconnected from the WS.")
	connected = false
	status_timer.stop()

func _on_game_activated(index: int) -> void:
	var app_id = game_list_items[index].app_id
	RPCManager.send_message({"command": "select-proton-game", "params": {"app_id": app_id}})

func _on_game_refresh_pressed() -> void:
	RPCManager.send_message({"command": "list-proton-games"})

func _populate_game_list(data: Array) -> void:
	game_list_items = data
	game_list.clear()
	for g in data:
		game_list.add_item("%s (%s)" % [g.name, g.app_id])

func _on_message(data: Dictionary) -> void:
	if not data.has("event"):
		return
	var event = data["event"]
	var payload = data["data"]

	match event:
		"list-proton-games":
			_populate_game_list(payload)
		"select-proton-game":
			game_selected = true
			pick_game.hide()
			pick_process.show()
			RPCManager.send_message({"command": "list-processes"})
			process_list_timer.start()
		"list-processes":
			populate_process_list(payload)
			_refresh_process_list(search_process.text)
		"attach":
			print("Successfully attached to %d!" % payload)
			process_list_timer.stop()
			pick_process.hide()
			hub.show()
		"first-scan", "next-scan":
			scan_results_label.text = "Scan Results (%s)" % _format_count(payload)
		"current-scan-results":
			populate_scan_results(payload)
			if not is_scan:
				is_scan = true
				_switch_scan_controls(true)
		"scan-progress":
			scan_progress_bar.visible = true
			scan_progress_bar.value = float(payload.current) / float(payload.total) * 100.0
			if payload.current == payload.total:
				scan_progress_bar.visible = false
		"status":
			provider = payload.provider
			if payload.state == "attached":
				attached = true
				stay_on_hub = false
				process_list_timer.stop()
				hub.show()
				pick_process.hide()
				pick_game.hide()
			elif stay_on_hub:
				pass
			elif attached:
				# just detached, keep hub visible so logs are readable
				attached = false
				stay_on_hub = true
			elif provider == "proton" and not game_selected:
				if not pick_game.visible:
					hub.hide()
					pick_process.hide()
					pick_game.show()
					RPCManager.send_message({"command": "list-proton-games"})
			else:
				if process_list_timer.is_stopped():
					RPCManager.send_message({"command": "list-processes"})
					process_list_timer.start()
				hub.hide()
				pick_process.show()
				pick_game.hide()
		"watch":
			_update_cheat_table_values(payload)
		"watchpoint-hit":
			_add_watchpoint_log_entry(payload)

func _on_first_scan_button_pressed() -> void:
	var selected_scan_type = scan_type.get_selected_id()
	if selected_scan_type == 3 or selected_scan_type == 4:  # INCREASED or DECREASED
		return
	var value = 0 if _is_valueless_scan_type(selected_scan_type) else int(scan_value.text)
	RPCManager.send_message({
		"command": "first-scan",
		"params": {
			"value": value,
			"data_type": data_type.get_selected_id(),
			"scan_type": selected_scan_type
		}
	})

func _on_second_scan_button_pressed() -> void:
	var selected_scan_type = scan_type.get_selected_id()
	var value = 0 if _is_valueless_scan_type(selected_scan_type) else int(scan_value.text)
	RPCManager.send_message({
		"command": "next-scan",
		"params": {
			"value": value,
			"data_type": data_type.get_selected_id(),
			"scan_type": selected_scan_type
		}
	})

func _on_undo_scan_button_pressed() -> void:
	RPCManager.send_message({"command": "undo-scan"})
	is_scan = false
	_switch_scan_controls(false)
	scan_results_label.text = "Scan Results"


func _on_scan_result_selected() -> void:
	var item = scan_results_tree.get_selected()
	if item:
		selected_scan_result = item.get_metadata(0)

func _on_scan_results_item_activated() -> void:
	if selected_scan_result.is_empty():
		return

	var address_str: String = selected_scan_result.address
	var current_data_type := data_type.get_selected_id()

	if _find_cheat_table_item(address_str):
		return

	var new_entry := {
		"address": address_str,
		"data_type": current_data_type,
		"value": selected_scan_result.value,
		"frozen": false,
		"freeze_mode": 0,
		"watchpoint": ""
	}

	RPCManager.send_message({
		"command": "add-to-watch-list",
		"params": {"address": address_str, "data_type": current_data_type}
	})

	_add_cheat_table_row(new_entry)


func _on_cheat_table_right_click(position: Vector2, mouse_button_index: int) -> void:
	if mouse_button_index != MOUSE_BUTTON_RIGHT:
		return
	selected_cheat_table_item = cheat_table.get_selected()
	if selected_cheat_table_item:
		_build_cheat_table_context_menu(selected_cheat_table_item)
		cheat_table_context_menu.popup(Rect2i(get_global_mouse_position(), Vector2i.ZERO))


func _build_cheat_table_context_menu(item: TreeItem) -> void:
	cheat_table_context_menu.clear()
	cheat_table_context_menu.add_item("Write Value", 0)
	cheat_table_context_menu.add_item("Remove", 1)
	cheat_table_context_menu.add_item("Freeze", 6)
	cheat_table_context_menu.add_item("Scale", 7)
	cheat_table_context_menu.add_separator()
	var entry: Dictionary = item.get_metadata(0)
	var wp: String = entry.get("watchpoint", "")
	if wp == "r":
		cheat_table_context_menu.add_item("Stop Watching Reads", 4)
	else:
		cheat_table_context_menu.add_item("Watch Reads", 2)
	if wp == "w":
		cheat_table_context_menu.add_item("Stop Watching Writes", 5)
	else:
		cheat_table_context_menu.add_item("Watch Writes", 3)


func _on_context_menu_item_selected(id: int) -> void:
	if not selected_cheat_table_item:
		return

	var entry: Dictionary = selected_cheat_table_item.get_metadata(0)

	match id:
		0:  # Write Value
			write_target_address = entry.address
			write_address_dialog.popup_centered()
		1:  # Remove
			_remove_from_cheat_table(selected_cheat_table_item)
		6:  # Freeze
			_show_freeze_dialog(selected_cheat_table_item, 0)
		7:  # Scale
			_show_freeze_dialog(selected_cheat_table_item, 1)
		2:  # Watch Reads
			RPCManager.send_message({
				"command": "set-watchpoint",
				"params": {
					"address": entry.address,
					"data_type": entry.data_type,
					"condition": "r"
				}
			})
			entry["watchpoint"] = "r"
			_update_cheat_table_item(selected_cheat_table_item)
		3:  # Watch Writes
			RPCManager.send_message({
				"command": "set-watchpoint",
				"params": {
					"address": entry.address,
					"data_type": entry.data_type,
					"condition": "w"
				}
			})
			entry["watchpoint"] = "w"
			_update_cheat_table_item(selected_cheat_table_item)
		4, 5:  # Stop Watching Reads/Writes
			RPCManager.send_message({"command": "clear-watchpoint"})
			entry["watchpoint"] = ""
			_update_cheat_table_item(selected_cheat_table_item)


func _on_cheat_table_item_edited() -> void:
	var edited_item := cheat_table.get_edited()
	var column := cheat_table.get_edited_column()

	if column == 3:  # Frozen checkbox column
		var entry: Dictionary = edited_item.get_metadata(0)
		var new_state := edited_item.is_checked(3)
		if new_state and not entry.frozen:
			# Revert checkbox until dialog confirms
			edited_item.set_checked(3, false)
			_show_freeze_dialog(edited_item, 0)
		elif not new_state and entry.frozen:
			_unfreeze(edited_item)


func _show_freeze_dialog(item: TreeItem, mode: int) -> void:
	freeze_pending_item = item
	var entry: Dictionary = item.get_metadata(0)
	var freeze_input: LineEdit = freeze_value_dialog.find_child("FreezeValue", true, false)
	var freeze_mode: OptionButton = freeze_value_dialog.find_child("FreezeMode", true, false)
	var label: Label = freeze_value_dialog.find_child("Label", true, false)
	freeze_mode.select(mode)
	if mode == 1:
		label.text = "Scale factor:"
		freeze_input.text = "2"
		freeze_value_dialog.title = "Scale Value"
	else:
		label.text = "Freeze value:"
		freeze_input.text = str(entry.value) if entry.value != null else ""
		freeze_value_dialog.title = "Freeze With Value"
	freeze_value_dialog.popup_centered()
	freeze_input.select_all()
	freeze_input.grab_focus()


func _on_freeze_value_dialog_confirmed() -> void:
	if not freeze_pending_item:
		return
	var entry: Dictionary = freeze_pending_item.get_metadata(0)
	var freeze_input: LineEdit = freeze_value_dialog.find_child("FreezeValue", true, false)
	var freeze_mode: OptionButton = freeze_value_dialog.find_child("FreezeMode", true, false)
	var mode := freeze_mode.get_selected_id()
	var freeze_value = int(freeze_input.text)
	entry.frozen = true
	entry.freeze_mode = mode
	if mode == 0:
		entry.value = freeze_value
	RPCManager.send_message({
		"command": "add-to-freeze-list",
		"params": {
			"address": entry.address,
			"value": freeze_value,
			"data_type": entry.data_type,
			"mode": mode
		}
	})
	_update_cheat_table_item(freeze_pending_item)
	freeze_pending_item = null


func _on_freeze_value_dialog_canceled() -> void:
	freeze_pending_item = null


func _unfreeze(item: TreeItem) -> void:
	var entry: Dictionary = item.get_metadata(0)
	entry.frozen = false
	RPCManager.send_message({
		"command": "remove-from-freeze-list",
		"params": {"address": entry.address}
	})
	_update_cheat_table_item(item)


func _remove_from_cheat_table(item: TreeItem) -> void:
	var entry: Dictionary = item.get_metadata(0)

	RPCManager.send_message({
		"command": "remove-from-watch-list",
		"params": {"address": entry.address, "data_type": entry.data_type}
	})

	if entry.frozen:
		RPCManager.send_message({
			"command": "remove-from-freeze-list",
			"params": {"address": entry.address}
		})

	item.free()
	selected_cheat_table_item = null


func _add_cheat_table_row(entry: Dictionary) -> void:
	var root := cheat_table.get_root()
	var item := cheat_table.create_item(root)
	item.set_metadata(0, entry)
	item.set_text(0, entry.address)
	item.set_text(1, str(entry.value) if entry.value != null else "?")
	item.set_text(2, _data_type_name(entry.data_type))
	item.set_cell_mode(3, TreeItem.CELL_MODE_CHECK)
	item.set_checked(3, entry.frozen)
	item.set_editable(3, true)


func _update_cheat_table_item(item: TreeItem) -> void:
	var entry: Dictionary = item.get_metadata(0)
	var wp: String = entry.get("watchpoint", "")
	if wp == "r":
		item.set_text(0, "[R] %s" % entry.address)
	elif wp == "w":
		item.set_text(0, "[W] %s" % entry.address)
	else:
		item.set_text(0, entry.address)
	item.set_text(1, str(entry.value) if entry.value != null else "?")
	item.set_checked(3, entry.frozen)
	var fm: int = entry.get("freeze_mode", 0)
	if entry.frozen and fm == 1:
		item.set_custom_color(0, Color.ORANGE)
		item.set_custom_color(1, Color.ORANGE)
	elif entry.frozen:
		item.set_custom_color(0, Color.CYAN)
		item.set_custom_color(1, Color.CYAN)
	elif wp != "":
		item.set_custom_color(0, Color.GREEN)
		item.clear_custom_color(1)
	else:
		item.clear_custom_color(0)
		item.clear_custom_color(1)


func _find_cheat_table_item(address: String) -> TreeItem:
	var root := cheat_table.get_root()
	var child := root.get_first_child()
	while child:
		var entry: Dictionary = child.get_metadata(0)
		if entry.address == address:
			return child
		child = child.get_next()
	return null


func _format_count(n: int) -> String:
	if n >= 1_000_000:
		return "%.1fM" % (n / 1_000_000.0)
	elif n >= 1_000:
		return "%.1fK" % (n / 1_000.0)
	return str(n)

func _data_type_name(dt: int) -> String:
	match dt:
		0: return "U8"
		1: return "U16"
		2: return "U32"
		3: return "U64"
		4: return "FLOAT"
		5: return "DOUBLE"
		6: return "STRING"
		_: return "?"


func _update_cheat_table_values(data: Dictionary) -> void:
	var root := cheat_table.get_root()
	var child := root.get_first_child()
	while child:
		var entry: Dictionary = child.get_metadata(0)
		if data.has(entry.address):
			entry.value = data[entry.address]
			_update_cheat_table_item(child)
		child = child.get_next()


func _on_write_address_dialog_confirmed() -> void:
	var write_input = int(write_address_dialog.find_child("WriteValue", true, false).text)
	print("Writing value: %d to address: %s" % [write_input, write_target_address])
	RPCManager.send_message({
		"command": "write-value",
		"params": {
			"address": write_target_address,
			"value": write_input,
			"data_type": data_type.get_selected_id()
		}
	})


func _clear_watchpoint_state(address: String) -> void:
	var item := _find_cheat_table_item(address)
	if item:
		var entry: Dictionary = item.get_metadata(0)
		entry["watchpoint"] = ""
		_update_cheat_table_item(item)


func _add_watchpoint_log_entry(payload: Dictionary) -> void:
	_clear_watchpoint_state(payload.get("address", ""))
	var root := watchpoint_log.get_root()
	var item := watchpoint_log.create_item(root)
	var op: String = payload.get("operation", "?")
	var pc: String = payload.get("pc", "?")
	var addr: String = payload.get("address", "?")

	item.set_text(0, op.to_upper())
	item.set_text(1, pc)
	item.set_text(2, addr)
	item.set_metadata(0, payload)

	if op == "write":
		item.set_custom_color(0, Color.ORANGE)
	else:
		item.set_custom_color(0, Color.CORNFLOWER_BLUE)


func _on_watchpoint_log_item_activated() -> void:
	var item := watchpoint_log.get_selected()
	if not item:
		return

	var payload: Dictionary = item.get_metadata(0)
	var bbcode := ""

	# Header
	var op: String = payload.get("operation", "?")
	var pc: String = payload.get("pc", "?")
	var addr: String = payload.get("address", "?")
	bbcode += "[b]%s[/b] at [b]%s[/b] accessing [b]%s[/b]\n\n" % [op.to_upper(), pc, addr]

	# Disassembly
	bbcode += "[b]Disassembly:[/b]\n"
	var disasm: Array = payload.get("disassembly", [])
	for i in disasm.size():
		var insn: Dictionary = disasm[i]
		var line := "  %s  %s %s" % [insn.get("address", "?"), insn.get("mnemonic", "?"), insn.get("opStr", "")]
		if i == 0:
			bbcode += "[color=yellow]> %s[/color]\n" % line.strip_edges()
		else:
			bbcode += "%s\n" % line

	# Stack trace
	bbcode += "\n[b]Stack Trace:[/b]\n"
	var bt: Array = payload.get("backtrace", [])
	for i in bt.size():
		bbcode += "  #%d  %s\n" % [i, bt[i]]

	watchpoint_detail_text.text = ""
	watchpoint_detail_text.append_text(bbcode)
	watchpoint_detail_dialog.popup_centered()


func _on_watchpoint_clear_pressed() -> void:
	var root := watchpoint_log.get_root()
	for child in root.get_children():
		child.free()


func _on_save_table_pressed() -> void:
	file_dialog_saving = true
	cheat_table_file_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
	cheat_table_file_dialog.title = "Save Cheat Table"
	cheat_table_file_dialog.popup_centered()

func _on_load_table_pressed() -> void:
	file_dialog_saving = false
	cheat_table_file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	cheat_table_file_dialog.title = "Load Cheat Table"
	cheat_table_file_dialog.popup_centered()

func _on_cheat_table_file_selected(path: String) -> void:
	if file_dialog_saving:
		_save_cheat_table(path)
	else:
		_load_cheat_table(path)

func _save_cheat_table(path: String) -> void:
	var entries: Array = []
	var root := cheat_table.get_root()
	var child := root.get_first_child()
	while child:
		var entry: Dictionary = child.get_metadata(0)
		entries.append({
			"address": entry.address,
			"data_type": entry.data_type,
			"value": entry.value,
			"frozen": entry.frozen,
			"freeze_mode": entry.get("freeze_mode", 0),
		})
		child = child.get_next()
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(entries, "\t"))
	file.close()
	print("Cheat table saved to %s" % path)

func _load_cheat_table(path: String) -> void:
	var file := FileAccess.open(path, FileAccess.READ)
	if not file:
		print("Failed to open %s" % path)
		return
	var json := JSON.new()
	if json.parse(file.get_as_text()) != OK:
		print("Failed to parse cheat table JSON")
		return
	var entries: Array = json.get_data()
	for entry in entries:
		if _find_cheat_table_item(entry.address):
			continue
		var fm := int(entry.get("freeze_mode", 0))
		var new_entry := {
			"address": entry.address,
			"data_type": int(entry.data_type),
			"value": entry.value,
			"frozen": entry.frozen,
			"freeze_mode": fm,
			"watchpoint": ""
		}
		RPCManager.send_message({
			"command": "add-to-watch-list",
			"params": {"address": entry.address, "data_type": int(entry.data_type)}
		})
		if entry.frozen:
			RPCManager.send_message({
				"command": "add-to-freeze-list",
				"params": {"address": entry.address, "value": entry.value, "data_type": int(entry.data_type), "mode": fm}
			})
		_add_cheat_table_row(new_entry)
	print("Cheat table loaded from %s (%d entries)" % [path, entries.size()])
