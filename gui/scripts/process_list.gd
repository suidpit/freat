extends PopupPanel

@onready var item_list: ItemList = $MarginContainer/VBoxContainer/ScrollContainer/ItemList
@onready var attach_button: Button = $MarginContainer/VBoxContainer/HBoxContainer/AttachButton
@onready var cancel_button: Button = $MarginContainer/VBoxContainer/HBoxContainer/CancelButton
@onready var search_bar: LineEdit = $MarginContainer/VBoxContainer/SearchBar

signal process_selected(process_info: Dictionary)

var all_processes: Array = []  # Store all processes

func _ready() -> void:
	connect("about_to_popup", self._on_about_to_popup)

	item_list.item_activated.connect(self._on_item_activated)
	attach_button.pressed.connect(self._on_attach_pressed)
	cancel_button.pressed.connect(self._on_cancel_pressed)
	search_bar.text_changed.connect(self._on_search_text_changed)
	
func _on_about_to_popup() -> void:
	grab_focus()


func populate_process_list(processes: Array) -> void:
	all_processes = processes  # Store the full list
	_filter_processes(search_bar.text)  # Apply current filter

func _on_search_text_changed(new_text: String) -> void:
	_filter_processes(new_text)

func _filter_processes(search_text: String) -> void:
	item_list.clear()  # Clear the current list
	search_text = search_text.to_lower()
	
	for process in all_processes:
		var pid = int(process["pid"])
		var process_name = process["name"].to_lower()
		var pid_str = str(pid)
		
		# Only add items that match the search text
		if search_text == "" or search_text in process_name or search_text in pid_str:
			var display_text = "%s (%s)" % [process["name"], pid]
			item_list.add_item(display_text)
			var index = item_list.get_item_count() - 1
			item_list.set_item_metadata(index, process)

func _on_item_selected() -> void:
	attach_button.disabled = false

func _on_item_activated(_item_index: int) -> void:
	_on_attach_pressed()

func _on_attach_pressed() -> void:
	var selected_indices = item_list.get_selected_items()
	if selected_indices.size() == 0:
		print("No process selected")
		return

	var selected_index = selected_indices[0]
	var process_info = item_list.get_item_metadata(selected_index)
	if process_info:
		emit_signal("process_selected", process_info)
		hide()
	else:
		print("No process info found")

func _on_cancel_pressed() -> void:
	hide()
		
func _unhandled_key_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		hide()
		get_viewport().set_input_as_handled()
