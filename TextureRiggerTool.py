import maya.cmds as cmds
import importlib
import re

# Import logic files
import step1_logic
import step2_logic
import step3_logic
import step3_uv_logic  # Add import for the new module

# For reloading modules during development (optional)
importlib.reload(step1_logic)
importlib.reload(step2_logic)
importlib.reload(step3_logic)
importlib.reload(step3_uv_logic)  # Add reload for the new module

class TextureRiggerUI:
    def __init__(self):
        self.window_name = "textureRiggerMainWindow"
        self.ui_title = "Texture Rigger 0.1.0"

        self.selected_mesh_transform = None
        self.selected_mesh_shape = None
        
        self.locators_data = {}
        self.follicles_data = {}
        self.textures_data = {}
        
        self.name_prefix = "Prefix"

        self.name_field = None

        self.step1_frame = None
        self.select_mesh_button = None
        self.create_locator_button = None
        self.delete_locator_button = None
        self.locator_list_widget = None
        self.step1_status_label = None

        # Mirror options
        self.mirror_checkbox = None
        self.mirror_options_layout = None
        self.mirror_axis_radios = None
        self.mirror_side_radios = None

        self.step2_frame = None
        self.create_follicles_button = None
        self.step2_status_label = None

        # Control shape/color
        self.ctrl_shape_menu = None
        self.ctrl_color_menu = None
        
        self.step3_frame = None
        self.step3_top_col_layout = None
        self.texture_selection_layout = None
        self.texture_path_fields = {}
        self.select_texture_buttons = {}
        self.connect_all_textures_button = None
        self.step3_status_label = None

        self.sequence_checkboxes = {}
        self.projection_checkboxes = {}

        # Layer ordering (inside Step 3, pre-connect)
        self.texture_order = []  # ordered list of prefixes for layeredTexture input order
        self.order_list_widget = None

        # Post-connect layer reorder (for edit existing setup)
        self.layer_frame = None
        self.layer_list_widget = None
        self.layer_texture_node = None

        # Existing setup edit
        self.edit_frame = None
        self.edit_setup_menu = None
        self.found_setups = []

    def on_window_close(self, *args):
        self.reset_tool_state()
        step1_logic.clear_reference_follicle()

    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

        self.window = cmds.window(
            self.window_name, 
            title=self.ui_title, 
            widthHeight=(450, 600),
            sizeable=True,
            closeCommand=self.on_window_close
        )
        
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10, parent=self.window)

        self.step1_frame = cmds.frameLayout("step1_frame", label="STEP 1: Select Mesh & Create Locators", collapsable=False, collapse=False, parent=main_layout, marginWidth=10, marginHeight=5)
        step1_col_layout = cmds.columnLayout(adjustableColumn=True, parent=self.step1_frame, rowSpacing=5)
        
        self.select_mesh_button = cmds.button(label="Select Mesh", command=self.on_select_mesh_click, parent=step1_col_layout, height=30)
        
        name_row_layout = cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 80), (2, 300)], parent=step1_col_layout, rowSpacing=(1,3))
        cmds.text(label="Prefix:", align="right")
        self.name_field = cmds.textField(text=self.name_prefix, parent=name_row_layout, 
                                    changeCommand=self.on_name_changed)
        cmds.setParent("..")
        
        self.create_locator_button = cmds.button(label="Create Locator", command=self.on_create_locator_click, parent=step1_col_layout, height=30, enable=False)

        # --- Mirror Options ---
        self.mirror_checkbox = cmds.checkBox(label="Mirror", value=False, changeCommand=self._on_mirror_toggle, parent=step1_col_layout)
        self.mirror_options_layout = cmds.rowColumnLayout(numberOfColumns=4, columnWidth=[(1, 80), (2, 100), (3, 80), (4, 100)], parent=step1_col_layout, visible=False)
        cmds.text(label="Axis:", align="right")
        self.mirror_axis_radios = cmds.radioCollection()
        mirror_axis_row = cmds.rowLayout(numberOfColumns=3, parent=self.mirror_options_layout)
        cmds.radioButton('mirror_X', label='X', select=True, collection=self.mirror_axis_radios)
        cmds.radioButton('mirror_Y', label='Y', collection=self.mirror_axis_radios)
        cmds.radioButton('mirror_Z', label='Z', collection=self.mirror_axis_radios)
        cmds.setParent('..')
        cmds.text(label="Original:", align="right")
        self.mirror_side_radios = cmds.radioCollection()
        mirror_side_row = cmds.rowLayout(numberOfColumns=2, parent=self.mirror_options_layout)
        cmds.radioButton('mirror_L', label='L_', select=True, collection=self.mirror_side_radios)
        cmds.radioButton('mirror_R', label='R_', collection=self.mirror_side_radios)
        cmds.setParent('..')
        cmds.setParent('..')

        # --- Locator List + Delete ---
        cmds.text(label="Created Locators:", align="left", parent=step1_col_layout)
        locator_list_row = cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 330), (2, 80)], parent=step1_col_layout)
        self.locator_list_widget = cmds.textScrollList(numberOfRows=4, allowMultiSelection=False, parent=locator_list_row, height=60)
        self.delete_locator_button = cmds.button(label="Delete", command=self.on_delete_locator_click, parent=locator_list_row, height=60, enable=False)
        cmds.setParent('..')
        
        self.step1_status_label = cmds.text(label="Status: Waiting for mesh selection...", align="left", parent=step1_col_layout)
        cmds.button(label="Revert Step 1", command=self._on_revert_step1, parent=step1_col_layout, height=25)
        cmds.setParent("..")
        cmds.setParent("..")

        self.step2_frame = cmds.frameLayout("step2_frame", label="STEP 2: Create Follicles and Control Curves", collapsable=False, collapse=False, parent=main_layout, marginWidth=10, marginHeight=5, enable=False)
        step2_col_layout = cmds.columnLayout(adjustableColumn=True, parent=self.step2_frame, rowSpacing=5)
        cmds.text(label="Move the created locators to desired positions on the mesh.", align="left", parent=step2_col_layout)

        # Control shape/color options
        ctrl_options_row = cmds.rowColumnLayout(numberOfColumns=4, columnWidth=[(1, 80), (2, 120), (3, 80), (4, 120)], parent=step2_col_layout, rowSpacing=(1,3))
        cmds.text(label="Ctrl Shape:", align="right")
        self.ctrl_shape_menu = cmds.optionMenu()
        for shape_name in step2_logic.CONTROL_SHAPES:
            cmds.menuItem(label=shape_name)
        cmds.text(label="Ctrl Color:", align="right")
        self.ctrl_color_menu = cmds.optionMenu()
        for color_name in step2_logic.CONTROL_COLORS.keys():
            cmds.menuItem(label=color_name)
        cmds.setParent("..")

        self.create_follicles_button = cmds.button(label="Create Follicles and Control Curves", command=self.on_create_follicles_click, parent=step2_col_layout, height=30)
        self.step2_status_label = cmds.text(label="Status: Waiting for locator positioning and follicle creation...", align="left", parent=step2_col_layout)
        cmds.button(label="Revert Step 2", command=self._on_revert_step2, parent=step2_col_layout, height=25)
        cmds.setParent("..")
        cmds.setParent("..")

        self.step3_frame = cmds.frameLayout("step3_frame", label="STEP 3: Select Textures & Connect to Materials", collapsable=False, collapse=False, parent=main_layout, marginWidth=10, marginHeight=5, enable=False)
        self.step3_top_col_layout = cmds.columnLayout(adjustableColumn=True, parent=self.step3_frame, rowSpacing=5)

        self.texture_selection_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=3, parent=self.step3_top_col_layout) 
        cmds.setParent("..")

        # --- Layer Ordering (inside Step 3, pre-connect) ---
        cmds.separator(height=8, style='in', parent=self.step3_top_col_layout)
        cmds.text(label="Layer Order (top = layeredTexture input[0]):", align="left", parent=self.step3_top_col_layout)
        self.order_list_widget = cmds.textScrollList(numberOfRows=5, allowMultiSelection=False, parent=self.step3_top_col_layout, height=80)
        order_btn_row = cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 210), (2, 210)], parent=self.step3_top_col_layout)
        cmds.button(label="Move Up", command=self._on_order_move_up)
        cmds.button(label="Move Down", command=self._on_order_move_down)
        cmds.setParent("..")

        self.connect_all_textures_button = cmds.button(label="Connect All Selected Textures to Materials", command=self.on_connect_all_textures_click, parent=self.step3_top_col_layout, height=30, enable=False)
        self.step3_status_label = cmds.text(label="Status: Waiting for follicle creation to enable texture selection...", align="left", parent=self.step3_top_col_layout)
        cmds.button(label="Revert Step 3", command=self._on_revert_step3, parent=self.step3_top_col_layout, height=25)
        cmds.setParent("..")
        cmds.setParent("..")

        # --- Layer Ordering Panel (post-connect / edit existing setup) ---
        self.layer_frame = cmds.frameLayout("layer_frame", label="Reorder Existing Layers", collapsable=True, collapse=True, parent=main_layout, marginWidth=10, marginHeight=5, enable=False)
        layer_col_layout = cmds.columnLayout(adjustableColumn=True, parent=self.layer_frame, rowSpacing=5)
        cmds.text(label="Drag layers to reorder (index 0 = top layer):", align="left", parent=layer_col_layout)
        self.layer_list_widget = cmds.textScrollList(numberOfRows=5, allowMultiSelection=False, parent=layer_col_layout, height=80)
        layer_btn_row = cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 200), (2, 200)], parent=layer_col_layout)
        cmds.button(label="Move Up", command=self._on_layer_move_up)
        cmds.button(label="Move Down", command=self._on_layer_move_down)
        cmds.setParent("..")
        cmds.setParent("..")
        cmds.setParent("..")

        # --- Existing Setup Edit Panel ---
        self.edit_frame = cmds.frameLayout("edit_frame", label="Edit Existing Setup", collapsable=True, collapse=True, parent=main_layout, marginWidth=10, marginHeight=5)
        edit_col_layout = cmds.columnLayout(adjustableColumn=True, parent=self.edit_frame, rowSpacing=5)
        cmds.button(label="Scan Scene for Setups", command=self._on_scan_setups_click, height=25)
        self.edit_setup_menu = cmds.optionMenu(label="Found Setups:")
        cmds.menuItem(label="(none)")
        cmds.button(label="Load Selected Setup", command=self._on_load_setup_click, height=25)
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.showWindow(self.window)

    def on_name_changed(self, new_name):
        if not new_name or new_name.isspace():
            self.name_prefix = "textureRig" 
            cmds.textField(self.name_field, edit=True, text=self.name_prefix)
            cmds.warning("Prefix cannot be empty. Using default 'textureRig'.")
        else:
            cleaned_name = ''.join(c for c in new_name if c.isalnum() or c == '_')
            if cleaned_name != new_name:
                cmds.textField(self.name_field, edit=True, text=cleaned_name)
            self.name_prefix = cleaned_name

    def _is_prefix_unique(self, prefix_to_check):
        return prefix_to_check not in self.locators_data

    def _on_mirror_toggle(self, state):
        cmds.rowColumnLayout(self.mirror_options_layout, edit=True, visible=state)

    def _on_undo_click(self, *args):
        """Deprecated - kept for compatibility."""
        pass

    def _on_revert_step1(self, *args):
        """Reverts Step 1: deletes all locators and reference follicle, resets to initial state."""
        # Delete all locators from scene
        for prefix, locator_name in list(self.locators_data.items()):
            if cmds.objExists(locator_name):
                cmds.delete(locator_name)
        
        # Also revert step 2 & 3 if they were executed
        self._delete_step2_nodes()
        self._delete_step3_nodes()
        
        # Full reset
        self.reset_tool_state()
        self.update_step1_status("Step 1 reverted. All locators deleted.", success=True)

    def _on_revert_step2(self, *args):
        """Reverts Step 2: deletes all follicles, controls, utility nodes. Returns to Step 1 state."""
        self._delete_step2_nodes()
        self._delete_step3_nodes()
        
        # Reset step 2 and step 3 UI
        self.reset_step2_and_beyond()
        
        # Re-enable Step 1 locator creation (mesh is still selected)
        if self.selected_mesh_transform and self.selected_mesh_shape:
            cmds.button(self.create_locator_button, edit=True, enable=True)
            cmds.textField(self.name_field, edit=True, enable=True)
            self.update_step1_status(f"Step 2 reverted. Mesh '{self.selected_mesh_transform}' still selected. Create new locators.", success=True)
        else:
            self.update_step1_status("Step 2 reverted.", success=True)

    def _on_revert_step3(self, *args):
        """Reverts Step 3: deletes all texture nodes created. Returns to Step 2 completed state."""
        self._delete_step3_nodes()
        
        # Reset step 3 UI but keep follicle data
        saved_follicles = dict(self.follicles_data)
        
        # Clear step 3 UI
        cmds.frameLayout(self.step3_frame, edit=True, enable=False)
        children = cmds.columnLayout(self.texture_selection_layout, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        self.texture_path_fields.clear()
        self.select_texture_buttons.clear()
        self.sequence_checkboxes.clear()
        self.projection_checkboxes.clear()
        cmds.button(self.connect_all_textures_button, edit=True, enable=False)
        self.textures_data.clear()
        self.texture_order = []
        cmds.textScrollList(self.order_list_widget, edit=True, removeAll=True)
        
        # Reset layer ordering
        cmds.frameLayout(self.layer_frame, edit=True, enable=False, collapse=True)
        cmds.textScrollList(self.layer_list_widget, edit=True, removeAll=True)
        self.layer_texture_node = None
        
        # Restore follicle data and re-populate step 3
        self.follicles_data = saved_follicles
        if self.follicles_data:
            self._populate_texture_selection_ui()
            cmds.frameLayout(self.step3_frame, edit=True, enable=True)
            cmds.button(self.connect_all_textures_button, edit=True, enable=True)
            self.update_step3_status(f"Step 3 reverted. Select textures for {len(self.follicles_data)} prefix(es).", success=True)

    def _delete_step2_nodes(self):
        """Deletes all nodes created by Step 2 (follicles, controls, DG utility nodes)."""
        for prefix, fol_data in list(self.follicles_data.items()):
            follicle_trans = fol_data.get('follicle')
            
            # Delete the follicle transform hierarchy (includes ctrl, bind, position_grp etc.)
            if follicle_trans and cmds.objExists(follicle_trans):
                cmds.delete(follicle_trans)
            
            # Delete DG utility nodes that are not in the hierarchy
            dg_suffixes = [
                '_compMat', '_multMat', '_decomMat',
                '_Translate_Invert', '_Invert_U', '_Invert_V',
                '_Precision_U', '_Precision_V',
                '_pos_U_driver', '_pos_V_driver', '_clamp',
                '_ReverseRotate_md', '_ScaleFactor_md'
            ]
            for suffix in dg_suffixes:
                node_name = f"{prefix}{suffix}"
                if cmds.objExists(node_name):
                    try:
                        cmds.delete(node_name)
                    except Exception:
                        pass
            
            # Delete Texture_ctrl_grp if it exists
            ctrl_grp = f"{prefix}_Texture_ctrl_grp"
            if cmds.objExists(ctrl_grp):
                cmds.delete(ctrl_grp)
        
        # Clean up empty RIG and UTIL groups under TextureRigSystem if they're empty
        if cmds.objExists("TextureRigSystem"):
            for grp_name in ["RIG", "UTIL"]:
                children = cmds.listRelatives("TextureRigSystem", children=True, type="transform", fullPath=True) or []
                for child in children:
                    if child.split('|')[-1] == grp_name:
                        grp_children = cmds.listRelatives(child, children=True) or []
                        if not grp_children:
                            cmds.delete(child)
            
            # Delete TextureRigSystem if empty
            remaining = cmds.listRelatives("TextureRigSystem", children=True) or []
            if not remaining:
                # Unlock and delete attribute before deleting
                if cmds.attributeQuery("isTextureRiggerSetup", node="TextureRigSystem", exists=True):
                    cmds.setAttr("TextureRigSystem.isTextureRiggerSetup", lock=False)
                if cmds.attributeQuery("textureRiggerVersion", node="TextureRigSystem", exists=True):
                    cmds.setAttr("TextureRigSystem.textureRiggerVersion", lock=False)
                cmds.delete("TextureRigSystem")

    def _delete_step3_nodes(self):
        """Deletes all texture nodes created by Step 3."""
        for prefix, tex_data in list(self.textures_data.items()):
            # Delete file node
            file_node = tex_data.get('file_node')
            if file_node and cmds.objExists(file_node):
                cmds.delete(file_node)
            
            # Delete projection node
            proj_node = tex_data.get('projection_node')
            if proj_node and cmds.objExists(proj_node):
                cmds.delete(proj_node)
            
            # Delete place2d node
            place2d = tex_data.get('place2d_node')
            if place2d and cmds.objExists(place2d):
                cmds.delete(place2d)
            
            # Delete place3d node (and its constraints)
            place3d = tex_data.get('place3d_node')
            if place3d and cmds.objExists(place3d):
                cmds.delete(place3d)
            
            # Delete alpha-related nodes by naming convention
            alpha_nodes = [
                f"{prefix}_alpha_layeredTexture",
                f"{prefix}_alpha_projection"
            ]
            for node_name in alpha_nodes:
                if cmds.objExists(node_name):
                    try:
                        cmds.delete(node_name)
                    except Exception:
                        pass
            
            # Delete UV-based setup nodes
            uv_nodes = [
                f"{prefix}_UV_Ref",
                f"{prefix}_Texture_Rotate",
                f"{prefix}_Texture_Ref",
                f"{prefix}_Texture_Control",
                f"{prefix}_Constraints",
                f"{prefix}_ParentConstraint",
                f"{prefix}_ScaleConstraint",
                f"{prefix}_OrientConstraint"
            ]
            for node_name in uv_nodes:
                if cmds.objExists(node_name):
                    try:
                        cmds.delete(node_name)
                    except Exception:
                        pass

    def on_delete_locator_click(self, *args):
        selected_items = cmds.textScrollList(self.locator_list_widget, query=True, selectItem=True)
        if not selected_items:
            self.update_step1_status("No locator selected in the list.", success=False)
            return
        
        selected_text = selected_items[0]
        prefix = selected_text.split(":")[0].strip()
        
        if prefix in self.locators_data:
            locator_name = self.locators_data[prefix]
            if cmds.objExists(locator_name):
                cmds.delete(locator_name)
            del self.locators_data[prefix]
            self._update_locator_list_widget()
            self.update_step1_status(f"Deleted locator for prefix '{prefix}'.", success=True)
            
            if not self.locators_data:
                cmds.button(self.delete_locator_button, edit=True, enable=False)

    def _update_locator_list_widget(self):
        cmds.textScrollList(self.locator_list_widget, edit=True, removeAll=True)
        for prefix, locator_name in self.locators_data.items():
            cmds.textScrollList(self.locator_list_widget, edit=True, append=f"{prefix}: {locator_name}")

    def _update_status(self, status_label, message, success=None):
        color = (0.9, 0.9, 0.9)
        if success is True: color = (0.6, 0.9, 0.6)
        elif success is False: color = (0.9, 0.6, 0.6)
        cmds.text(status_label, edit=True, label=f"Status: {message}", backgroundColor=color)
        
    def update_step1_status(self, message, success=None):
        self._update_status(self.step1_status_label, message, success)

    def update_step2_status(self, message, success=None):
        self._update_status(self.step2_status_label, message, success)

    def update_step3_status(self, message, success=None):
        self._update_status(self.step3_status_label, message, success)

    def on_create_follicles_click(self, *args):
        if not self.selected_mesh_shape:
            self.update_step2_status("Mesh not selected from Step 1.", success=False)
            return
        if not self.locators_data:
            self.update_step2_status("No locators created in Step 1.", success=False)
            return

        # Get control shape/color selections
        ctrl_shape = cmds.optionMenu(self.ctrl_shape_menu, query=True, value=True)
        ctrl_color = cmds.optionMenu(self.ctrl_color_menu, query=True, value=True)

        cmds.undoInfo(openChunk=True, chunkName="TextureRigger_CreateFollicles")
        try:
            step1_logic.clear_reference_follicle()

            # --- Generate mirror locators from positioned locators ---
            is_mirror = cmds.checkBox(self.mirror_checkbox, query=True, value=True)
            if is_mirror:
                selected_axis_radio = cmds.radioCollection(self.mirror_axis_radios, query=True, select=True)
                mirror_axis = selected_axis_radio.replace('mirror_', '') if selected_axis_radio else 'X'
                
                selected_side_radio = cmds.radioCollection(self.mirror_side_radios, query=True, select=True)
                original_side = selected_side_radio.replace('mirror_', '') if selected_side_radio else 'L'
                mirror_side = 'R' if original_side == 'L' else 'L'
                
                # Collect new mirror entries (can't modify dict during iteration)
                mirror_entries = {}
                for prefix, locator_name in list(self.locators_data.items()):
                    if prefix.startswith(f"{original_side}_") and cmds.objExists(locator_name):
                        base = prefix[len(original_side) + 1:]
                        mirror_prefix = f"{mirror_side}_{base}"
                        if mirror_prefix not in self.locators_data:
                            mirror_locator = step1_logic.create_mirrored_locator(
                                locator_name, self.selected_mesh_transform, mirror_axis, mirror_prefix)
                            if mirror_locator:
                                mirror_entries[mirror_prefix] = mirror_locator
                
                self.locators_data.update(mirror_entries)
                self._update_locator_list_widget()
            
            all_successful = True
            created_count = 0
            self.follicles_data.clear()

            for prefix, locator_name in self.locators_data.items():
                if not cmds.objExists(self.selected_mesh_shape) or not cmds.objExists(locator_name):
                    self.update_step2_status(f"Mesh or locator '{locator_name}' (prefix: '{prefix}') no longer exists.", success=False)
                    all_successful = False
                    continue
                    
                follicle_transform, main_control = step2_logic.run_step2_logic(
                    self.selected_mesh_shape, locator_name, prefix,
                    ctrl_shape=ctrl_shape, ctrl_color=ctrl_color)
                
                if follicle_transform and main_control:
                    self.follicles_data[prefix] = {
                        'follicle': follicle_transform, 
                        'control': main_control,
                        'locator_at_creation': locator_name
                    }
                    created_count += 1
                    try:
                        if cmds.objExists(locator_name):
                            cmds.delete(locator_name)
                    except Exception as e:
                        print(f"Could not delete locator '{locator_name}': {e}")
                else:
                    all_successful = False
                    self.update_step2_status(f"Failed to create follicle for prefix '{prefix}'.", success=False)
        finally:
            cmds.undoInfo(closeChunk=True)

        processed_prefixes = list(self.follicles_data.keys())
        for prefix in processed_prefixes:
            if prefix in self.locators_data:
                del self.locators_data[prefix]
        self._update_locator_list_widget()

        if created_count > 0:
            self.update_step2_status(f"Successfully created {created_count} follicle(s)/control(s).", success=True)
            cmds.button(self.create_follicles_button, edit=True, enable=False)
            cmds.button(self.create_locator_button, edit=True, enable=False)
            cmds.textField(self.name_field, edit=True, enable=False)
            
            self._populate_texture_selection_ui()
            cmds.frameLayout(self.step3_frame, edit=True, enable=True)
            self.update_step3_status(f"Select textures for {len(self.follicles_data)} prefix(es).")
            if self.follicles_data:
                cmds.button(self.connect_all_textures_button, edit=True, enable=True)
        elif not self.locators_data:
            self.update_step2_status("No locators available or all failed. Please restart Step 1.", success=False)
        else:
            self.update_step2_status(f"Processed locators. {created_count} created. Some may have failed or remain.", success=all_successful)

    def _populate_texture_selection_ui(self):
        children = cmds.columnLayout(self.texture_selection_layout, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        
        self.texture_path_fields.clear()
        self.select_texture_buttons.clear()
        self.sequence_checkboxes.clear()
        self.projection_checkboxes.clear()  # Clear projection checkboxes
        self.texture_order = []

        if not self.follicles_data:
            cmds.text(label="No follicles created. Cannot select textures.", parent=self.texture_selection_layout)
            return

        for prefix in self.follicles_data.keys():
            self.texture_order.append(prefix)
            # Create main row layout for texture selection
            row_layout = cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 120), (2, 200), (3, 100)], parent=self.texture_selection_layout, rowSpacing=(1,3))
            cmds.text(label=f"Texture for '{prefix}':", align="right")
            path_field = cmds.textField(text="No texture selected", editable=False, width=190) 
            select_button = cmds.button(label="Select File...", command=lambda ignored_arg, p_captured=prefix: self._on_select_single_texture_click(p_captured))
            cmds.setParent("..")
            
            # Create checkboxes row (both sequence and projection)
            checkboxes_row = cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 120), (2, 150), (3, 150)], parent=self.texture_selection_layout, rowSpacing=(1,3))
            cmds.text(label="", align="left")  # Spacer
            seq_checkbox = cmds.checkBox(label="is sequence?", value=False, 
                                       changeCommand=lambda state, p_captured=prefix: self._on_sequence_checkbox_changed(p_captured, state))
            proj_checkbox = cmds.checkBox(label="Projection?", value=True,  # Default to True for backward compatibility
                                       changeCommand=lambda state, p_captured=prefix: self._on_projection_checkbox_changed(p_captured, state))
            cmds.setParent("..")
            
            # Add separator for visual clarity
            cmds.separator(height=5, style='single', parent=self.texture_selection_layout)

            self.texture_path_fields[prefix] = path_field
            self.select_texture_buttons[prefix] = select_button
            self.sequence_checkboxes[prefix] = seq_checkbox
            self.projection_checkboxes[prefix] = proj_checkbox
            
            self.textures_data[prefix] = {
                'file_path': None, 'file_node': None, 'projection_node': None, 
                'place2d_node': None, 'place3d_node': None, 
                'layered_texture': None, 'material': None,
                'is_sequence': False,  # Flag for sequence textures
                'use_projection': True  # Default to True for backward compatibility
            }

        # Populate the ordering list
        self._refresh_order_list()

    def _on_sequence_checkbox_changed(self, prefix, state):
        """
        Handle sequence checkbox state changes.
        
        Args:
            prefix (str): Prefix of the texture
            state (bool): New state of the checkbox
        """
        print(f"Sequence checkbox for '{prefix}' changed to: {state}")
        
        # Update our data structure
        if prefix in self.textures_data:
            self.textures_data[prefix]['is_sequence'] = state
        
        # If we've already created file nodes, update them immediately
        if (prefix in self.textures_data and 
            self.textures_data[prefix]['file_node'] and 
            cmds.objExists(self.textures_data[prefix]['file_node'])):
            
            file_node = self.textures_data[prefix]['file_node']
            slide_ctrl = None
            
            # Find the slide ctrl for this prefix
            if prefix in self.follicles_data and self.follicles_data[prefix]['control']:
                follicle_data = self.follicles_data[prefix]
                control_name = follicle_data['control']
                
                if "_Slide_ctrl" in control_name:
                    slide_ctrl = control_name
                else:
                    # Try to find the Slide ctrl as a child
                    children = cmds.listRelatives(control_name, allDescendents=True, type="transform") or []
                    for child in children:
                        if "_Slide_ctrl" in child:
                            slide_ctrl = child
                            break
            
            if slide_ctrl and file_node:
                step3_logic.setup_sequence_texture(file_node, slide_ctrl, state)
                if state:
                    self.update_step3_status(f"Activated sequence mode for '{prefix}'", success=True)
                else:
                    self.update_step3_status(f"Deactivated sequence mode for '{prefix}'", success=True)

    def _on_projection_checkbox_changed(self, prefix, state):
        """
        Handle projection checkbox state changes.
        
        Args:
            prefix (str): Prefix of the texture
            state (bool): New state of the checkbox
        """
        print(f"Projection checkbox for '{prefix}' changed to: {state}")
        
        # Update our data structure
        if prefix in self.textures_data:
            self.textures_data[prefix]['use_projection'] = state

    def _on_select_single_texture_click(self, prefix):
        file_paths = cmds.fileDialog2(fileMode=1, caption=f"Select Texture for Prefix: {prefix}")
        if file_paths and file_paths[0]:
            selected_file = file_paths[0]
            self.textures_data[prefix]['file_path'] = selected_file
            cmds.textField(self.texture_path_fields[prefix], edit=True, text=selected_file)
            self.update_step3_status(f"Texture for '{prefix}' selected. Ready to connect all.", success=True)
        else:
            self.update_step3_status(f"Texture selection cancelled for '{prefix}'.", success=False)

    def on_connect_all_textures_click(self, *args):
        """
        Process all selected textures and connect them to their respective follicles
        """
        if not self.selected_mesh_transform:
            cmds.warning("No mesh selected or initial locator created. Please complete Step 1.")
            return
        
        if not self.textures_data:
            cmds.warning("No textures selected or locators processed for texture connection.")
            return

        cmds.undoInfo(openChunk=True, chunkName="TextureRigger_ConnectTextures")
        try:
            all_successful = True
            # Iterate in user-specified order (top of list = layeredTexture input[0])
            ordered_prefixes = self.texture_order if self.texture_order else list(self.textures_data.keys())
            for prefix in ordered_prefixes:
                tex_data = self.textures_data.get(prefix)
                if not tex_data:
                    continue
                texture_file_path = tex_data.get('file_path')
                if not texture_file_path or texture_file_path == "No texture selected":
                    cmds.warning(f"No texture file selected for prefix '{prefix}'. Skipping.")
                    continue

                follicle_info = self.follicles_data.get(prefix)
                if not follicle_info:
                    cmds.warning(f"Follicle data not found for prefix '{prefix}'. Cannot connect texture.")
                    all_successful = False
                    continue
                
                created_follicle_transform = follicle_info.get('follicle')
                if not created_follicle_transform:
                    cmds.warning(f"Follicle transform not found for prefix '{prefix}'.")
                    all_successful = False
                    continue
                
                # Get flags
                is_sequence = tex_data.get('is_sequence', False)
                use_projection = tex_data.get('use_projection', True)
                
                if use_projection:
                    # Use original projection-based method
                    file_node, projection_node, place2d_node, place3d_node, layered_texture_node, material_node, updated_mesh_transform = step3_logic.run_step3_logic(
                        mesh_transform=self.selected_mesh_transform,
                        image_file_path=texture_file_path,
                        name_prefix=prefix,
                        follicle_transform=created_follicle_transform,
                        is_sequence=is_sequence
                    )
                    
                    if file_node:
                        self.textures_data[prefix].update({
                            'file_node': file_node,
                            'projection_node': projection_node,
                            'place2d_node': place2d_node,
                            'place3d_node': place3d_node,
                            'layered_texture_node': layered_texture_node,
                            'material_node': material_node
                        })
                        self.selected_mesh_transform = updated_mesh_transform
                    else:
                        cmds.warning(f"Texture connection failed for prefix '{prefix}'.")
                        all_successful = False
                else:
                    # Use UV-based method
                    file_node, projection_node, place2d_node, place3d_node, layered_texture_node, material_node, updated_mesh_transform = step3_uv_logic.run_step3_uv_logic(
                        mesh_transform=self.selected_mesh_transform,
                        image_file_path=texture_file_path,
                        name_prefix=prefix,
                        follicle_transform=created_follicle_transform,
                        is_sequence=is_sequence
                    )
                    
                    if file_node:
                        self.textures_data[prefix].update({
                            'file_node': file_node,
                            'projection_node': projection_node,
                            'place2d_node': place2d_node,
                            'place3d_node': place3d_node,
                            'layered_texture_node': layered_texture_node,
                            'material_node': material_node
                        })
                        self.selected_mesh_transform = updated_mesh_transform
                    else:
                        cmds.warning(f"Texture connection failed for prefix '{prefix}'.")
                        all_successful = False

            if all_successful:
                cmds.headsUpMessage(f"All selected textures connected and scene organized.", time=5.0)
                self._enable_layer_ordering()
                self.reset_tool_state()
            else:
                cmds.warning("Some textures could not be connected. Check the script editor.")
        finally:
            cmds.undoInfo(closeChunk=True)

    def reset_step2_and_beyond(self):
        cmds.frameLayout(self.step2_frame, edit=True, enable=False)
        cmds.button(self.create_follicles_button, edit=True, enable=True)
        self.update_step2_status("Waiting for locator positioning and follicle creation...")
        self.follicles_data.clear()

        cmds.frameLayout(self.step3_frame, edit=True, enable=False)
        children = cmds.columnLayout(self.texture_selection_layout, query=True, childArray=True) or []
        for child in children: cmds.deleteUI(child)
        self.texture_path_fields.clear()
        self.select_texture_buttons.clear()
        self.sequence_checkboxes.clear()
        self.projection_checkboxes.clear()
        cmds.button(self.connect_all_textures_button, edit=True, enable=False)
        self.update_step3_status("Waiting for follicle creation to enable texture selection...")
        self.textures_data.clear()
        self.texture_order = []
        cmds.textScrollList(self.order_list_widget, edit=True, removeAll=True)

        # Reset layer ordering
        cmds.frameLayout(self.layer_frame, edit=True, enable=False, collapse=True)
        cmds.textScrollList(self.layer_list_widget, edit=True, removeAll=True)
        self.layer_texture_node = None

    def reset_tool_state(self):
        self.selected_mesh_transform = None
        self.selected_mesh_shape = None
        
        self.locators_data.clear()
        self._update_locator_list_widget()
        
        self.reset_step2_and_beyond()

        cmds.button(self.select_mesh_button, edit=True, enable=True)
        cmds.button(self.create_locator_button, edit=True, enable=False)
        cmds.button(self.delete_locator_button, edit=True, enable=False)
        
        default_prefix = "Prefix"
        self.name_prefix = default_prefix
        cmds.textField(self.name_field, edit=True, text=default_prefix, enable=True)
        
        self.update_step1_status("Waiting for mesh selection...")
        step1_logic.clear_reference_follicle()

    def on_select_mesh_click(self, *args):
        self.reset_step2_and_beyond()
        step1_logic.clear_reference_follicle()
        
        selected_objects = cmds.ls(selection=True, transforms=True)
        if not selected_objects:
            self.update_step1_status("No objects selected. Please select a mesh.", success=False)
            return

        mesh_transform = mesh_shape = None
        for obj in selected_objects:
            shapes = cmds.listRelatives(obj, shapes=True) or []
            for shape in shapes:
                if cmds.objectType(shape, isType="mesh"):
                    mesh_transform = obj
                    mesh_shape = shape
                    break
            if mesh_transform: break
        
        if not mesh_transform or not mesh_shape:
            self.update_step1_status("Selected object is not a mesh.", success=False)
            return
        
        # Check if mesh has UV coordinates
        if not step1_logic.has_uv_map(mesh_shape):
            self.update_step1_status("Selected mesh does not have UV coordinates. Please select a mesh with UVs.", success=False)
            return
        
        self.selected_mesh_transform = mesh_transform
        self.selected_mesh_shape = mesh_shape
        
        cmds.undoInfo(openChunk=True, chunkName="TextureRigger_SelectMesh")
        try:
            follicle_transform, follicle_shape, null_group = step1_logic.create_reference_follicle(
                mesh_transform, mesh_shape)
            
            if follicle_transform and null_group:
                self.update_step1_status(f"Mesh '{mesh_transform}' selected and reference follicle created.", success=True)
                cmds.button(self.create_locator_button, edit=True, enable=True)
            else:
                self.update_step1_status("Failed to create reference follicle.", success=False)
        finally:
            cmds.undoInfo(closeChunk=True)
    
    def on_create_locator_click(self, *args):
        if not self.selected_mesh_transform or not self.selected_mesh_shape:
            self.update_step1_status("No mesh selected. Please select a mesh first.", success=False)
            return

        current_prefix = cmds.textField(self.name_field, query=True, text=True)
        self.name_prefix = current_prefix
        
        if not current_prefix or current_prefix.isspace():
            self.update_step1_status("Prefix cannot be empty.", success=False)
            return

        # Check mirror settings
        is_mirror = cmds.checkBox(self.mirror_checkbox, query=True, value=True)
        
        if is_mirror:
            # Get side selection to apply prefix, but only create ONE locator
            selected_side_radio = cmds.radioCollection(self.mirror_side_radios, query=True, select=True)
            original_side = selected_side_radio.replace('mirror_', '') if selected_side_radio else 'L'
            
            original_prefix = f"{original_side}_{current_prefix}"
            
            if not self._is_prefix_unique(original_prefix):
                self.update_step1_status(f"Prefix '{original_prefix}' already exists.", success=False)
                return
            
            cmds.undoInfo(openChunk=True, chunkName="TextureRigger_CreateLocator")
            try:
                # Create only the original side locator; mirror will be generated in Step 2
                locator = step1_logic.create_locator_at_null_position(original_prefix)
                if not locator:
                    self.update_step1_status(f"Failed to create locator with prefix '{original_prefix}'.", success=False)
                    return
                
                self.locators_data[original_prefix] = locator
                self._update_locator_list_widget()
                self.update_step1_status(f"Added '{locator}'. Mirror will be created in Step 2 after positioning.", success=True)
                cmds.button(self.delete_locator_button, edit=True, enable=True)
            finally:
                cmds.undoInfo(closeChunk=True)
        else:
            # Non-mirror mode (original behavior)
            if not self._is_prefix_unique(current_prefix):
                self.update_step1_status(f"Prefix '{current_prefix}' already exists.", success=False)
                return
            
            cmds.undoInfo(openChunk=True, chunkName="TextureRigger_CreateLocator")
            try:
                locator = step1_logic.create_locator_at_null_position(current_prefix)
                
                if locator:
                    self.locators_data[current_prefix] = locator
                    self._update_locator_list_widget()
                    self.update_step1_status(f"Added locator '{locator}'.", success=True)
                    cmds.button(self.delete_locator_button, edit=True, enable=True)
                else:
                    self.update_step1_status(f"Failed to add locator with prefix '{current_prefix}'.", success=False)
                    return
            finally:
                cmds.undoInfo(closeChunk=True)
        
        # Auto-increment prefix
        match = re.match(r'^(.+?)_(\d+)$', current_prefix)
        if match:
            base = match.group(1)
            num = int(match.group(2))
            next_prefix = f"{base}_{num + 1}"
        else:
            next_prefix = f"{current_prefix}_1"
            
        cmds.textField(self.name_field, edit=True, text=next_prefix)
        self.name_prefix = next_prefix
        
        cmds.frameLayout(self.step2_frame, edit=True, enable=True)
        self.update_step2_status("Move locators. Create more or proceed to create follicles.")

    # --- Pre-connect Ordering Methods ---

    def _refresh_order_list(self):
        """Refreshes the ordering list widget from self.texture_order."""
        cmds.textScrollList(self.order_list_widget, edit=True, removeAll=True)
        for i, prefix in enumerate(self.texture_order):
            cmds.textScrollList(self.order_list_widget, edit=True, append=f"[{i}] {prefix}")

    def _on_order_move_up(self, *args):
        selected = cmds.textScrollList(self.order_list_widget, query=True, selectIndexedItem=True)
        if not selected or selected[0] <= 1:
            return
        idx = selected[0] - 1  # convert to 0-based
        self.texture_order[idx - 1], self.texture_order[idx] = self.texture_order[idx], self.texture_order[idx - 1]
        self._refresh_order_list()
        cmds.textScrollList(self.order_list_widget, edit=True, selectIndexedItem=[idx])  # keep selection (now moved up)

    def _on_order_move_down(self, *args):
        selected = cmds.textScrollList(self.order_list_widget, query=True, selectIndexedItem=True)
        if not selected:
            return
        idx = selected[0] - 1  # convert to 0-based
        if idx >= len(self.texture_order) - 1:
            return
        self.texture_order[idx], self.texture_order[idx + 1] = self.texture_order[idx + 1], self.texture_order[idx]
        self._refresh_order_list()
        cmds.textScrollList(self.order_list_widget, edit=True, selectIndexedItem=[idx + 2])  # keep selection (now moved down)

    # --- Post-connect Layer Ordering Methods ---

    def _enable_layer_ordering(self):
        """Finds layeredTexture nodes from connected textures and populates the layer list."""
        # Collect unique layeredTexture nodes
        lt_nodes = set()
        for prefix, tex_data in self.textures_data.items():
            lt = tex_data.get('layered_texture_node') or tex_data.get('layered_texture')
            if lt and cmds.objExists(lt):
                lt_nodes.add(lt)
        
        if lt_nodes:
            self.layer_texture_node = list(lt_nodes)[0]  # Use first found
            cmds.frameLayout(self.layer_frame, edit=True, enable=True, collapse=False)
            self._refresh_layer_list()

    def _refresh_layer_list(self):
        """Refreshes the layer list widget from the current layeredTexture node."""
        cmds.textScrollList(self.layer_list_widget, edit=True, removeAll=True)
        if not self.layer_texture_node or not cmds.objExists(self.layer_texture_node):
            return
        
        layers = step3_logic.get_layer_info(self.layer_texture_node)
        for layer in layers:
            label = f"[{layer['index']}] {layer['display_name']}"
            cmds.textScrollList(self.layer_list_widget, edit=True, append=label)

    def _on_layer_move_up(self, *args):
        selected = cmds.textScrollList(self.layer_list_widget, query=True, selectIndexedItem=True)
        if not selected or selected[0] <= 1:
            return
        ui_idx = selected[0]
        layers = step3_logic.get_layer_info(self.layer_texture_node)
        if ui_idx > len(layers) or ui_idx < 2:
            return
        idx_a = layers[ui_idx - 1]['index']
        idx_b = layers[ui_idx - 2]['index']
        step3_logic.swap_layers(self.layer_texture_node, idx_a, idx_b)
        self._refresh_layer_list()
        cmds.textScrollList(self.layer_list_widget, edit=True, selectIndexedItem=[ui_idx - 1])

    def _on_layer_move_down(self, *args):
        selected = cmds.textScrollList(self.layer_list_widget, query=True, selectIndexedItem=True)
        if not selected:
            return
        ui_idx = selected[0]
        layers = step3_logic.get_layer_info(self.layer_texture_node)
        if ui_idx >= len(layers):
            return
        idx_a = layers[ui_idx - 1]['index']
        idx_b = layers[ui_idx]['index']
        step3_logic.swap_layers(self.layer_texture_node, idx_a, idx_b)
        self._refresh_layer_list()
        cmds.textScrollList(self.layer_list_widget, edit=True, selectIndexedItem=[ui_idx + 1])

    # --- Existing Setup Edit Methods ---

    def _on_scan_setups_click(self, *args):
        """Scans the scene for existing TextureRigger setups."""
        self.found_setups = step3_logic.scan_existing_setups()
        
        # Clear and repopulate the menu
        menu_items = cmds.optionMenu(self.edit_setup_menu, query=True, itemListLong=True) or []
        for item in menu_items:
            cmds.deleteUI(item)
        
        if not self.found_setups:
            cmds.menuItem(label="(none found)", parent=self.edit_setup_menu)
            self.update_step1_status("No existing TextureRigger setups found in scene.", success=False)
        else:
            for setup in self.found_setups:
                mesh_name = setup['mesh'] or '(unknown mesh)'
                prefixes = ', '.join(setup['prefixes']) if setup['prefixes'] else '(no prefixes)'
                label = f"{setup['master_group']} | {mesh_name} | [{prefixes}]"
                cmds.menuItem(label=label, parent=self.edit_setup_menu)
            self.update_step1_status(f"Found {len(self.found_setups)} existing setup(s).", success=True)

    def _on_load_setup_click(self, *args):
        """Loads a selected existing setup for editing - populates tool state from scene."""
        if not self.found_setups:
            self.update_step1_status("No setups to load. Scan first.", success=False)
            return
        
        selected_idx = cmds.optionMenu(self.edit_setup_menu, query=True, select=True) - 1
        if selected_idx < 0 or selected_idx >= len(self.found_setups):
            self.update_step1_status("Invalid setup selection.", success=False)
            return
        
        setup = self.found_setups[selected_idx]
        master_grp = setup['master_group']
        mesh = setup['mesh']
        prefixes = setup['prefixes']
        
        if not mesh or not cmds.objExists(mesh):
            self.update_step1_status("Could not find mesh for this setup.", success=False)
            return
        
        # Reset current state
        self.reset_tool_state()
        
        # Set mesh
        self.selected_mesh_transform = mesh
        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh") or []
        if shapes:
            self.selected_mesh_shape = shapes[0]
        
        # Populate follicles_data from the RIG hierarchy
        self.follicles_data.clear()
        node_children = cmds.listRelatives(master_grp, children=True, type="transform", fullPath=True) or []
        for child in node_children:
            if child.split('|')[-1] == "RIG":
                rig_children = cmds.listRelatives(child, children=True, type="transform", fullPath=True) or []
                for rc in rig_children:
                    rc_short = rc.split('|')[-1]
                    if rc_short.endswith("_Texture_ctrl_grp"):
                        prefix = rc_short.replace("_Texture_ctrl_grp", "")
                        # Find follicle and control under this group
                        grp_children = cmds.listRelatives(rc, children=True, type="transform", fullPath=True) or []
                        follicle_trans = None
                        control = None
                        for gc in grp_children:
                            gc_short = gc.split('|')[-1]
                            # Check if it's a follicle
                            fol_shapes = cmds.listRelatives(gc, shapes=True, type="follicle") or []
                            if fol_shapes:
                                follicle_trans = gc
                                # Find control under follicle
                                fol_descendants = cmds.listRelatives(gc, allDescendents=True, type="transform") or []
                                for fd in fol_descendants:
                                    if "_Slide_ctrl" in fd:
                                        control = fd
                                        break
                        
                        if follicle_trans:
                            self.follicles_data[prefix] = {
                                'follicle': follicle_trans,
                                'control': control,
                                'locator_at_creation': None
                            }
                break
        
        # Update UI to reflect loaded state
        cmds.button(self.select_mesh_button, edit=True, enable=False)
        cmds.button(self.create_locator_button, edit=True, enable=False)
        self.update_step1_status(f"Loaded setup: {master_grp} | Mesh: {mesh}", success=True)
        
        # Enable Step 2 (disabled since follicles already exist)
        cmds.frameLayout(self.step2_frame, edit=True, enable=True)
        cmds.button(self.create_follicles_button, edit=True, enable=False)
        self.update_step2_status(f"Loaded {len(self.follicles_data)} existing follicle(s).", success=True)
        
        # Enable Step 3 for adding new textures
        if self.follicles_data:
            self._populate_texture_selection_ui()
            cmds.frameLayout(self.step3_frame, edit=True, enable=True)
            cmds.button(self.connect_all_textures_button, edit=True, enable=True)
            self.update_step3_status(f"Select new textures for {len(self.follicles_data)} prefix(es).")
        
        # Enable layer ordering if layeredTexture exists on the mesh material
        self._enable_layer_ordering_from_mesh(mesh)
        
        # Select the master group
        if cmds.objExists(master_grp):
            cmds.select(master_grp, replace=True)
        
        print(f"Loaded setup for editing: {setup}")

    def _enable_layer_ordering_from_mesh(self, mesh_transform):
        """Finds layeredTexture nodes connected to the mesh's material and enables the layer panel."""
        if not mesh_transform or not cmds.objExists(mesh_transform):
            return
        
        shapes = cmds.listRelatives(mesh_transform, shapes=True, type="mesh") or []
        if not shapes:
            return
        
        # Find shading groups
        sgs = cmds.listConnections(shapes[0], type="shadingEngine") or []
        for sg in sgs:
            # Find materials
            materials = cmds.listConnections(f"{sg}.surfaceShader", source=True, destination=False) or []
            for mat in materials:
                # Find layeredTexture connected to the material
                lt_nodes = cmds.listConnections(mat, type="layeredTexture", source=True, destination=False) or []
                if lt_nodes:
                    self.layer_texture_node = lt_nodes[0]
                    cmds.frameLayout(self.layer_frame, edit=True, enable=True, collapse=False)
                    self._refresh_layer_list()
                    return


def show_ui():
    tool_ui = TextureRiggerUI()
    tool_ui.create_ui()
    return tool_ui

if __name__ == "__main__":
    ui_instance = show_ui()

