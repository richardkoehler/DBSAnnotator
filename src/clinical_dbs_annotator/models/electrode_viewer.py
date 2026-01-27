"""
DBS Electrode 2D Interactive Viewer
Interactive 2D visualization of deep brain stimulation electrodes
with anodic/cathodic modes and case (ground) support
Based on Lead-DBS repository models
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QPalette, QPainterPath, QLinearGradient

# Import configuration
from ..config_electrode_models import (ContactState, ElectrodeModel, ELECTRODE_MODELS, 
                    MANUFACTURERS, get_all_manufacturers, StimulationRule)


class ElectrodeCanvas(QWidget):
    """Canvas for drawing 2D electrode visualization with clickable contacts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = None
        self.contact_states = {}  # {(contact_idx, segment_idx): ContactState}
        self.case_state = ContactState.OFF  # Case (ground) state
        self.contact_rects = {}  # Dictionary to store contact positions
        self.contact_hit_areas = {}  # {(contact_idx, segment_idx): QPainterPath}
        self.ring_rects = {}  # Dictionary for ring "caps" on directional electrodes
        self.case_rect = None  # Case rectangle
        self.hovered_contact = None
        self.hovered_ring = None
        self.hovered_case = False
        self.validation_callback = None  # Callback for validation
        self.setMinimumWidth(120)
        self.setContentsMargins(2, 2, 2, 2)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
    def set_model(self, model):
        """Set the electrode model and reset all states"""
        self.model = model
        self.contact_states.clear()
        self.case_state = ContactState.OFF
        self.contact_rects.clear()
        self.contact_hit_areas.clear()
        self.ring_rects.clear()
        self.case_rect = None
        self.hovered_contact = None
        self.hovered_ring = None
        self.hovered_case = False
        self.update()
        
    def _is_contact_directional(self, contact_idx: int) -> bool:
        if not self.model or not self.model.is_directional:
            return False
        return 0 < contact_idx < self.model.num_contacts - 1
        
    def calculate_scale(self):
        """Calculate optimal scale to fit electrode in canvas based on height only"""
        if not self.model:
            return 20
            
        contacts_total_mm = (
            self.model.num_contacts * self.model.contact_height
            + max(0, self.model.num_contacts - 1) * self.model.contact_spacing
        )
        total_height_mm = contacts_total_mm + 18
        
        # Calculate scale based on height only
        available_height = max(1, self.height() - 60)
        
        scale_height = available_height / total_height_mm
        
        # Apply only height-based scaling with max limit
        return min(scale_height * 1.2, 40)
        
    def get_contact_at_pos(self, pos):
        """Return contact (contact_index, segment_index) at mouse position"""
        point = QPointF(pos)
        for contact_id, hit_area in self.contact_hit_areas.items():
            if hit_area.contains(point):
                return contact_id
        return None
    
    def get_ring_at_pos(self, pos):
        """Return ring index at mouse position"""
        for ring_idx, rect in self.ring_rects.items():
            if rect.contains(pos):
                return ring_idx
        return None
    
    def is_case_at_pos(self, pos):
        """Check if mouse is over the case"""
        if self.case_rect and self.case_rect.contains(pos):
            return True
        return False
    
    def _apply_change_if_valid(self, new_contact_states, new_case_state):
        is_valid, error_msg = StimulationRule.validate_configuration(
            new_contact_states,
            new_case_state,
        )

        # Always apply the change regardless of validation
        self.contact_states = new_contact_states
        self.case_state = new_case_state

        if self.validation_callback:
            self.validation_callback(is_valid, error_msg)
        self.update()
        return is_valid

    def cycle_contact_state(self, contact_id):
        """Cycle contact state: OFF -> ANODIC -> CATHODIC -> OFF"""
        new_states = dict(self.contact_states)
        current_state = new_states.get(contact_id, ContactState.OFF)

        if current_state == ContactState.OFF:
            new_states[contact_id] = ContactState.ANODIC
        elif current_state == ContactState.ANODIC:
            new_states[contact_id] = ContactState.CATHODIC
        elif current_state == ContactState.CATHODIC:
            if contact_id in new_states:
                del new_states[contact_id]

        self._apply_change_if_valid(new_states, self.case_state)
    
    def cycle_case_state(self):
        """Cycle case state: OFF -> ANODIC -> CATHODIC -> OFF"""
        new_case_state = self.case_state
        if self.case_state == ContactState.OFF:
            new_case_state = ContactState.ANODIC
        elif self.case_state == ContactState.ANODIC:
            new_case_state = ContactState.CATHODIC
        elif self.case_state == ContactState.CATHODIC:
            new_case_state = ContactState.OFF

        self._apply_change_if_valid(dict(self.contact_states), new_case_state)
    
    def set_ring_state(self, ring_idx, state):
        """Set state for all segments of a ring"""
        if not self.model or not self.model.is_directional or not self._is_contact_directional(ring_idx):
            return

        new_states = dict(self.contact_states)
        for seg in range(3):
            contact_id = (ring_idx, seg)
            if state == ContactState.OFF:
                if contact_id in new_states:
                    del new_states[contact_id]
            else:
                new_states[contact_id] = state

        self._apply_change_if_valid(new_states, self.case_state)
        
    def mousePressEvent(self, event):
        """Handle clicks on contacts, rings and case"""
        if event.button() == Qt.LeftButton:
            # Check if a contact was clicked
            contact_id = self.get_contact_at_pos(event.pos())
            if contact_id:
                self.cycle_contact_state(contact_id)
                return

            # Check if a ring (cap) was clicked
            ring_idx = self.get_ring_at_pos(event.pos())
            if ring_idx is not None:
                # Cycle entire ring state
                states = []
                for seg in range(3):
                    contact_id = (ring_idx, seg)
                    states.append(self.contact_states.get(contact_id, ContactState.OFF))
                
                # Determine predominant state
                if all(s == ContactState.OFF for s in states):
                    new_state = ContactState.ANODIC
                elif all(s == ContactState.ANODIC for s in states):
                    new_state = ContactState.CATHODIC
                else:
                    new_state = ContactState.OFF
                
                self.set_ring_state(ring_idx, new_state)
                return
            
            # Check if case was clicked
            if self.is_case_at_pos(event.pos()):
                self.cycle_case_state()
                return
                
    def mouseMoveEvent(self, event):
        """Handle hover over contacts, rings and case"""
        old_hovered_contact = self.hovered_contact
        old_hovered_ring = self.hovered_ring
        old_hovered_case = self.hovered_case
        
        self.hovered_case = self.is_case_at_pos(event.pos())
        self.hovered_ring = self.get_ring_at_pos(event.pos())
        self.hovered_contact = self.get_contact_at_pos(event.pos())
        
        if (old_hovered_contact != self.hovered_contact or 
            old_hovered_ring != self.hovered_ring or
            old_hovered_case != self.hovered_case):
            self.update()
    
    def get_state_color(self, state, is_hovered=False):
        """Return color based on state"""
        if state == ContactState.ANODIC:
            base_color = QColor(255, 100, 100)  # Red for anodic
            border_color = QColor(200, 50, 50)
        elif state == ContactState.CATHODIC:
            base_color = QColor(100, 150, 255)  # Blue for cathodic
            border_color = QColor(50, 100, 200)
        else:  # OFF
            base_color = QColor(150, 150, 150)  # Gray
            border_color = QColor(50, 50, 50)
        
        if is_hovered:
            base_color = base_color.lighter(120)
            border_color = border_color.lighter(120)
        
        border_width = 3 if state != ContactState.OFF else 1
        if is_hovered:
            border_width += 1
            
        return base_color, border_color, border_width
            
    def paintEvent(self, event):
        if not self.model:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        palette = self.palette()
        painter.fillRect(self.rect(), palette.color(QPalette.Window))
        
        # Calculate optimal scale
        scale = self.calculate_scale()
        
        # Canvas center
        center_x = self.width() / 2 - 4
        top_padding = 4
        
        # Clear position dictionaries
        self.contact_rects.clear()
        self.contact_hit_areas.clear()
        self.ring_rects.clear()
        
        # Draw case (ground) at the top
        case_height = 4 * scale
        case_width = self.model.lead_diameter * scale * 1.35 + 10
        case_x = center_x - case_width / 2
        case_y = top_padding
        start_y = case_y + case_height + 5
        
        self.case_rect = QRectF(case_x, case_y, case_width, case_height)
        
        color, border_color, border_width = self.get_state_color(
            self.case_state, 
            self.hovered_case
        )
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(self.case_rect, 5, 5)
        
        # Case label
        painter.setPen(Qt.white if self.case_state != ContactState.OFF else Qt.black)
        font = QFont('Arial', max(8, int(scale * 0.4)), QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.case_rect, Qt.AlignCenter, "CASE")
        
        # Draw electrode body (lead)
        lead_width = self.model.lead_diameter * scale * 1.4
        contacts_total_mm = (
            self.model.num_contacts * self.model.contact_height
            + max(0, self.model.num_contacts - 1) * self.model.contact_spacing
        )
        total_height = (contacts_total_mm + 8) * scale
        
        # Create gradient for 3D effect
        gradient = QLinearGradient(center_x - lead_width/2, start_y, center_x + lead_width/2, start_y)
        gradient.setColorAt(0, palette.color(QPalette.Midlight).lighter(120))
        gradient.setColorAt(0.5, palette.color(QPalette.Midlight))
        gradient.setColorAt(1, palette.color(QPalette.Midlight).darker(110))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(palette.color(QPalette.Dark), 2))
        painter.drawRoundedRect(
            int(center_x - lead_width/2),
            int(start_y),
            int(lead_width),
            int(total_height),
            int(lead_width/4),
            int(lead_width/4)
        )
        
        # Draw contacts
        current_y = start_y + 4 * scale
        base_extension = lead_width * 0.15 if self.model.is_directional else 0
         
        for i in range(self.model.num_contacts):
            contact_height_px = self.model.contact_height * scale
            contact_number = self.model.num_contacts - 1 - i
            contact_idx = contact_number
            is_directional_contact = self._is_contact_directional(contact_idx)
             
            if is_directional_contact:
                # Store ring cap position but don't draw yet - will draw after contacts
                ring_cap_height = contact_height_px * 0.5
                ring_cap_width = lead_width * 1.3
                ring_cap_rect = QRectF(
                    center_x - ring_cap_width/2,
                    current_y - ring_cap_height + 10,
                    ring_cap_width,
                    ring_cap_height
                )
                self.ring_rects[contact_idx] = ring_cap_rect
                
                # Directional electrode with improved geometry
                # Segments extend beyond the lead body
                segment_width = lead_width * 0.5  # Wider segments
                extension = base_extension  # How much they extend
                
                # Segment 'a' (left) - extends left
                contact_id_a = (contact_idx, 0)
                state_a = self.contact_states.get(contact_id_a, ContactState.OFF)
                is_hovered_a = contact_id_a == self.hovered_contact
                color_a, border_a, width_a = self.get_state_color(state_a, is_hovered_a)
                
                painter.setBrush(QBrush(color_a))
                painter.setPen(QPen(border_a, width_a))
                
                # Create trapezoid shape for left segment
                x_left = center_x - lead_width/2 - extension
                poly_a = QPolygonF([
                    QPointF(x_left, current_y),
                    QPointF(center_x - lead_width/6, current_y),
                    QPointF(center_x - lead_width/6, current_y + contact_height_px),
                    QPointF(x_left + extension/2, current_y + contact_height_px)
                ])
                painter.drawPolygon(poly_a)
                self.contact_rects[contact_id_a] = poly_a.boundingRect()
                path_a = QPainterPath()
                path_a.addPolygon(poly_a)
                self.contact_hit_areas[contact_id_a] = path_a
                
                # Label
                painter.setPen(Qt.white if state_a != ContactState.OFF else Qt.black)
                font = QFont('Arial', max(7, int(scale * 0.4)))
                painter.setFont(font)
                painter.drawText(self.contact_rects[contact_id_a], Qt.AlignCenter, "a")
                
                # Segment 'b' (center)
                contact_id_b = (contact_idx, 1)
                state_b = self.contact_states.get(contact_id_b, ContactState.OFF)
                is_hovered_b = contact_id_b == self.hovered_contact
                color_b, border_b, width_b = self.get_state_color(state_b, is_hovered_b)
                
                painter.setBrush(QBrush(color_b))
                painter.setPen(QPen(border_b, width_b))
                
                rect_b = QRectF(
                    center_x - lead_width/6,
                    current_y,
                    lead_width/3,
                    contact_height_px
                )
                painter.drawRect(rect_b)
                self.contact_rects[contact_id_b] = rect_b
                path_b = QPainterPath()
                path_b.addRect(rect_b)
                self.contact_hit_areas[contact_id_b] = path_b
                
                painter.setPen(Qt.white if state_b != ContactState.OFF else Qt.black)
                painter.drawText(rect_b, Qt.AlignCenter, "b")
                
                # Segment 'c' (right) - extends right
                contact_id_c = (contact_idx, 2)
                state_c = self.contact_states.get(contact_id_c, ContactState.OFF)
                is_hovered_c = contact_id_c == self.hovered_contact
                color_c, border_c, width_c = self.get_state_color(state_c, is_hovered_c)
                
                painter.setBrush(QBrush(color_c))
                painter.setPen(QPen(border_c, width_c))
                
                # Create trapezoid shape for right segment
                x_right = center_x + lead_width/2 + extension
                poly_c = QPolygonF([
                    QPointF(center_x + lead_width/6, current_y),
                    QPointF(x_right, current_y),
                    QPointF(x_right - extension/2, current_y + contact_height_px),
                    QPointF(center_x + lead_width/6, current_y + contact_height_px)
                ])
                painter.drawPolygon(poly_c)
                self.contact_rects[contact_id_c] = poly_c.boundingRect()
                path_c = QPainterPath()
                path_c.addPolygon(poly_c)
                self.contact_hit_areas[contact_id_c] = path_c
                
                painter.setPen(Qt.white if state_c != ContactState.OFF else Qt.black)
                painter.drawText(self.contact_rects[contact_id_c], Qt.AlignCenter, "c")
                
            else:
                # Standard electrode without segments (also used for first/last contacts in directional leads)
                contact_id = (contact_idx, 0)
                contact_state = self.contact_states.get(contact_id, ContactState.OFF)
                is_hovered = contact_id == self.hovered_contact
                
                color, border_color, border_width = self.get_state_color(
                    contact_state, 
                    is_hovered
                )
                
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(border_color, border_width))
                
                # Draw contact rectangle
                rect = QRectF(
                    center_x - lead_width/2 + 2,
                    current_y,
                    lead_width - 4,
                    contact_height_px
                )
                painter.drawRoundedRect(rect, 3, 3)
                
                # Store position
                self.contact_rects[contact_id] = rect
                path = QPainterPath()
                path.addRect(rect)
                self.contact_hit_areas[contact_id] = path
            
            # Contact number on the left
            painter.setPen(palette.color(QPalette.Text))
            font = QFont('Arial', max(10, int(scale * 0.5)), QFont.Bold)
            painter.setFont(font)
            
            label_extension = base_extension if is_directional_contact else 0
            extra_offset = label_extension + 15 if is_directional_contact else 0
            
            # Adjust horizontal position for better alignment
            if is_directional_contact:
                label_x = center_x - lead_width/2 - label_extension - 22 - extra_offset
            else:
                # For ring contacts, center the label relative to the contact rectangle
                contact_rect_x = center_x - lead_width/2 + 2
                contact_rect_width = lead_width - 4
                label_x = contact_rect_x + contact_rect_width/2 - 30
            
            # Use new E0, E1a format for labels
            if is_directional_contact:
                contact_label = f"E{contact_idx}"
            else:
                contact_label = f"E{contact_idx}"
            
            painter.drawText(
                int(label_x),
                int(current_y),
                35,
                int(contact_height_px),
                Qt.AlignVCenter | Qt.AlignRight,
                contact_label
            )
            
            # Spacing between contacts
            current_y += contact_height_px + self.model.contact_spacing * scale
        
        # Draw ring caps on top of contacts (after all contacts are drawn)
        for contact_idx, ring_cap_rect in self.ring_rects.items():
            # Cap color based on ring state
            ring_states = [self.contact_states.get((contact_idx, seg), ContactState.OFF) 
                          for seg in range(3)]
            if all(s == ContactState.ANODIC for s in ring_states):
                ring_state = ContactState.ANODIC
            elif all(s == ContactState.CATHODIC for s in ring_states):
                ring_state = ContactState.CATHODIC
            else:
                ring_state = ContactState.OFF
            
            is_ring_hovered = self.hovered_ring == contact_idx
            cap_color, cap_border, cap_width = self.get_state_color(
                ring_state, 
                is_ring_hovered
            )
            painter.setBrush(QBrush(cap_color.lighter(130)))
            painter.setPen(QPen(cap_border, cap_width))
            painter.drawRoundedRect(ring_cap_rect, 3, 3)
            
            # Ring label
            painter.setPen(Qt.white if ring_state != ContactState.OFF else Qt.black)
            font = QFont('Arial', max(6, int(scale * 0.3)))
            painter.setFont(font)
            painter.drawText(ring_cap_rect, Qt.AlignCenter, "Ring")

        
    def resizeEvent(self, event):
        """Redraw when window is resized"""
        super().resizeEvent(event)
        self.update()