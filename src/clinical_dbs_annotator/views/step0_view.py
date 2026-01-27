"""
Step 0 view: Mode selection page.

This module contains the initial view where users choose between
full mode (with stimulation settings and scales) or annotations-only mode.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
)
from PyQt5.QtGui import QFont


class Step0View(QWidget):
    """
    Step 0: Mode selection view.

    Users can choose between:
    - Full mode: Annotations + stimulation settings + clinical scales
    - Simple mode: Annotations only
    """

    def __init__(self, parent=None):
        """Initialize the Step 0 view."""
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # Buttons container - only the two option squares
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

        # Full mode button
        self.full_mode_button = QPushButton(
            "Annotations + Stimulation\nSettings + Clinical Scales"
        )
        self.full_mode_button.setObjectName("full_mode_button")
        self.full_mode_button.setMinimumHeight(120)
        self.full_mode_button.setMinimumWidth(250)
        self.full_mode_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.full_mode_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.full_mode_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.full_mode_button)

        # Annotations only button
        self.annotations_only_button = QPushButton("Free annotations")
        self.annotations_only_button.setObjectName("annotations_only_button")
        self.annotations_only_button.setMinimumHeight(120)
        self.annotations_only_button.setMinimumWidth(250)
        self.annotations_only_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.annotations_only_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.annotations_only_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.annotations_only_button)

        self.main_layout.addLayout(buttons_layout)

        # Add stretch to center the buttons
        self.main_layout.addStretch(1)
