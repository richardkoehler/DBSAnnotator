"""
Step 3 view - Active session recording.

This module contains the view for the third step where users actively record
session data including stimulation parameters and scale values.
"""

from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QFont, QIntValidator, QPixmap
from PyQt5.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from ..config import (
    PLACEHOLDERS,
    SESSION_SCALE_LIMITS,
    STIMULATION_LIMITS,
)
from ..ui import IncrementWidget, create_horizontal_line
from .base_view import BaseStepView
from ..models import ElectrodeCanvas
from ..config_electrode_models import ContactState, StimulationRule


class Step3View(BaseStepView):
    """
    Third step view for active session recording.

    This view handles:
    - Real-time stimulation parameter adjustment
    - Session scale value recording
    - Session notes
    - Data insertion and session closing
    """

    def __init__(self, parent_style):
        """
        Initialize Step 3 view.

        Args:
            parent_style: Parent widget style for icon access
        """
        super().__init__()
        self.parent_style = parent_style
        self.session_scale_value_edits: List[Tuple[str, QLineEdit]] = []
        self.step3_session_scales_form: QFormLayout = None

        self.left_canvas = ElectrodeCanvas()
        self.right_canvas = ElectrodeCanvas()
        self.left_canvas.validation_callback = self._on_left_canvas_validation
        self.right_canvas.validation_callback = self._on_right_canvas_validation

        self._current_model = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(12, 8, 12, 8)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: Stimulation params
        left_layout = QVBoxLayout()
        params_group = self._create_stimulation_params_group()
        left_layout.addWidget(params_group)
        left_layout.addStretch(1)
        content_layout.addLayout(left_layout)

        # Center: Electrodes
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
        content_layout.addLayout(electrodes_layout, 1)

        # Right side: Scales and notes
        right_layout = QVBoxLayout()
        scales_group = self._create_session_scales_group()
        right_layout.addWidget(scales_group)
        right_layout.addWidget(create_horizontal_line())
        notes_group = self._create_notes_group()
        right_layout.addWidget(notes_group)
        content_layout.addLayout(right_layout)

        self.main_layout.addLayout(content_layout)
        self.main_layout.addStretch(1)

        self.insert_button = QPushButton("Insert")
        self.insert_button.setIcon(
            self.parent_style.standardIcon(QStyle.SP_DialogApplyButton)
        )
        self.insert_button.setMaximumWidth(120)

        self.close_button = QPushButton("Close session")
        self.close_button.setIcon(
            self.parent_style.standardIcon(QStyle.SP_DialogCloseButton)
        )
        self.close_button.setFixedWidth(150)

        self.export_button = QPushButton("Export Report")
        self.export_button.setIcon(
            self.parent_style.standardIcon(QStyle.SP_DialogSaveButton)
        )
        self.export_button.setFixedWidth(150)
        
        # Create dropdown menu for export options
        self.export_menu = QMenu(self)
        
        # Excel export action
        self.export_excel_action = self.export_menu.addAction("📊 Excel Report")
        self.export_excel_action.setToolTip("Export to Excel (.xlsx) with summary statistics")
        
        # Word export action  
        self.export_word_action = self.export_menu.addAction("📄 Word Report")
        self.export_word_action.setToolTip("Export to Word (.docx) document")
        
        # PDF export action
        self.export_pdf_action = self.export_menu.addAction("📋 PDF Report")
        self.export_pdf_action.setToolTip("Export to PDF document")
        
        # Set menu to button
        self.export_button.setMenu(self.export_menu)

    def _create_stimulation_params_group(self) -> QWidget:
        """Create the stimulation parameters container."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        # Group selector
        self.group_combo = QComboBox()
        self.group_combo.addItems(["A", "B", "C", "D"])
        self.group_combo.setCurrentIndex(0)
        form.addRow(QLabel("Group:"), self.group_combo)

        freq_limits = STIMULATION_LIMITS["frequency"]
        amp_limits = STIMULATION_LIMITS["amplitude"]
        pw_limits = STIMULATION_LIMITS["pulse_width"]

        # Left electrode section
        form.addRow(QLabel(""), QLabel(""))  # Empty row for spacing
        left_electrode_label = QLabel("Left electrode")
        left_electrode_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        form.addRow(left_electrode_label, QLabel(""))

        # Left stimulation frequency
        self.session_left_stim_freq_edit = QLineEdit()
        self.session_left_stim_freq_edit.setPlaceholderText(PLACEHOLDERS["frequency"])
        self.session_left_stim_freq_edit.setFixedWidth(100)
        self.session_left_stim_freq_edit.setValidator(
            QIntValidator(freq_limits["min"], freq_limits["max"])
        )
        left_freq_widget = IncrementWidget(
            self.session_left_stim_freq_edit,
            step1=freq_limits["step"],
            decimals=0,
            min_value=freq_limits["min"],
            max_value=freq_limits["max"],
        )
        form.addRow(QLabel("Stimulation frequency:"), left_freq_widget)

        self.left_config_text = QTextEdit()
        self.left_config_text.setReadOnly(True)
        self.left_config_text.setMaximumHeight(120)
        form.addRow(self.left_config_text)

        # Left amplitude
        self.session_left_amp_edit = QLineEdit()
        self.session_left_amp_edit.setPlaceholderText(PLACEHOLDERS["amplitude"])
        self.session_left_amp_edit.setFixedWidth(100)
        self.session_left_amp_edit.setValidator(
            QDoubleValidator(amp_limits["min"], amp_limits["max"], amp_limits["decimals"])
        )
        left_amp_widget = IncrementWidget(
            self.session_left_amp_edit,
            step1=amp_limits["step1"],
            step2=amp_limits["step2"],
            decimals=1,
            min_value=amp_limits["min"],
            max_value=amp_limits["max"],
        )
        form.addRow(QLabel("Amplitude:"), left_amp_widget)

        # Left pulse width
        self.session_left_pw_edit = QLineEdit()
        self.session_left_pw_edit.setPlaceholderText(PLACEHOLDERS["pulse_width"])
        self.session_left_pw_edit.setFixedWidth(100)
        self.session_left_pw_edit.setValidator(
            QIntValidator(pw_limits["min"], pw_limits["max"])
        )
        left_pw_widget = IncrementWidget(
            self.session_left_pw_edit,
            step1=pw_limits["step"],
            decimals=0,
            min_value=pw_limits["min"],
            max_value=pw_limits["max"],
        )
        form.addRow(QLabel("Pulse width:"), left_pw_widget)
        form.addWidget(create_horizontal_line())

        # Right electrode section
        form.addRow(QLabel(""), QLabel(""))  # Empty row for spacing
        right_electrode_label = QLabel("Right electrode")
        right_electrode_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        form.addRow(right_electrode_label, QLabel(""))

        # Right stimulation frequency
        self.session_right_stim_freq_edit = QLineEdit()
        self.session_right_stim_freq_edit.setPlaceholderText(PLACEHOLDERS["frequency"])
        self.session_right_stim_freq_edit.setFixedWidth(100)
        self.session_right_stim_freq_edit.setValidator(
            QIntValidator(freq_limits["min"], freq_limits["max"])
        )
        right_freq_widget = IncrementWidget(
            self.session_right_stim_freq_edit,
            step1=freq_limits["step"],
            decimals=0,
            min_value=freq_limits["min"],
            max_value=freq_limits["max"],
        )
        form.addRow(QLabel("Stimulation frequency:"), right_freq_widget)

        self.right_config_text = QTextEdit()
        self.right_config_text.setReadOnly(True)
        self.right_config_text.setMaximumHeight(120)
        form.addRow(self.right_config_text)

        # Right amplitude
        self.session_right_amp_edit = QLineEdit()
        self.session_right_amp_edit.setPlaceholderText(PLACEHOLDERS["amplitude"])
        self.session_right_amp_edit.setFixedWidth(100)
        self.session_right_amp_edit.setValidator(
            QDoubleValidator(amp_limits["min"], amp_limits["max"], amp_limits["decimals"])
        )
        right_amp_widget = IncrementWidget(
            self.session_right_amp_edit,
            step1=amp_limits["step1"],
            step2=amp_limits["step2"],
            decimals=1,
            min_value=amp_limits["min"],
            max_value=amp_limits["max"],
        )
        form.addRow(QLabel("Amplitude:"), right_amp_widget)

        # Right pulse width
        self.session_right_pw_edit = QLineEdit()
        self.session_right_pw_edit.setPlaceholderText(PLACEHOLDERS["pulse_width"])
        self.session_right_pw_edit.setFixedWidth(100)
        self.session_right_pw_edit.setValidator(
            QIntValidator(pw_limits["min"], pw_limits["max"])
        )
        right_pw_widget = IncrementWidget(
            self.session_right_pw_edit,
            step1=pw_limits["step"],
            decimals=0,
            min_value=pw_limits["min"],
            max_value=pw_limits["max"],
        )
        form.addRow(QLabel("Pulse width:"), right_pw_widget)

        container_layout.addLayout(form)
        return container

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

    def _on_left_canvas_validation(self, is_valid: bool, error_msg: str) -> None:
        self.update_configuration_display()

    def _on_right_canvas_validation(self, is_valid: bool, error_msg: str) -> None:
        self.update_configuration_display()

    def set_electrode_model(self, model) -> None:
        self._current_model = model
        self.left_canvas.set_model(model)
        self.right_canvas.set_model(model)
        self.update_configuration_display()

    def update_configuration_display(self) -> None:
        if not hasattr(self, "left_config_text") or not hasattr(self, "right_config_text"):
            return
        self.left_config_text.setHtml(self._format_configuration_html(self.left_canvas))
        self.right_config_text.setHtml(self._format_configuration_html(self.right_canvas))

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
                    anode_items.append(f"{contact_idx} ring")
                    continue
                if all(s == ContactState.CATHODIC for s in seg_states):
                    cathode_items.append(f"{contact_idx} ring")
                    continue

                seg_labels = ["a", "b", "c"]
                for seg, seg_state in enumerate(seg_states):
                    if seg_state == ContactState.ANODIC:
                        anode_items.append(f"{contact_idx}{seg_labels[seg]}")
                    elif seg_state == ContactState.CATHODIC:
                        cathode_items.append(f"{contact_idx}{seg_labels[seg]}")
        else:
            for contact_idx in range(model.num_contacts):
                state = canvas.contact_states.get((contact_idx, 0), ContactState.OFF)
                if state == ContactState.ANODIC:
                    anode_items.append(f"{contact_idx} ring")
                elif state == ContactState.CATHODIC:
                    cathode_items.append(f"{contact_idx} ring")

        return "_".join(anode_items), "_".join(cathode_items)

    def _create_session_scales_group(self) -> QGroupBox:
        """Create the session scales group box."""
        gb_session = QGroupBox("Session scales")
        gb_session.setStyleSheet(
            "QGroupBox::title { color: #ff8800; font-size: 15pt; font-weight: 600; }"
        )
        gb_session.setFont(QFont("Segoe UI", 12, QFont.Bold))

        self.step3_session_scales_form = QFormLayout(gb_session)
        self.step3_session_scales_form.setLabelAlignment(Qt.AlignRight)
        self.step3_session_scales_form.setFormAlignment(Qt.AlignTop)
        self.step3_session_scales_form.setHorizontalSpacing(18)
        self.step3_session_scales_form.setVerticalSpacing(10)

        return gb_session

    def _create_notes_group(self) -> QGroupBox:
        """Create the session notes group box."""
        gb_notes = QGroupBox("Session notes")
        gb_notes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        gb_notes.setStyleSheet(
            "QGroupBox::title { color: #ff8800; font-size: 11pt; font-weight: 600; }"
        )
        gb_notes.setFont(QFont("Segoe UI", 10, QFont.Bold))

        layout = QHBoxLayout(gb_notes)
        self.session_notes_edit = QTextEdit()
        self.session_notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.session_notes_edit.setMinimumHeight(40)
        layout.addWidget(self.session_notes_edit)

        return gb_notes

    def update_session_scales(self, scale_names: List[str]) -> None:
        """
        Update the session scales form with the given scale names.

        Args:
            scale_names: List of scale names to display
        """
        # Clear existing form
        while self.step3_session_scales_form.rowCount():
            self.step3_session_scales_form.removeRow(0)

        self.session_scale_value_edits = []

        # Add scale inputs
        limits = SESSION_SCALE_LIMITS
        for name in scale_names:
            value_edit = QLineEdit()
            value_edit.setPlaceholderText(PLACEHOLDERS["scale_value"])
            value_edit.setFixedWidth(75)

            widget = IncrementWidget(
                value_edit,
                step1=limits["step1"],
                step2=limits["step2"],
                decimals=limits["decimals"],
                min_value=limits["min"],
                max_value=limits["max"],
            )

            self.step3_session_scales_form.addRow(QLabel(name + ":"), widget)
            self.session_scale_value_edits.append((name, value_edit))

    def set_initial_stimulation_params(
        self,
        left_frequency: str,
        left_cathode: str,
        left_anode: str,
        left_amp: str,
        left_pw: str,
        right_frequency: str,
        right_cathode: str,
        right_anode: str,
        right_amp: str,
        right_pw: str,
        group: str,
    ) -> None:
        """
        Set initial stimulation parameters from previous step.

        Args:
            left_frequency: Left stimulation frequency
            left_cathode: Left electrode cathode configuration
            left_anode: Left electrode anode configuration
            left_amp: Left amplitude
            left_pw: Left pulse width
            right_frequency: Right stimulation frequency
            right_cathode: Right electrode cathode configuration
            right_anode: Right electrode anode configuration
            right_amp: Right amplitude
            right_pw: Right pulse width
        """
        self.session_left_stim_freq_edit.setText(left_frequency)
        self.session_left_amp_edit.setText(left_amp)
        self.session_left_pw_edit.setText(left_pw)
        self.session_right_stim_freq_edit.setText(right_frequency)
        self.session_right_amp_edit.setText(right_amp)
        self.session_right_pw_edit.setText(right_pw)

        if hasattr(self, "_current_model") and self._current_model:
            self.set_electrode_model(self._current_model)

        if hasattr(self, "group_combo") and group:
            try:
                self.group_combo.setCurrentText(str(group))
            except Exception:
                pass

        if self.left_canvas.model:
            self._apply_contact_text_to_canvas(self.left_canvas, left_anode, left_cathode)
        if self.right_canvas.model:
            self._apply_contact_text_to_canvas(self.right_canvas, right_anode, right_cathode)

        self.update_configuration_display()

    def _apply_contact_text_to_canvas(self, canvas: ElectrodeCanvas, anode_text: str, cathode_text: str) -> None:
        model = canvas.model
        if not model:
            return

        canvas.contact_states.clear()
        canvas.case_state = ContactState.OFF

        def apply_tokens(text: str, state: int) -> None:
            if not text:
                return
            for token in text.split("_"):
                token = token.strip()
                if not token:
                    continue

                if token == "case":
                    canvas.case_state = state
                    continue

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

                if model.is_directional and len(token) >= 2:
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

        is_valid, _ = StimulationRule.validate_configuration(canvas.contact_states, canvas.case_state)
        if not is_valid:
            canvas.contact_states.clear()
            canvas.case_state = ContactState.OFF

        canvas.update()
