extends Panel

# --- Node References ---
@onready var initial_view: CenterContainer = $InitialView
@onready var processing_view: CenterContainer = $ProcessingView
@onready var main_app_view: HSplitContainer = $MainAppView
@onready var attach_timer: Timer = $AttachTimer
@onready var address_list: ItemList = $MainAppView/LeftPanel/MarginContainer/VBoxContainer/AddressScroll/AddressList
@onready var scan_value_edit: LineEdit = $MainAppView/RightPanel/MarginContainer/VBoxScanControls/HBoxValue/ScanValueEdit
@onready var scan_type_option: OptionButton = $MainAppView/RightPanel/MarginContainer/VBoxScanControls/HBoxType/ScanTypeOption


# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	# Ensure only the initial view is visible at the start
	initial_view.visible = true
	processing_view.visible = false
	main_app_view.visible = false
	print("UI Ready. Initial view shown.")


# --- Signal Handlers ---

func _on_attach_button_pressed() -> void:
	print("Attach button pressed.")
	initial_view.visible = false
	processing_view.visible = true
	main_app_view.visible = false
	attach_timer.start() # Start the delay timer
	print("Processing view shown. Timer started.")


func _on_attach_timer_timeout() -> void:
	print("Attach timer timeout.")
	initial_view.visible = false
	processing_view.visible = false
	main_app_view.visible = true
	print("Main app view shown.")
	
	# --- Mock attaching process and populate list ---
	# In a real app, you'd do actual process attachment here
	# For now, just add dummy data to the address list
	_mock_populate_address_list()


func _on_first_scan_button_pressed() -> void:
	var value = scan_value_edit.text
	var type_id = scan_type_option.selected
	var type_text = scan_type_option.get_item_text(type_id)
	print("First Scan initiated. Value: '", value, "', Type: '", type_text, "' (ID:", type_id, ")")
	# --- Mock scan result ---
	address_list.clear() # Clear previous results for first scan
	address_list.add_item("0x%08X - Value: %s (Mock)" % [randi() % 0xFFFFFFF, value])
	address_list.add_item("0x%08X - Value: %s (Mock)" % [randi() % 0xFFFFFFF, value])
	address_list.add_item("0x%08X - Value: %s (Mock)" % [randi() % 0xFFFFFFF, value])
	print("Mock results added to list.")


func _on_next_scan_button_pressed() -> void:
	var value = scan_value_edit.text
	var type_id = scan_type_option.selected
	var type_text = scan_type_option.get_item_text(type_id)
	print("Next Scan initiated. Value: '", value, "', Type: '", type_text, "' (ID:", type_id, ")")
	# --- Mock next scan (just remove one item) ---
	if address_list.item_count > 0:
		address_list.remove_item(randi() % address_list.item_count)
		print("Mock item removed from list.")
	else:
		print("No items left to remove.")


func _on_reset_scan_button_pressed() -> void:
	print("Reset Scan pressed.")
	address_list.clear()
	scan_value_edit.clear()
	print("Address list and value cleared.")


# --- Helper Functions ---

func _mock_populate_address_list() -> void:
	address_list.clear()
	# Add some dummy entries after "attaching"
	address_list.add_item("0x00401000 - Base Address (Mock)")
	address_list.add_item("0x7FFAC123 - Player Health (Mock)")
	address_list.add_item("0x7FFBD456 - Ammo Count (Mock)")
	print("Mock address list populated.")
