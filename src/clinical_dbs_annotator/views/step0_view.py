"""
Step 0 view: Mode selection page.

This module contains the initial view where users choose between
full mode (with stimulation settings and scales) or annotations-only mode,
and provides access to longitudinal reporting.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    QFrame,
)
from PyQt5.QtGui import QFont


class Step0View(QWidget):
    """
    Step 0: Mode selection view.

    Organized into two sections:
    - Session Notes: start a new annotation session (full or simple mode)
    - Longitudinal Data: create longitudinal reports from existing sessions
    """

    def __init__(self, parent=None):
        """Initialize the Step 0 view."""
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 16, 24, 16)
        self.main_layout.setSpacing(16)

        # ── Section 1: Session Notes ──────────────────────────────
        section1_label = QLabel("Session Notes")
        section1_label.setObjectName("step0_section_title")
        section1_label.setFont(QFont("Arial", 13, QFont.DemiBold))
        section1_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.main_layout.addWidget(section1_label)

        # Buttons row for session notes
        notes_buttons_layout = QHBoxLayout()
        notes_buttons_layout.setAlignment(Qt.AlignCenter)
        notes_buttons_layout.setSpacing(30)

        # Full mode button
        self.full_mode_button = QPushButton(
            "Annotations + Stimulation\nSettings + Clinical Scales"
        )
        self.full_mode_button.setObjectName("full_mode_button")
        self.full_mode_button.setFixedHeight(150)
        self.full_mode_button.setFixedWidth(250)
        self.full_mode_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.full_mode_button.setCursor(Qt.PointingHandCursor)
        notes_buttons_layout.addWidget(self.full_mode_button)

        # Annotations only button
        self.annotations_only_button = QPushButton("Free annotations")
        self.annotations_only_button.setObjectName("annotations_only_button")
        self.annotations_only_button.setFixedHeight(150)
        self.annotations_only_button.setFixedWidth(250)
        self.annotations_only_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.annotations_only_button.setCursor(Qt.PointingHandCursor)
        notes_buttons_layout.addWidget(self.annotations_only_button)

        self.main_layout.addLayout(notes_buttons_layout)

        # ── Separator ─────────────────────────────────────────────
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)

        # ── Section 2: Longitudinal Data ──────────────────────────
        section2_label = QLabel("Longitudinal Data")
        section2_label.setObjectName("step0_section_title")
        section2_label.setFont(QFont("Arial", 13, QFont.DemiBold))
        section2_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.main_layout.addWidget(section2_label)

        # Longitudinal report button
        longitudinal_buttons_layout = QHBoxLayout()
        longitudinal_buttons_layout.setAlignment(Qt.AlignCenter)
        longitudinal_buttons_layout.setSpacing(30)

        self.longitudinal_report_button = QPushButton("Create Longitudinal\nReport")
        self.longitudinal_report_button.setObjectName("longitudinal_report_button")
        self.longitudinal_report_button.setFixedHeight(150)
        self.longitudinal_report_button.setFixedWidth(250)
        self.longitudinal_report_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.longitudinal_report_button.setCursor(Qt.PointingHandCursor)
        longitudinal_buttons_layout.addWidget(self.longitudinal_report_button)

        self.main_layout.addLayout(longitudinal_buttons_layout)

        # Add stretch to push content up
        self.main_layout.addStretch(1)
