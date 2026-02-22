class_name MultiSelectTree
extends Tree

var _shift_anchor: TreeItem = null

func _gui_input(event: InputEvent) -> void:
	if not event is InputEventMouseButton:
		return
	var mb := event as InputEventMouseButton
	if mb.button_index != MOUSE_BUTTON_LEFT or not mb.pressed:
		return
	# Let double-clicks pass through so item_activated fires.
	if mb.double_click:
		return

	var item := get_item_at_position(mb.position)
	if not item:
		deselect_all()
		_shift_anchor = null
		accept_event()
		return

	if mb.shift_pressed and _shift_anchor:
		deselect_all()
		var in_range := false
		var child := get_root().get_first_child()
		while child:
			var is_endpoint := (child == item or child == _shift_anchor)
			if is_endpoint:
				in_range = not in_range
			if in_range or is_endpoint:
				_select_row(child)
			child = child.get_next()
		accept_event()

	elif mb.ctrl_pressed or mb.meta_pressed:
		if item.is_selected(0):
			_deselect_row(item)
		else:
			_select_row(item)
			_shift_anchor = item
		accept_event()

	else:
		deselect_all()
		_select_row(item)
		_shift_anchor = item
		accept_event()


func _select_row(item: TreeItem) -> void:
	for col in columns:
		item.select(col)


func _deselect_row(item: TreeItem) -> void:
	for col in columns:
		item.deselect(col)
