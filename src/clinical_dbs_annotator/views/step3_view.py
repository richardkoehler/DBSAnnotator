"""
Step 3 view - Active session recording.

This module contains the view for the third step where users actively record
session data including stimulation parameters and scale values.
"""

from typing import List, Tuple
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QProgressBar, QSizePolicy,
    QWidget, QMenu, QComboBox, QStyle
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QDoubleValidator, QIntValidator, QPixmap, QMouseEvent, QIcon

from ..config import (
    PLACEHOLDERS,
    SESSION_SCALE_LIMITS,
    STIMULATION_LIMITS,
)
from ..ui import IncrementWidget, create_horizontal_line
from .base_view import BaseStepView
from ..models import ElectrodeCanvas
from ..config_electrode_models import ContactState, StimulationRule


class InteractiveProgressBar(QWidget):
    """Custom progress bar widget with navigation arrows and drag support."""
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dragging = False
        self._minimum = 0
        self._maximum = 40
        self._value = 0
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the UI with arrows and progress bar."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Left arrows - horizontal layout
        left_layout = QHBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        
        # Single left arrow (-0.25) - closer to bar
        self.left_single_btn = QPushButton()
        self.left_single_btn.setText("◀")
        self.left_single_btn.setFixedSize(18, 18)
        self.left_single_btn.setToolTip("-0.25")
        self.left_single_btn.clicked.connect(lambda: self._adjust_value(-1))
        
        # Double left arrow (-0.5) - farther from bar
        self.left_double_btn = QPushButton()
        self.left_double_btn.setText("◀◀")
        self.left_double_btn.setFixedSize(24, 18)
        self.left_double_btn.setToolTip("-0.5")
        self.left_double_btn.clicked.connect(lambda: self._adjust_value(-2))
        
        left_layout.addWidget(self.left_single_btn)
        left_layout.addWidget(self.left_double_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(self._minimum)
        self.progress_bar.setMaximum(self._maximum)
        self.progress_bar.setValue(self._value)
        self.progress_bar.setFormat("0.00")
        self.progress_bar.setCursor(Qt.PointingHandCursor)
        self.progress_bar.valueChanged.connect(self._on_bar_value_changed)
        
        # Right side controls - horizontal layout
        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        # Single right arrow (+0.25) - closer to bar
        self.right_single_btn = QPushButton()
        self.right_single_btn.setText("▶")
        self.right_single_btn.setFixedSize(18, 18)
        self.right_single_btn.setToolTip("+0.25")
        self.right_single_btn.clicked.connect(lambda: self._adjust_value(1))
        
        # Double right arrow (+0.5) - farther from bar
        self.right_double_btn = QPushButton()
        self.right_double_btn.setText("▶▶")
        self.right_double_btn.setFixedSize(24, 18)
        self.right_double_btn.setToolTip("+0.5")
        self.right_double_btn.clicked.connect(lambda: self._adjust_value(2))
        
        # Reset button (X) - clears the scale value
        self.reset_btn = QPushButton()
        self.reset_btn.setText("✕")
        self.reset_btn.setFixedSize(18, 18)
        self.reset_btn.setToolTip("Reset to 0")
        self.reset_btn.clicked.connect(lambda: self.setValue(0))
        
        right_layout.addWidget(self.right_single_btn)
        right_layout.addWidget(self.right_double_btn)
        right_layout.addWidget(self.reset_btn)
        
        # Add all to main layout
        layout.addLayout(left_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(right_layout)
        
        # Install mouse event filter on progress bar
        self.progress_bar.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        """Handle mouse events on progress bar."""
        if obj == self.progress_bar:
            if event.type() == QEvent.MouseButtonPress:
                self._is_dragging = True
                self._update_value_from_position(event.pos().x())
                return True
            elif event.type() == QEvent.MouseMove:
                if self._is_dragging:
                    self._update_value_from_position(event.pos().x())
                    return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._is_dragging = False
                return True
        return super().eventFilter(obj, event)
        
    def _adjust_value(self, delta):
        """Adjust value by delta (1 = 0.25, 2 = 0.5)."""
        new_value = max(self._minimum, min(self._maximum, self._value + delta))
        self.setValue(new_value)
        
    def _update_value_from_position(self, x_position):
        """Update progress bar value based on mouse position."""
        rect = self.progress_bar.rect()
        if rect.width() > 0:
            relative_x = max(0, min(x_position, rect.width()))
            value = int((relative_x / rect.width()) * self._maximum)
            self.setValue(value)
            
    def _on_bar_value_changed(self, value):
        """Handle progress bar value change."""
        self._value = value
        self.valueChanged.emit(value)
        # Update format to show current value
        actual_value = value / 4.0  # Convert from internal value to actual value
        self.progress_bar.setFormat(f"{actual_value:.2f}")
        
    # Progress bar interface methods
    def setMinimum(self, value):
        self._minimum = value
        self.progress_bar.setMinimum(value)
        
    def setMaximum(self, value):
        self._maximum = value
        self.progress_bar.setMaximum(value)
        
    def setValue(self, value):
        self._value = value
        self.progress_bar.setValue(value)
        
    def setFormat(self, format_str):
        self.progress_bar.setFormat(format_str)
        
    def setFixedWidth(self, width):
        # Reserve space for controls: left (18+24+4+4=50) + right (18+24+18+6+4=70) = 120px total
        bar_width = width - 120  # Space for all controls
        self.progress_bar.setFixedWidth(bar_width)
        super().setFixedWidth(width)
        
    def setToolTip(self, tooltip):
        self.progress_bar.setToolTip(tooltip)
        
    def value(self):
        return self._value


class Step3View(BaseStepView):
    """
    Third step view for active session recording.

    This view handles:
    - Real-time stimulation parameter adjustment
    - Session scale value recording
    - Session notes
    - Data insertion and session closing
    """

    def __init__(self, logo_pixmap: QPixmap, parent_style):
        """
        Initialize Step 3 view.

        Args:
            logo_pixmap: Application logo
            parent_style: Parent widget style for icon access
        """
        super().__init__(logo_pixmap)
        self.parent_style = parent_style
        self.session_scale_value_edits: List[Tuple[str, QLineEdit]] = []
        self.session_scale_progress_bars: List[Tuple[str, QProgressBar]] = []
        self.step3_session_scales_form: QFormLayout = None

        self.left_canvas = ElectrodeCanvas()
        self.right_canvas = ElectrodeCanvas()
        self.left_canvas.validation_callback = self._on_left_canvas_validation
        self.right_canvas.validation_callback = self._on_right_canvas_validation
        self._left_selection_valid = True
        self._right_selection_valid = True

        self._current_model = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(12, 8, 12, 8)

        # Header
        header = self.create_header(
            "Active Session Recording"
        )
        self.main_layout.addWidget(header)

        # Main content area
        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        settings_group = self._create_stimulation_params_group()
        left_layout.addWidget(settings_group)
        #left_layout.addStretch(1)
        content_layout.addLayout(left_layout)

        # Right side: Scales and notes
        right_layout = QVBoxLayout()
        scales_group = self._create_session_scales_group()
        right_layout.addWidget(scales_group)
        right_layout.addWidget(create_horizontal_line())
        notes_group = self._create_notes_group()
        right_layout.addWidget(notes_group)
        content_layout.addLayout(right_layout)

        self.main_layout.addLayout(content_layout)
        #self.main_layout.addStretch(1)

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
        gb_init = QGroupBox("Stimulation settings")
        gb_init.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        gb_init.setFont(QFont("Segoe UI", 12, QFont.Bold))
        gb_init.setStyleSheet(
            "QGroupBox { margin-top: 8pt; } "
            "QGroupBox::title { color: #ff8800; margin-left: 4pt; "
            "font-size: 16pt; font-weight: 600; }"
        )

        container_layout = QHBoxLayout()

        sidebar_layout = QVBoxLayout()

        group_row = QGroupBox("Group")
        group_row_layout = QHBoxLayout()
        self.group_combo = QComboBox()
        self.group_combo.addItems(["A", "B", "C", "D", "None"])
        group_row_layout.addWidget(self.group_combo)
        group_row.setLayout(group_row_layout)

        freq_limits = STIMULATION_LIMITS["frequency"]
        amp_limits = STIMULATION_LIMITS["amplitude"]
        pw_limits = STIMULATION_LIMITS["pulse_width"]

        left_group = QGroupBox("Left")
        left_group_layout = QVBoxLayout()
        left_form = QFormLayout()
        left_form.setLabelAlignment(Qt.AlignRight)

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
        left_form.addRow(QLabel("Stimulation frequency:"), left_freq_widget)

        self.left_config_text = QTextEdit()
        self.left_config_text.setReadOnly(True)
        self.left_config_text.setMinimumHeight(60)
        self.left_config_text.setMaximumHeight(90)
        self.left_config_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        left_form.addRow(QLabel("Amplitude:"), left_amp_widget)

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
        left_form.addRow(QLabel("Pulse width:"), left_pw_widget)

        left_group_layout.addLayout(left_form)
        left_group_layout.addWidget(self.left_config_text)
        left_group.setLayout(left_group_layout)

        right_group = QGroupBox("Right")
        right_group_layout = QVBoxLayout()
        right_form = QFormLayout()
        right_form.setLabelAlignment(Qt.AlignRight)

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
        right_form.addRow(QLabel("Stimulation frequency:"), right_freq_widget)

        self.right_config_text = QTextEdit()
        self.right_config_text.setReadOnly(True)
        self.right_config_text.setMinimumHeight(60)
        self.right_config_text.setMaximumHeight(90)
        self.right_config_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        right_form.addRow(QLabel("Amplitude:"), right_amp_widget)

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
        right_form.addRow(QLabel("Pulse width:"), right_pw_widget)

        right_group_layout.addLayout(right_form)
        right_group_layout.addWidget(self.right_config_text)
        right_group.setLayout(right_group_layout)

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

    def _on_left_canvas_validation(self, is_valid: bool, error_msg: str) -> None:
        self._left_selection_valid = is_valid
        self.update_configuration_display()

    def _on_right_canvas_validation(self, is_valid: bool, error_msg: str) -> None:
        self._right_selection_valid = is_valid
        self.update_configuration_display()

    def set_electrode_model(self, model) -> None:
        self._current_model = model
        self.left_canvas.set_model(model)
        self.right_canvas.set_model(model)
        self.update_configuration_display()

    def update_configuration_display(self) -> None:
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
        gb_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        gb_notes.setStyleSheet(
            "QGroupBox::title { color: #ff8800; font-size: 11pt; font-weight: 600; }"
        )
        gb_notes.setFont(QFont("Segoe UI", 10, QFont.Bold))

        layout = QHBoxLayout(gb_notes)
        self.session_notes_edit = QTextEdit()
        self.session_notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.session_notes_edit.setMinimumHeight(40)
        layout.addWidget(self.session_notes_edit)

        return gb_notes

    def update_session_scales(self, scale_data: List[Tuple[str, str, str]]) -> None:
        """
        Update the session scales form with the given scale data.

        Args:
            scale_data: List of (name, min, max) tuples for each scale
        """
        # Clear existing form
        while self.step3_session_scales_form.rowCount():
            self.step3_session_scales_form.removeRow(0)

        self.session_scale_value_edits = []
        self.session_scale_progress_bars = []

        # Add scale inputs with progress bars
        for name, min_val, max_val in scale_data:
            # Convert min/max to internal values (multiply by 4 for 0.25 precision)
            try:
                min_internal = float(min_val) * 4
                max_internal = float(max_val) * 4
            except (ValueError, TypeError):
                # Fallback to default values
                min_internal = 0
                max_internal = 40  # 10 * 4
            
            # Create interactive progress bar with dynamic range
            progress_bar = InteractiveProgressBar()
            progress_bar.setMinimum(int(min_internal))
            progress_bar.setMaximum(int(max_internal))
            progress_bar.setValue(int(min_internal))  # Start at minimum
            progress_bar.setFixedWidth(300)  # Increased width for better interaction
            progress_bar.setFormat(f"{float(min_val):.2f}")  # Initial format with min value
            
            # Set tooltip
            progress_bar.setToolTip(f"Click or drag to adjust {name} value")
            
            # Create hidden edit to store value
            value_edit = QLineEdit()
            value_edit.setPlaceholderText(PLACEHOLDERS["scale_value"])
            value_edit.setFixedWidth(80)
            value_edit.setValidator(
                QDoubleValidator(float(min_val), float(max_val), 2)
            )
            value_edit.hide()  # Hide the edit field

            # Connect progress bar value change to update the hidden edit
            progress_bar.valueChanged.connect(
                lambda value, edit=value_edit, min_val=min_val: edit.setText(str(value / 4.0))
            )
            
            # Initialize the edit with min value
            value_edit.setText(min_val)
            
            # Create horizontal layout for progress bar
            widget_layout = QHBoxLayout()
            widget_layout.addWidget(progress_bar)
            widget_layout.addWidget(value_edit)
            widget_layout.setContentsMargins(0, 0, 0, 0)

            self.step3_session_scales_form.addRow(QLabel(name + ":"), widget_layout)
            self.session_scale_value_edits.append((name, value_edit))
            self.session_scale_progress_bars.append((name, progress_bar))

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

        is_valid, _ = StimulationRule.validate_configuration(canvas.contact_states, canvas.case_state)
        if not is_valid:
            canvas.contact_states.clear()
            canvas.case_state = ContactState.OFF

        canvas.update()
