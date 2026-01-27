"""
Step 1 view - Initial settings and clinical scales.

This module contains the view for the first step of the wizard where users
configure initial settings, stimulation parameters, and clinical scales.
"""

from typing import Callable, List, Tuple, Dict, Optional
import json
import os
from datetime import datetime

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QDoubleValidator, QFont, QIntValidator, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    PLACEHOLDERS,
    PRESET_BUTTONS,
    STIMULATION_LIMITS,
)
from ..ui import create_horizontal_line
from ..ui.clinical_scales_settings_dialog import ClinicalScalesSettingsDialog
from ..utils.resources import resource_path
from .base_view import BaseStepView
from ..models import ElectrodeCanvas
# Import configuration
from ..config_electrode_models import ContactState, ElectrodeModel, ELECTRODE_MODELS, MANUFACTURERS, get_all_manufacturers


class FileDropLineEdit(QLineEdit):
    def __init__(self, on_file_dropped: Callable[[str], None], parent=None):
        super().__init__(parent)
        self._on_file_dropped = on_file_dropped
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                local_path = urls[0].toLocalFile()
                if local_path:
                    self._on_file_dropped(local_path)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class Step1View(BaseStepView):
    """
    First step view for initial configuration.

    This view handles:
    - File selection for TSV output
    - Initial stimulation parameters
    - Clinical scales configuration
    - Initial notes
    """

    def __init__(self, logo_pixmap: QPixmap, parent_style):
        """
        Initialize Step 1 view.

        Args:
            logo_pixmap: Application logo
            parent_style: Parent widget style for icon access
        """
        super().__init__(logo_pixmap)
        self.parent_style = parent_style
        self.clinical_scales_rows: List[Tuple[QLineEdit, QLineEdit, QHBoxLayout]] = []
        self.current_file_mode = None  # Track file mode: 'existing', 'new', or None
        self.next_block_id: Optional[int] = None

        self.left_canvas = ElectrodeCanvas()
        self.right_canvas = ElectrodeCanvas()
        self.left_canvas.validation_callback = self._on_left_canvas_validation
        self.right_canvas.validation_callback = self._on_right_canvas_validation
        self._left_selection_valid = True
        self._right_selection_valid = True
        
        # Load custom presets
        self.clinical_presets = self._load_clinical_presets()
        
        self._setup_ui()

    def _on_left_canvas_validation(self, is_valid: bool, error_msg: str) -> None:
        self._left_selection_valid = is_valid
        self.update_configuration_display()

    def _on_right_canvas_validation(self, is_valid: bool, error_msg: str) -> None:
        self._right_selection_valid = is_valid
        self.update_configuration_display()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        # Header
        header = self.create_step1_header(
            "Clinical Programming Session Setup"
        )
        self.main_layout.addWidget(header)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: File + Initial settings
        left_layout = QVBoxLayout()
        upload_group = self._create_upload_tsv_group()
        settings_group = self._create_settings_group()
        left_layout.addWidget(upload_group)
        left_layout.addWidget(settings_group)
        #left_layout.addStretch(1)
        content_layout.addLayout(left_layout)

        # Right side: Clinical scales and notes
        right_layout = QVBoxLayout()
        clinical_group = self._create_clinical_scales_group()
        notes_group = self._create_notes_group()
        right_layout.addWidget(clinical_group)
        right_layout.addWidget(notes_group)
        #right_layout.addStretch(1) 
        content_layout.addLayout(right_layout)

        self.main_layout.addLayout(content_layout)

        self.next_button = QPushButton("Next")
        self.next_button.setIcon(self.parent_style.standardIcon(QStyle.SP_ArrowForward))
        self.next_button.setIconSize(QSize(16, 16))
        self.next_button.setMaximumWidth(120)

    def _create_settings_group(self) -> QGroupBox:
        """Create the initial settings group box."""
        gb_init = QGroupBox("Initial settings")
        gb_init.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        gb_init.setFont(QFont("Segoe UI", 12, QFont.Bold))
        gb_init.setStyleSheet(
            "QGroupBox { margin-top: 8pt; } "
            "QGroupBox::title { color: #ff8800; margin-left: 4pt; "
            "font-size: 16pt; font-weight: 600; }"
        )

        container_layout = QHBoxLayout()

        sidebar_layout = QVBoxLayout()

        model_group = QGroupBox("Electrode")
        model_layout = QVBoxLayout()

        manufacturer_label = QLabel("Manufacturer:")
        self.manufacturer_combo = QComboBox()
        self.manufacturer_combo.addItem("All Manufacturers")
        self.manufacturer_combo.addItems(get_all_manufacturers())
        self.manufacturer_combo.currentTextChanged.connect(self.on_manufacturer_changed)

        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.populate_models("All Manufacturers")
        self.model_combo.currentTextChanged.connect(self.on_model_changed)

        model_layout.addWidget(manufacturer_label)
        model_layout.addWidget(self.manufacturer_combo)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)

        group_row = QGroupBox("Group")
        group_row_layout = QHBoxLayout()
        self.group_combo = QComboBox()
        self.group_combo.addItems(["A", "B", "C", "D", "None"])
        self.group_combo.setCurrentText("None") 
        group_row_layout.addWidget(self.group_combo)
        group_row.setLayout(group_row_layout)

        freq_limits = STIMULATION_LIMITS["frequency"]
        amp_limits = STIMULATION_LIMITS["amplitude"]
        pw_limits = STIMULATION_LIMITS["pulse_width"]

        left_group = QGroupBox("Left")
        left_group_layout = QVBoxLayout()
        left_form = QFormLayout()
        left_form.setLabelAlignment(Qt.AlignRight)

        self.left_stim_freq_edit = QLineEdit()
        self.left_stim_freq_edit.setMaximumWidth(80)
        self.left_stim_freq_edit.setPlaceholderText(PLACEHOLDERS["frequency"])
        self.left_stim_freq_edit.setValidator(QIntValidator(freq_limits["min"], freq_limits["max"]))
        left_form.addRow(QLabel("Frequency:"), self.left_stim_freq_edit)

        self.left_amp_edit = QLineEdit()
        self.left_amp_edit.setMaximumWidth(80)
        self.left_amp_edit.setPlaceholderText(PLACEHOLDERS["amplitude"])
        self.left_amp_edit.setValidator(QDoubleValidator(amp_limits["min"], amp_limits["max"], amp_limits["decimals"]))
        left_form.addRow(QLabel("Amplitude:"), self.left_amp_edit)

        self.left_pw_edit = QLineEdit()
        self.left_pw_edit.setMaximumWidth(80)
        self.left_pw_edit.setPlaceholderText(PLACEHOLDERS["pulse_width"])
        self.left_pw_edit.setValidator(QIntValidator(pw_limits["min"], pw_limits["max"]))
        left_form.addRow(QLabel("Pulse width:"), self.left_pw_edit)

        self.left_config_text = QTextEdit()
        self.left_config_text.setReadOnly(True)
        self.left_config_text.setMinimumHeight(60)
        self.left_config_text.setMaximumHeight(90)
        self.left_config_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        left_group_layout.addLayout(left_form)
        left_group_layout.addWidget(self.left_config_text)
        left_group.setLayout(left_group_layout)

        right_group = QGroupBox("Right")
        right_group_layout = QVBoxLayout()
        right_form = QFormLayout()
        right_form.setLabelAlignment(Qt.AlignRight)

        self.right_stim_freq_edit = QLineEdit()
        self.right_stim_freq_edit.setMaximumWidth(80)
        self.right_stim_freq_edit.setPlaceholderText(PLACEHOLDERS["frequency"])
        self.right_stim_freq_edit.setValidator(QIntValidator(freq_limits["min"], freq_limits["max"]))
        right_form.addRow(QLabel("Frequency:"), self.right_stim_freq_edit)

        self.right_amp_edit = QLineEdit()
        self.right_amp_edit.setMaximumWidth(80)
        self.right_amp_edit.setPlaceholderText(PLACEHOLDERS["amplitude"])
        self.right_amp_edit.setValidator(QDoubleValidator(amp_limits["min"], amp_limits["max"], amp_limits["decimals"]))
        right_form.addRow(QLabel("Amplitude:"), self.right_amp_edit)

        self.right_pw_edit = QLineEdit()
        self.right_pw_edit.setMaximumWidth(80)
        self.right_pw_edit.setPlaceholderText(PLACEHOLDERS["pulse_width"])
        self.right_pw_edit.setValidator(QIntValidator(pw_limits["min"], pw_limits["max"]))
        right_form.addRow(QLabel("Pulse width:"), self.right_pw_edit)

        self.right_config_text = QTextEdit()
        self.right_config_text.setReadOnly(True)
        self.right_config_text.setMinimumHeight(60)
        self.right_config_text.setMaximumHeight(90)
        self.right_config_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        right_group_layout.addLayout(right_form)
        right_group_layout.addWidget(self.right_config_text)
        right_group.setLayout(right_group_layout)

        sidebar_layout.addWidget(model_group)
        sidebar_layout.addWidget(group_row)
        sidebar_layout.addWidget(left_group)
        sidebar_layout.addWidget(right_group)
        sidebar_layout.addStretch(1)

        electrodes_layout = QVBoxLayout()
        electrodes_row = QHBoxLayout()

        left_canvas_group = QGroupBox("Left electrode")
        left_canvas_layout = QVBoxLayout()
        left_canvas_layout.addWidget(self.left_canvas, 1)
        left_canvas_group.setLayout(left_canvas_layout)

        right_canvas_group = QGroupBox("Right electrode")
        right_canvas_layout = QVBoxLayout()
        right_canvas_layout.addWidget(self.right_canvas, 1)
        right_canvas_group.setLayout(right_canvas_layout)

        electrodes_row.addWidget(left_canvas_group, 1)
        electrodes_row.addWidget(right_canvas_group, 1)

        electrodes_layout.addLayout(electrodes_row)
        electrodes_layout.addLayout(self._create_electrode_legend_layout())

        container_layout.addLayout(sidebar_layout, 0)
        container_layout.addLayout(electrodes_layout, 1)

        layout = QVBoxLayout(gb_init)
        layout.addLayout(container_layout)

        if self.model_combo.count() > 0:
            self.on_model_changed(self.model_combo.currentText())

        return gb_init

    def _create_electrode_legend_layout(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch(1)

        def legend_item(color: str, text: str, border: str) -> QWidget:
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            swatch = QLabel()
            swatch.setFixedSize(16, 12)
            swatch.setStyleSheet(f"background-color: {color}; border: 1px solid {border};")
            label = QLabel(text)
            row.addWidget(swatch)
            row.addSpacing(6)
            row.addWidget(label)
            return w

        layout.addWidget(legend_item("#969696", "OFF", "#333333"))
        layout.addSpacing(18)
        layout.addWidget(legend_item("#ff6464", "Anodic (+)", "#c83232"))
        layout.addSpacing(18)
        layout.addWidget(legend_item("#6496ff", "Cathodic (-)", "#3264c8"))
        layout.addStretch(1)
        return layout

# functions for the electrode visualization
    def populate_models(self, manufacturer):
        """Populate model combo box based on selected manufacturer"""
        self.model_combo.blockSignals(True)  # Prevent triggering on_model_changed during population
        self.model_combo.clear()
        
        if manufacturer == "All Manufacturers":
            # Add all models sorted alphabetically
            all_models = sorted(ELECTRODE_MODELS.keys())
            self.model_combo.addItems(all_models)
        else:
            # Add models for specific manufacturer
            models = MANUFACTURERS.get(manufacturer, [])
            self.model_combo.addItems(models)
        
        self.model_combo.blockSignals(False)
        
    
    def on_manufacturer_changed(self, manufacturer):
        """Handle manufacturer selection change"""
        self.populate_models(manufacturer)
        if self.model_combo.count() > 0:
            self.on_model_changed(self.model_combo.currentText())
        
    def on_model_changed(self, model_name):
        """Handle model selection change"""
        if not model_name:
            return
            
        model = ELECTRODE_MODELS.get(model_name)
        if not model:
            return
            
        self.left_canvas.set_model(model)
        self.right_canvas.set_model(model)
        
        self.update_configuration_display()
        
    def update_configuration_display(self):
        """Update stimulation configuration display"""
        if not hasattr(self, "left_config_text") or not hasattr(self, "right_config_text"):
            return

        # Keep text edits empty by default
        self.left_config_text.setPlainText("")
        self.right_config_text.setPlainText("")
        
        self._apply_config_validation_styles()

    def _apply_config_validation_styles(self) -> None:
        if hasattr(self, "left_config_text"):
            if not self._left_selection_valid:
                self.left_config_text.setStyleSheet("border: 2px solid #cc0000; color: #cc0000;")
                self.left_config_text.setPlainText("Invalid configuration: violates selection rules")
            else:
                self.left_config_text.setStyleSheet("")
                self.left_config_text.setPlainText("")
                
        if hasattr(self, "right_config_text"):
            if not self._right_selection_valid:
                self.right_config_text.setStyleSheet("border: 2px solid #cc0000; color: #cc0000;")
                self.right_config_text.setPlainText("Invalid configuration: violates selection rules")
            else:
                self.right_config_text.setStyleSheet("")
                self.right_config_text.setPlainText("")

    def _format_configuration_html(self, canvas: ElectrodeCanvas) -> str:
        model = canvas.model
        if not model:
            return ""

        lines = []

        case_state_str = {
            ContactState.OFF: "OFF",
            ContactState.ANODIC: "Anodic (+)",
            ContactState.CATHODIC: "Cathodic (-)",
        }
        lines.append(f"<b>CASE (Ground):</b> {case_state_str[canvas.case_state]}")
        lines.append("")

        if canvas.contact_states:
            lines.append("<b>Active contacts:</b>")
            for contact_id in sorted(canvas.contact_states.keys()):
                contact_idx, seg_idx = contact_id
                state = canvas.contact_states[contact_id]
                state_str = "Anodic (+)" if state == ContactState.ANODIC else "Cathodic (-)"

                if model.is_directional:
                    segment_labels = ['a', 'b', 'c']
                    contact_name = f"C{contact_idx}{segment_labels[seg_idx]}"
                else:
                    contact_name = f"C{contact_idx}"

                lines.append(f"  • {contact_name}: {state_str}")
        else:
            lines.append("<i>No active contacts</i>")

        return "<br>".join(lines)

    def get_left_anode_text(self) -> str:
        return self._get_anode_cathode_texts(self.left_canvas)[0]

    def get_left_cathode_text(self) -> str:
        return self._get_anode_cathode_texts(self.left_canvas)[1]

    def get_right_anode_text(self) -> str:
        return self._get_anode_cathode_texts(self.right_canvas)[0]

    def get_right_cathode_text(self) -> str:
        return self._get_anode_cathode_texts(self.right_canvas)[1]

    def _get_anode_cathode_texts(self, canvas: ElectrodeCanvas) -> Tuple[str, str]:
        model = canvas.model
        if not model:
            return "", ""

        anode_items = []
        cathode_items = []

        if canvas.case_state == ContactState.ANODIC:
            anode_items.append("case")
        elif canvas.case_state == ContactState.CATHODIC:
            cathode_items.append("case")

        if model.is_directional:
            for contact_idx in range(model.num_contacts):
                seg_states = [canvas.contact_states.get((contact_idx, seg), ContactState.OFF) for seg in range(3)]
                if all(s == ContactState.ANODIC for s in seg_states):
                    anode_items.append(f"E{contact_idx}")
                    continue
                if all(s == ContactState.CATHODIC for s in seg_states):
                    cathode_items.append(f"E{contact_idx}")
                    continue

                seg_labels = ["a", "b", "c"]
                for seg, seg_state in enumerate(seg_states):
                    if seg_state == ContactState.ANODIC:
                        anode_items.append(f"E{contact_idx}{seg_labels[seg]}")
                    elif seg_state == ContactState.CATHODIC:
                        cathode_items.append(f"E{contact_idx}{seg_labels[seg]}")
        else:
            for contact_idx in range(model.num_contacts):
                state = canvas.contact_states.get((contact_idx, 0), ContactState.OFF)
                if state == ContactState.ANODIC:
                    anode_items.append(f"E{contact_idx}")
                elif state == ContactState.CATHODIC:
                    cathode_items.append(f"E{contact_idx}")

        return "_".join(anode_items), "_".join(cathode_items)

    def _apply_contact_text_to_canvas(self, canvas: ElectrodeCanvas, anode_text: str, cathode_text: str) -> None:
        model = canvas.model
        if not model:
            return

        canvas.contact_states.clear()
        canvas.case_state = ContactState.OFF

        def apply_tokens(text: str, state: ContactState) -> None:
            if not text:
                return
            for token in text.split("_"):
                token = token.strip()
                if not token:
                    continue

                if token == "case":
                    canvas.case_state = state
                    continue

                if token.startswith("E") and len(token) >= 2:
                    # Handle new E0, E1a format
                    try:
                        if token[-1].isalpha():
                            # Directional contact like E1a
                            idx = int(token[1:-1])
                            seg_char = token[-1].lower()
                            seg_map = {"a": 0, "b": 1, "c": 2}
                            if seg_char in seg_map:
                                canvas.contact_states[(idx, seg_map[seg_char])] = state
                        else:
                            # Ring contact like E0
                            idx = int(token[1:])
                            if model.is_directional:
                                for seg in range(3):
                                    canvas.contact_states[(idx, seg)] = state
                            else:
                                canvas.contact_states[(idx, 0)] = state
                    except Exception:
                        continue
                    continue
                
                # Legacy support for old format
                if token.endswith(" ring"):
                    idx_str = token.replace(" ring", "")
                    try:
                        idx = int(idx_str)
                    except Exception:
                        continue

                    if model.is_directional:
                        for seg in range(3):
                            canvas.contact_states[(idx, seg)] = state
                    else:
                        canvas.contact_states[(idx, 0)] = state
                    continue

                if model.is_directional and len(token) >= 2 and token[0].isdigit():
                    try:
                        idx = int(token[:-1])
                    except Exception:
                        continue
                    seg_char = token[-1].lower()
                    seg_map = {"a": 0, "b": 1, "c": 2}
                    if seg_char in seg_map:
                        canvas.contact_states[(idx, seg_map[seg_char])] = state

        apply_tokens(anode_text, ContactState.ANODIC)
        apply_tokens(cathode_text, ContactState.CATHODIC)

        canvas.update()
        
    def reset_all(self):
        """Reset all contacts and case"""
        self.left_canvas.contact_states.clear()
        self.left_canvas.case_state = ContactState.OFF
        self.right_canvas.contact_states.clear()
        self.right_canvas.case_state = ContactState.OFF
        self.left_canvas.update()
        self.right_canvas.update()
        self.update_configuration_display()
        
    def export_configuration(self):
        """Export current configuration to console"""
        left_model = self.left_canvas.model
        right_model = self.right_canvas.model
        if not left_model or not right_model:
            return

        print("\n" + "=" * 60)
        print("DBS STIMULATION CONFIGURATION")
        print("=" * 60)
        print(f"Model: {left_model.name}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        print(f"LEFT  Anode: {self.get_left_anode_text()} | Cathode: {self.get_left_cathode_text()}")
        print(f"RIGHT Anode: {self.get_right_anode_text()} | Cathode: {self.get_right_cathode_text()}")
        print("=" * 60 + "\n")

    def _create_upload_tsv_group(self) -> QGroupBox:
        gb_upload = QGroupBox("Upload TSV file")
        gb_upload.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        gb_upload.setFont(QFont("Segoe UI", 14, QFont.Bold))
        gb_upload.setStyleSheet(
            "QGroupBox { margin-top: 8pt; } "
            "QGroupBox::title { color: #ff8800; margin-left: 4pt; "
            "font-size: 16pt; font-weight: 600; }"
        )

        layout = QHBoxLayout(gb_upload)

        self.file_path_edit = FileDropLineEdit(self._on_file_dropped)
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setClearButtonEnabled(True)
        self.file_path_edit.textChanged.connect(self._on_file_path_changed)
        self.file_path_edit.setToolTip("Drop a .tsv here, or use the buttons")

        open_button = QPushButton()
        open_button.setText("Open")
        open_button.setMaximumWidth(60)
        #open_button.setIcon(self.parent_style.standardIcon(QStyle.SP_DialogOpenButton))
        open_button.setToolTip("Open existing file")
        open_button.clicked.connect(self.open_existing_file)

        create_button = QPushButton()
        create_button.setText("New")
        create_button.setMaximumWidth(60)
        #create_button.setIcon(self.parent_style.standardIcon(QStyle.SP_FileIcon))
        create_button.setToolTip("Create new file")
        create_button.clicked.connect(self.create_new_file)

        layout.addWidget(self.file_path_edit, 1)
        layout.addWidget(open_button)
        layout.addWidget(create_button)

        return gb_upload

    def _create_clinical_scales_group(self) -> QGroupBox:
        """Create the clinical scales group box."""
        gb_clinical = QGroupBox("Clinical scales")
        gb_clinical.setStyleSheet(
            "QGroupBox::title { color: #ff8800; font-size: 11pt; font-weight: 600; }"
        )
        gb_clinical.setFont(QFont("Segoe UI", 11, QFont.Bold))
        gb_clinical.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(gb_clinical)

        # Preset buttons
        preset_row = QHBoxLayout()
        self.preset_buttons = []
        preset_row.addStretch(1)
        
        # Settings button
        settings_btn = QPushButton('⚙️')
        settings_btn.setObjectName("settings_clincal_scales")
        settings_btn.setToolTip("Settings clinical scales")
        settings_btn.clicked.connect(self._open_clinical_scales_settings)
        preset_row.addWidget(settings_btn)
        
        layout.addLayout(preset_row)
        
        # Store the layout for later updates
        self.preset_row_layout = preset_row

        # Build buttons from current presets (JSON) once the row exists
        self._refresh_preset_buttons()

        # Container for dynamic scale rows - expands to show all rows
        scroll_content = QWidget()
        scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  
        self.clinical_scales_container = QVBoxLayout(scroll_content)
        self.clinical_scales_container.setContentsMargins(0, 0, 0, 0)

        # Scrollable area - will only scroll when user resizes window smaller
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        scroll_area.setWidget(scroll_content)

        layout.addWidget(scroll_area)

        return gb_clinical

    def _create_notes_group(self) -> QGroupBox:
        """Create the initial notes group box."""
        gb_notes = QGroupBox("Initial notes")
        gb_notes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding) 
        gb_notes.setFont(QFont("Segoe UI", 11, QFont.Bold))
        gb_notes.setStyleSheet(
            "QGroupBox::title { color: #ff8800; font-size: 11pt; font-weight: 600; }"
        )

        layout = QHBoxLayout(gb_notes)
        self.notes_edit = QTextEdit()
        self.notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        self.notes_edit.setMinimumHeight(100)  
        layout.addWidget(self.notes_edit)

        return gb_notes

    def _on_file_path_changed(self, text: str) -> None:
        if not text.strip():
            self.current_file_mode = None
            self.next_block_id = None

    def _on_file_dropped(self, file_path: str) -> None:
        if file_path:
            self._load_existing_file(file_path)

    def open_existing_file(self) -> None:
        current_path = self.file_path_edit.text().strip()
        start_dir = os.path.dirname(current_path) if current_path else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Existing TSV File",
            start_dir,
            "TSV Files (*.tsv);;All Files (*)",
        )
        if file_path:
            self._load_existing_file(file_path)

    def _load_existing_file(self, file_path: str) -> None:
        import csv

        block0_row = None
        block0_scales: List[Tuple[str, str]] = []
        max_block = -1

        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    try:
                        bid_raw = row.get("block_id", "")
                        if bid_raw is None or bid_raw == "":
                            continue
                        bid = int(float(bid_raw))
                    except Exception:
                        continue

                    max_block = max(max_block, bid)

                    if bid == 0:
                        if block0_row is None:
                            block0_row = row
                        sname = row.get("scale_name", None)
                        sval = row.get("scale_value", None)
                        if sname not in (None, ""):
                            block0_scales.append((str(sname), "" if sval is None else str(sval)))

            self.file_path_edit.setText(file_path)
            self.current_file_mode = "existing"
            self.next_block_id = max_block + 1

            if block0_row is not None:
                group_val = block0_row.get("group", None)
                if group_val not in (None, "") and hasattr(self, "group_combo"):
                    try:
                        self.group_combo.setCurrentText(str(group_val))
                    except Exception:
                        pass

                if block0_row.get("left_stim_freq") not in (None, ""):
                    self.left_stim_freq_edit.setText(str(block0_row.get("left_stim_freq")))
                if block0_row.get("right_stim_freq") not in (None, ""):
                    self.right_stim_freq_edit.setText(str(block0_row.get("right_stim_freq")))

                left_anode = "" if block0_row.get("left_anode") in (None, "") else str(block0_row.get("left_anode"))
                left_cathode = "" if block0_row.get("left_cathode") in (None, "") else str(block0_row.get("left_cathode"))
                right_anode = "" if block0_row.get("right_anode") in (None, "") else str(block0_row.get("right_anode"))
                right_cathode = "" if block0_row.get("right_cathode") in (None, "") else str(block0_row.get("right_cathode"))

                self._apply_contact_text_to_canvas(self.left_canvas, left_anode, left_cathode)
                self._apply_contact_text_to_canvas(self.right_canvas, right_anode, right_cathode)

                if block0_row.get("left_amplitude") not in (None, ""):
                    self.left_amp_edit.setText(str(block0_row.get("left_amplitude")))
                if block0_row.get("right_amplitude") not in (None, ""):
                    self.right_amp_edit.setText(str(block0_row.get("right_amplitude")))
                if block0_row.get("left_pulse_width") not in (None, ""):
                    self.left_pw_edit.setText(str(block0_row.get("left_pulse_width")))
                if block0_row.get("right_pulse_width") not in (None, ""):
                    self.right_pw_edit.setText(str(block0_row.get("right_pulse_width")))

                if block0_row.get("notes") not in (None, ""):
                    self.notes_edit.setText(str(block0_row.get("notes")))

            self.update_configuration_display()

            if block0_scales and hasattr(self, "on_add_callback") and hasattr(self, "on_remove_callback"):
                for _, _, row_layout in self.clinical_scales_rows:
                    while row_layout.count():
                        item = row_layout.takeAt(0)
                        widget = item.widget()
                        if widget is not None:
                            widget.deleteLater()
                    self.clinical_scales_container.removeItem(row_layout)
                self.clinical_scales_rows = []

                while self.clinical_scales_container.count():
                    item = self.clinical_scales_container.takeAt(0)
                    if item.spacerItem():
                        continue
                    if item.widget():
                        item.widget().deleteLater()

                for scale_name, scale_value in block0_scales:
                    self._add_clinical_scale_row(
                        scale_name,
                        with_minus=True,
                        on_remove=self.on_remove_callback,
                    )
                    try:
                        self.clinical_scales_rows[-1][1].setText(scale_value)
                    except Exception:
                        pass

                self._add_clinical_scale_row("", with_plus=True, on_add=self.on_add_callback)
                self.clinical_scales_container.addStretch()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load file: {str(e)}")
    
    def create_new_file(self) -> None:
        """Create new file with BIDS-style naming."""
        from datetime import datetime

        current_path = self.file_path_edit.text().strip()
        start_dir = os.path.dirname(current_path) if current_path else ""

        now = datetime.now()
        subject_id = "sub-01"
        session_id = f"ses-{now.strftime('%Y%m%d')}"
        task = "task-percept"
        run = "run-01"
        default_name = f"{subject_id}_{session_id}_{task}_{run}_events.tsv"

        default_path = os.path.join(start_dir, default_name) if start_dir else default_name

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New TSV File",
            default_path,
            "TSV Files (*.tsv);;All Files (*)",
        )

        if file_path:
            if not file_path.endswith(".tsv"):
                file_path += ".tsv"
            self.file_path_edit.setText(file_path)
            self.current_file_mode = "new"
            self.next_block_id = None

    def get_preset_button(self, preset_name: str) -> QPushButton:
        """Get a preset button by name."""
        return self.findChild(QPushButton, f"preset_{preset_name}")

    def update_clinical_scales(
        self, preset_scales: List[str], on_add_callback: Callable, on_remove_callback: Callable
    ) -> None:
        """
        Update the clinical scales UI with the given scales.

        Args:
            preset_scales: List of scale names to display
            on_add_callback: Callback for add button
            on_remove_callback: Callback for remove button
        """
        # Store callbacks for preset buttons
        self.on_add_callback = on_add_callback
        self.on_remove_callback = on_remove_callback
        
        # Clear existing rows
        for _, _, row_layout in self.clinical_scales_rows:
            while row_layout.count():
                item = row_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self.clinical_scales_container.removeItem(row_layout)
        self.clinical_scales_rows = []

        # Add preset scales
        for name in preset_scales:
            self._add_clinical_scale_row(name, with_minus=True, on_remove=on_remove_callback)

        # Add empty row with add button
        self._add_clinical_scale_row("", with_plus=True, on_add=on_add_callback)
        
        # Add stretch at the bottom to push content up
        self.clinical_scales_container.addStretch()
        
        # Store callbacks for preset buttons
        self.on_add_callback = on_add_callback
        self.on_remove_callback = on_remove_callback
        
        # Connect preset buttons to their respective scales (only now that callbacks are available)
        self._connect_preset_buttons()

    def _connect_preset_buttons(self):
        """Connect all preset buttons to their respective scales."""
        for btn in self.preset_buttons:
            # Disconnect any existing connections
            try:
                btn.clicked.disconnect()
            except:
                pass
            
            # Get the preset name from object name
            preset_name = btn.objectName().replace("preset_", "")
            
            # Get the scales for this preset from clinical_presets
            if preset_name in self.clinical_presets:
                preset_scales = self.clinical_presets[preset_name]
                
                if preset_scales and isinstance(preset_scales, list):
                    # Create a proper closure using a function
                    def create_preset_handler(scales):
                        return lambda: self._apply_preset_scales(scales)
                    
                    btn.clicked.connect(create_preset_handler(preset_scales))
            else:
                # Still connect with empty list as fallback
                btn.clicked.connect(lambda: self._apply_preset_scales([]))
                
    def _apply_preset_scales(self, scales: List[str]):
        """Apply a preset's scales to the clinical scales section."""
        if not isinstance(scales, list):
            return
            
        if hasattr(self, 'on_add_callback') and hasattr(self, 'on_remove_callback'):
            # Clear existing scales first
            for _, _, row_layout in self.clinical_scales_rows:
                while row_layout.count():
                    item = row_layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
                self.clinical_scales_container.removeItem(row_layout)
            self.clinical_scales_rows = []
            
            # Also remove any stretches from container
            while self.clinical_scales_container.count():
                item = self.clinical_scales_container.takeAt(0)
                if item.spacerItem():
                    # Just remove the stretch, no widget to delete
                    continue
                elif item.widget():
                    item.widget().deleteLater()
                else:
                    # Remove layout items
                    continue
            
            # Add the preset scales
            for scale_name in scales:
                self._add_clinical_scale_row(scale_name, with_minus=True, on_remove=self.on_remove_callback)
            
            # Add empty row with add button
            self._add_clinical_scale_row("", with_plus=True, on_add=self.on_add_callback)
            
            # Add stretch at the very bottom 
            self.clinical_scales_container.addStretch()

    def _add_clinical_scale_row(
        self,
        name: str = "",
        with_plus: bool = False,
        with_minus: bool = False,
        on_add: Callable = None,
        on_remove: Callable = None,
    ) -> None:
        """Add a single clinical scale row."""
        row = QHBoxLayout()

        name_edit = QLineEdit()
        name_edit.setPlaceholderText(PLACEHOLDERS["scale_name"])
        name_edit.setMaximumWidth(80)
        name_edit.setText(name)

        score_edit = QLineEdit()
        score_edit.setPlaceholderText(PLACEHOLDERS["scale_score"])
        score_edit.setMaximumWidth(50)

        if with_plus:
            btn = QPushButton("+")
            btn.setToolTip("Add clinical scale")
            btn.setMaximumWidth(24)
            if on_add:
                btn.clicked.connect(on_add)
        elif with_minus:
            btn = QPushButton("-")
            btn.setToolTip("Remove clinical scale")
            btn.setMaximumWidth(24)
            if on_remove:
                btn.clicked.connect(lambda: on_remove(row))
                
        # Add widgets to row
        row.addWidget(QLabel("Name:"))
        row.addWidget(name_edit)
        row.addSpacing(5)
        row.addWidget(QLabel("Score:"))
        row.addWidget(score_edit)
        row.addWidget(btn)
        row.addStretch(1)

        # Add row to container and track it
        self.clinical_scales_container.addLayout(row)
        self.clinical_scales_rows.append((name_edit, score_edit, row))

    def _load_clinical_presets(self) -> Dict[str, List[str]]:
        """Load clinical presets from config file."""
        presets_file = resource_path("config/clinical_presets.json")
        
        if os.path.exists(presets_file):
            try:
                with open(presets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading clinical presets: {e}")
                return {}
        else:
            # Create default presets if file doesn't exist
            return {k: list(v) for k, v in PRESET_BUTTONS.items()}

    def _open_clinical_scales_settings(self):
        """Open the clinical scales settings dialog."""
        dialog = ClinicalScalesSettingsDialog(self.clinical_presets, self, PRESET_BUTTONS)
        dialog.presets_changed.connect(self._on_presets_changed)
        dialog.exec_()

    def _on_presets_changed(self, new_presets: Dict[str, List[str]]):
        """Handle presets change from settings dialog."""
        old_presets = self.clinical_presets
        self.clinical_presets = new_presets
        
        # Save all presets to file immediately
        try:
            presets_file = resource_path("config/clinical_presets.json")
            os.makedirs(os.path.dirname(presets_file), exist_ok=True)
            
            with open(presets_file, 'w', encoding='utf-8') as f:
                json.dump(new_presets, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving presets: {e}")
        
        # Check if any currently displayed preset was modified or deleted
        current_scales = []
        for name_edit, _, _ in self.clinical_scales_rows:
            scale_name = name_edit.text().strip()
            if scale_name:
                current_scales.append(scale_name)
        
        # Find which preset contains current scales
        current_preset = None
        if len(current_scales) > 0:
            for preset_name, preset_scales in old_presets.items():
                if all(scale in preset_scales for scale in current_scales):
                    current_preset = preset_name
                    break
        
        # Refresh preset buttons
        self._refresh_preset_buttons()
        
        # Reconnect buttons with new scales
        if hasattr(self, 'on_add_callback') and hasattr(self, 'on_remove_callback'):
            self._connect_preset_buttons()
            
            # If we found a current preset, check if it was modified
            if current_preset:
                if current_preset in new_presets:
                    # Check if scales actually changed
                    old_scales = old_presets[current_preset]
                    new_scales = new_presets[current_preset]
                    
                    if old_scales != new_scales:
                        # Preset was modified - apply new scales
                        self._apply_preset_scales(new_scales)
                else:
                    # Preset was deleted - clear scales
                    self._apply_preset_scales([])

    def _refresh_preset_buttons(self):
        """Refresh preset buttons with new presets."""
        # Clear existing preset buttons
        for btn in self.preset_buttons:
            btn.setParent(None)
            btn.deleteLater()
        self.preset_buttons.clear()
        
        # Use the stored preset row layout
        preset_row = self.preset_row_layout
        
        if preset_row:
            # Remove all existing widgets from preset row (except stretch and settings button)
            widgets_to_remove = []
            for i in range(preset_row.count()):
                item = preset_row.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if widget and widget.objectName() != "settings_clincal_scales":
                        widgets_to_remove.append(widget)
            
            for widget in widgets_to_remove:
                preset_row.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
                    
            # Find the settings button and its position
            settings_btn = None
            settings_index = -1
            for i in range(preset_row.count()):
                item = preset_row.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if widget and widget.objectName() == "settings_clincal_scales":
                        settings_btn = widget
                        settings_index = i
                        break
            
            if settings_btn is None:
                return

            # Ensure exactly one stretch before the settings button
            stretch_index = settings_index - 1
            if stretch_index < 0 or not (preset_row.itemAt(stretch_index) and preset_row.itemAt(stretch_index).spacerItem()):
                preset_row.insertStretch(settings_index, 1)
                settings_index += 1
                stretch_index = settings_index - 1

            # # Remove any other stretches before the settings button (keep only the one right before it)
            # for i in range(stretch_index):
            #     item = preset_row.itemAt(i)
            #     if item and item.spacerItem():
            #         preset_row.takeAt(i)
            #         break

            # Insert new preset buttons before the stretch
            insert_index = stretch_index

            # Prefer showing defaults first IF they exist in the current presets
            ordered_names: List[str] = []
            for name in PRESET_BUTTONS:
                if name in self.clinical_presets:
                    ordered_names.append(name)
            for name in self.clinical_presets.keys():
                if name not in ordered_names:
                    ordered_names.append(name)

            for preset_name in ordered_names:
                btn = QPushButton(preset_name)
                btn.setObjectName(f"preset_{preset_name}")
                self.preset_buttons.append(btn)
                preset_row.insertWidget(insert_index, btn)
                insert_index += 1
                settings_index += 1
                stretch_index += 1
            
            # Reconnect all preset buttons after refresh
            if hasattr(self, 'on_add_callback') and hasattr(self, 'on_remove_callback'):
                self._connect_preset_buttons()
