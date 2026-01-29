"""
Session data exporter for Clinical DBS Annotator.

This module provides functionality to export session data to Word and PDF.
"""

import os
import tempfile
from datetime import datetime
from typing import Optional

import pandas as pd
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtGui import QPixmap
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False
    docx2pdf_convert = None

from ..config import PLACEHOLDERS
from ..config_electrode_models import ContactState, ELECTRODE_MODELS
from ..models import ElectrodeCanvas

class SessionExporter:
    """
    Handles exporting session data to various formats.
    
    This class provides methods to export the collected session data
    to Word and PDF.
    """
    
    def __init__(self, session_data):
        """
        Initialize the session exporter.
        
        Args:
            session_data: The SessionData instance containing collected data
        """
        self.session_data = session_data
     
    
    def _read_session_data(self) -> Optional[pd.DataFrame]:
        """
        Read session data from the TSV file.
        
        Returns:
            DataFrame with session data or None if error
        """
        try:
            if hasattr(self.session_data, 'file_path') and self.session_data.file_path:
                return pd.read_csv(self.session_data.file_path, sep='\t')
            return None
        except Exception:
            return None
    
    # NOTE: Excel export removed.
    
    def _create_lateral_table_data(self, df):
        """
        Create lateral table structure for Word and PDF exports.
        
        Returns DataFrame with lateral structure:
        - Left side parameters in first row
        - Right side parameters in second row
        - Non-lateral data merged vertically
        - Multiple scales from same block grouped in single cell
        """
        if df.empty:
            return df
        
        # Group by block_id to consolidate multiple scales
        if 'block_id' in df.columns:
            grouped = df.groupby('block_id', sort=False)
        else:
            grouped = [(0, df)]
        
        # Create new lateral structure
        lateral_data = []
        
        # Process each block
        for block_id, block_df in grouped:
            # Get first row for stimulation parameters
            first_row = block_df.iloc[0]
            
            # Collect all scales for this block
            scale_names = []
            scale_values = []
            for _, row in block_df.iterrows():
                sname = row.get('scale_name', '')
                sval = row.get('scale_value', '')
                if pd.notna(sname) and str(sname).strip():
                    scale_names.append(str(sname))
                    scale_values.append(str(sval) if pd.notna(sval) else '')
            
            # Join multiple scales with newlines for internal separation
            combined_scale_name = '\n'.join(scale_names) if scale_names else ''
            combined_scale_value = '\n'.join(scale_values) if scale_values else ''
            
            # Left side row
            left_row = {}
            right_row = {}
            
            # Common columns (non-lateral) - use combined scales with internal lines
            left_row['group_ID'] = first_row.get('group_ID', '')
            left_row['scale_name'] = combined_scale_name
            left_row['scale_value'] = combined_scale_value
            left_row['notes'] = first_row.get('notes', '')
            
            right_row['group_ID'] = first_row.get('group_ID', '')
            right_row['scale_name'] = combined_scale_name
            right_row['scale_value'] = combined_scale_value
            right_row['notes'] = first_row.get('notes', '')
            
            # Lateral columns - map to generic names
            lateral_mappings = {
                'left_stim_freq': 'frequency',
                'left_cathode': 'cathode',
                'left_anode': 'anode',
                'left_amplitude': 'amplitude',
                'left_pulse_width': 'pulse_width',
                'right_stim_freq': 'frequency',
                'right_cathode': 'cathode',
                'right_anode': 'anode',
                'right_amplitude': 'amplitude',
                'right_pulse_width': 'pulse_width',
            }
            
            # Left side parameters
            for left_col, generic_col in lateral_mappings.items():
                if left_col.startswith('left_'):
                    left_row[generic_col] = first_row.get(left_col, '')
            
            # Right side parameters
            for right_col, generic_col in lateral_mappings.items():
                if right_col.startswith('right_'):
                    right_row[generic_col] = first_row.get(right_col, '')
            
            # Add lateral indicator
            left_row['laterality'] = 'L'
            right_row['laterality'] = 'R'
            
            lateral_data.append(left_row)
            lateral_data.append(right_row)
        
        return pd.DataFrame(lateral_data)

    def _column_header(self, col: str) -> str:
        placeholder_map = {
            "scale_name": PLACEHOLDERS.get("scale_name"),
            "scale_value": PLACEHOLDERS.get("scale_value"),
            "frequency": PLACEHOLDERS.get("frequency"),
            "anode": "+",
            "cathode": "-",
            "amplitude": PLACEHOLDERS.get("amplitude"),
            "pulse_width": PLACEHOLDERS.get("pulse_width"),
            "group_ID": "grp",
            "laterality": "",
        }
        if col in placeholder_map and placeholder_map[col] is not None:
            return str(placeholder_map[col])
        return str(col).replace('_', ' ').title()

    def _pick_latest_row(self, df: pd.DataFrame) -> Optional[pd.Series]:
        if df is None or df.empty:
            return None
        if "block_id" in df.columns:
            try:
                bid = pd.to_numeric(df["block_id"], errors="coerce")
                return df.loc[bid.idxmax()]
            except Exception:
                return df.iloc[-1]
        return df.iloc[-1]
    
    def _set_cell_border_top(self, cell, sz=12):
        """Set top border of a cell to specified size (in eighths of a point)."""
        try:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            top = OxmlElement('w:top')
            top.set(qn('w:val'), 'single')
            top.set(qn('w:sz'), str(sz))
            top.set(qn('w:space'), '0')
            top.set(qn('w:color'), '000000')
            tcBorders.append(top)
            tcPr.append(tcBorders)
        except Exception:
            pass
    
    def _set_cell_border_bottom(self, cell, sz=12):
        """Set bottom border of a cell to specified size (in eighths of a point)."""
        try:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), str(sz))
            bottom.set(qn('w:space'), '0')
            bottom.set(qn('w:color'), '000000')
            tcBorders.append(bottom)
            tcPr.append(tcBorders)
        except Exception:
            pass

    def _set_paragraph_bottom_border(self, paragraph, sz: int = 6, color: str = '000000') -> None:
        try:
            pPr = paragraph._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), str(sz))
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), str(color))
            pBdr.append(bottom)
            pPr.append(pBdr)
        except Exception:
            pass

    def _write_multiline_cell_with_dividers(self, cell, lines: list, divider_sz: int = 12, divider_color: str = '000000') -> None:
        """Write each line as its own paragraph and draw a full-width divider under each line except the last."""
        try:
            cell.text = ''
            if not lines:
                return

            p0 = cell.paragraphs[0]
            p0.text = str(lines[0])
            if len(lines) > 1:
                self._set_paragraph_bottom_border(p0, sz=divider_sz, color=divider_color)

            for k in range(1, len(lines)):
                p = cell.add_paragraph(str(lines[k]))
                if k < len(lines) - 1:
                    self._set_paragraph_bottom_border(p, sz=divider_sz, color=divider_color)
        except Exception:
            try:
                cell.text = "\n".join([str(x) for x in (lines or [])])
            except Exception:
                pass

    def _apply_contact_tokens_to_canvas(self, canvas: ElectrodeCanvas, anode_text: str, cathode_text: str) -> None:
        model = canvas.model
        if not model:
            return

        canvas.contact_states.clear()
        canvas.case_state = ContactState.OFF

        def apply_tokens(text: str, state: ContactState) -> None:
            if not text:
                return
            for token in str(text).split("_"):
                token = token.strip()
                if not token:
                    continue
                if token == "case":
                    canvas.case_state = state
                    continue

                if token.startswith("E") and len(token) >= 2:
                    try:
                        if token[-1].isalpha():
                            idx = int(token[1:-1])
                            seg_char = token[-1].lower()
                            seg_map = {"a": 0, "b": 1, "c": 2}
                            if seg_char in seg_map:
                                canvas.contact_states[(idx, seg_map[seg_char])] = state
                        else:
                            idx = int(token[1:])
                            if model.is_directional:
                                for seg in range(3):
                                    canvas.contact_states[(idx, seg)] = state
                            else:
                                canvas.contact_states[(idx, 0)] = state
                    except Exception:
                        continue

        apply_tokens(anode_text, ContactState.ANODIC)
        apply_tokens(cathode_text, ContactState.CATHODIC)
        canvas.update()

    def _render_electrode_png(
        self,
        model_name: str,
        anode_text: str,
        cathode_text: str,
        target_size_px: tuple[int, int] = (220, 320),
    ) -> Optional[str]:
        model = ELECTRODE_MODELS.get(model_name)
        if not model:
            return None

        canvas = ElectrodeCanvas()
        canvas.set_model(model)
        canvas.resize(*target_size_px)
        self._apply_contact_tokens_to_canvas(canvas, anode_text, cathode_text)

        pixmap = QPixmap(canvas.size())
        pixmap.fill(canvas.palette().color(canvas.backgroundRole()))
        canvas.render(pixmap)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.close()
        pixmap.save(tmp.name, "PNG")
        return tmp.name

    def _add_electrode_config_section(self, doc: Document, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        if "session_ID" not in df.columns or "is_initial" not in df.columns:
            return

        dfc = df.copy()
        dfc["session_ID"] = pd.to_numeric(dfc["session_ID"], errors="coerce")
        dfc["is_initial"] = pd.to_numeric(dfc["is_initial"], errors="coerce").fillna(0).astype(int)

        df_init = dfc[dfc["is_initial"] == 1]
        df_final = dfc[dfc["is_initial"] == 0]

        if df_init.empty or df_final.empty:
            return

        init_session = int(dfc.loc[df_init.index, "session_ID"].max())
        final_session = int(dfc.loc[df_final.index, "session_ID"].max())

        init_row = self._pick_latest_row(df_init[df_init["session_ID"] == init_session])
        final_row = self._pick_latest_row(df_final[df_final["session_ID"] == final_session])

        if init_row is None or final_row is None:
            return

        init_model = str(init_row.get("electrode_model", "") or "")
        final_model = str(final_row.get("electrode_model", "") or "")
        if not init_model or not final_model:
            return

        paths = {
            "Init L": self._render_electrode_png(init_model, str(init_row.get("left_anode", "") or ""), str(init_row.get("left_cathode", "") or "")),
            "Init R": self._render_electrode_png(init_model, str(init_row.get("right_anode", "") or ""), str(init_row.get("right_cathode", "") or "")),
            "Final L": self._render_electrode_png(final_model, str(final_row.get("left_anode", "") or ""), str(final_row.get("left_cathode", "") or "")),
            "Final R": self._render_electrode_png(final_model, str(final_row.get("right_anode", "") or ""), str(final_row.get("right_cathode", "") or "")),
        }

        if not all(paths.values()):
            return

        doc.add_heading("Electrode Configurations", level=1)

        t = doc.add_table(rows=2, cols=4)
        t.autofit = False

        labels = ["Init L", "Init R", "Final L", "Final R"]
        for c, label in enumerate(labels):
            t.cell(0, c).text = label

        for c, label in enumerate(labels):
            cell = t.cell(1, c)
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run()
            run.add_picture(paths[label], width=Inches(1.35))

        for pth in paths.values():
            try:
                os.unlink(pth)
            except Exception:
                pass

    def _compute_table_widths_points(self, ordered_columns, page_width_points: float) -> list:
        base = {
            'laterality': 55,
            'group': 45,
            'frequency': 55,
            'cathode': 80,
            'anode': 80,
            'amplitude': 60,
            'pulse_width': 60,
            'scale_name': 80,
            'scale_value': 55,
            'session_condition': 70,
        }
        widths = [base.get(col, 60) for col in ordered_columns]
        if 'notes' in ordered_columns:
            notes_idx = ordered_columns.index('notes')
            min_notes = 160
            widths[notes_idx] = min_notes
            used = sum(widths)
            if used < page_width_points:
                widths[notes_idx] += (page_width_points - used)
        return widths

    def export_to_pdf(self, parent: Optional[QWidget] = None) -> bool:
        """Export session data to PDF by generating a Word report and converting it."""
        try:
            if not DOCX2PDF_AVAILABLE:
                QMessageBox.critical(
                    parent,
                    "Missing Dependency",
                    "PDF export requires the 'docx2pdf' package.\n\n"
                    "Please install it by running:\n"
                    "pip install docx2pdf\n\n"
                    "Alternatively, export to Word (.docx) and convert manually.",
                )
                return False

            if not self.session_data.is_file_open():
                QMessageBox.warning(
                    parent,
                    "No Session Data",
                    "No session file is currently open. Please start a session first.",
                )
                return False

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"dbs_session_report_{timestamp}.pdf"

            from PyQt5.QtWidgets import QFileDialog

            pdf_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Export Session Report",
                default_filename,
                "PDF Files (*.pdf);;All Files (*)",
            )

            if not pdf_path:
                return False

            if not pdf_path.endswith(".pdf"):
                pdf_path += ".pdf"

            docx_path = os.path.splitext(pdf_path)[0] + ".docx"

            ok = self._export_to_word_path(docx_path)
            if not ok:
                return False

            # Best option on Windows: uses Microsoft Word to convert
            docx2pdf_convert(docx_path, pdf_path)

            # Alternatives (commented):
            # - LibreOffice headless conversion: soffice --headless --convert-to pdf <docx>
            # - pypandoc (requires pandoc)

            QMessageBox.information(
                parent,
                "Export Successful",
                f"Session report exported successfully to:\n{pdf_path}",
            )

            return True

        except Exception as e:
            QMessageBox.critical(
                parent,
                "Export Error",
                f"Failed to export session data to PDF:\n{str(e)}",
            )
            return False
    
    def export_to_word(self, parent: Optional[QWidget] = None) -> bool:
        """
        Export session data to Word format.
        
        Args:
            parent: Parent widget for dialog display
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Get the current session data
            if not self.session_data.is_file_open():
                QMessageBox.warning(
                    parent, 
                    "No Session Data", 
                    "No session file is currently open. Please start a session first."
                )
                return False
            
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"dbs_session_report_{timestamp}.docx"
            
            # Get save location
            from PyQt5.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Export Session Report",
                default_filename,
                "Word Files (*.docx);;All Files (*)"
            )
            
            if not file_path:
                return False  # User cancelled
            
            # Ensure .docx extension
            if not file_path.endswith('.docx'):
                file_path += '.docx'

            ok = self._export_to_word_path(file_path)
            if not ok:
                QMessageBox.warning(
                    parent,
                    "No Data to Export",
                    "No session data has been recorded yet.",
                )
                return False

            QMessageBox.information(
                parent,
                "Export Successful",
                f"Session report exported successfully to:\n{file_path}",
            )

            return True
            
        except Exception as e:
            QMessageBox.critical(
                parent,
                "Export Error",
                f"Failed to export session data to Word:\n{str(e)}"
            )
            return False

    def _export_to_word_path(self, file_path: str) -> bool:
        """Generate the Word report at an explicit path (used also by PDF export)."""
        df = self._read_session_data()
        if df is None or df.empty:
            return False

        df = df.copy()
        if "is_initial" in df.columns:
            df["is_initial"] = pd.to_numeric(df["is_initial"], errors="coerce").fillna(0).astype(int)

        df_initial = df[df.get("is_initial", 0) == 1] if "is_initial" in df.columns else df.iloc[0:0]
        df_table = df[df.get("is_initial", 0) != 1] if "is_initial" in df.columns else df

        doc = Document()

        title = doc.add_heading('Clinical DBS Session Report', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        doc.add_paragraph(f'Total Records: {len(df)}')
        doc.add_paragraph('')

        doc.add_heading('Summary', level=1)
        
        # Basic statistics
        doc.add_paragraph(f'Total Records: {len(df)}')
        doc.add_paragraph(f'Unique Scales: {df["scale_name"].nunique() if "scale_name" in df.columns else 0}')
        
        # Initial session information with electrode drawings
        if not df_initial.empty and "session_ID" in df_initial.columns:
            doc.add_paragraph('')
            doc.add_heading('Initial Sessions', level=2)
            for sid in sorted(pd.to_numeric(df_initial["session_ID"], errors="coerce").dropna().unique()):
                srows = df_initial[pd.to_numeric(df_initial["session_ID"], errors="coerce") == sid]
                latest = self._pick_latest_row(srows)
                if latest is None:
                    continue
                
                p = doc.add_paragraph()
                p.add_run(f"Session {int(sid)}").bold = True
                p.add_run(f" | Group: {latest.get('group_ID','')}")
                
                # Add electrode canvas drawings for initial session
                model = str(latest.get('electrode_model', '') or '')
                if model:
                    left_path = self._render_electrode_png(
                        model,
                        str(latest.get('left_anode', '') or ''),
                        str(latest.get('left_cathode', '') or '')
                    )
                    right_path = self._render_electrode_png(
                        model,
                        str(latest.get('right_anode', '') or ''),
                        str(latest.get('right_cathode', '') or '')
                    )
                    
                    if left_path and right_path:
                        # Create a small table for side-by-side electrode images
                        t = doc.add_table(rows=2, cols=2)
                        t.autofit = False
                        t.cell(0, 0).text = 'Left'
                        t.cell(0, 1).text = 'Right'
                        
                        # Add images
                        cell_l = t.cell(1, 0)
                        cell_l.text = ''
                        p_l = cell_l.paragraphs[0]
                        run_l = p_l.add_run()
                        run_l.add_picture(left_path, width=Inches(1.0))
                        
                        cell_r = t.cell(1, 1)
                        cell_r.text = ''
                        p_r = cell_r.paragraphs[0]
                        run_r = p_r.add_run()
                        run_r.add_picture(right_path, width=Inches(1.0))
                        
                        # Clean up temp files
                        try:
                            os.unlink(left_path)
                            os.unlink(right_path)
                        except Exception:
                            pass

        doc.add_paragraph('')

        self._add_electrode_config_section(doc, df)

        doc.add_heading('Session Data', level=1)

        lateral_df = self._create_lateral_table_data(df_table)
        
        # Keep block_id for tracking block changes (but don't display it)
        block_ids = df_table['block_id'].tolist() if 'block_id' in df_table.columns else []

        columns_to_exclude = ['date', 'time', 'onset', 'block_id', 'session_ID', 'is_initial', 'electrode_model']
        display_columns = [col for col in lateral_df.columns if col not in columns_to_exclude]

        lateral_cols = ['laterality', 'frequency', 'cathode', 'anode', 'amplitude', 'pulse_width']
        common_cols = ['group_ID', 'scale_name', 'scale_value', 'notes']

        lateral_cols = [col for col in lateral_cols if col in display_columns]
        common_cols = [col for col in common_cols if col in display_columns]
        ordered_columns = lateral_cols + common_cols

        table = doc.add_table(rows=lateral_df.shape[0] + 1, cols=len(ordered_columns))
        table.style = 'Table Grid'
        table.autofit = False

        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(ordered_columns):
            hdr_cells[i].text = self._column_header(col_name)
            for paragraph in hdr_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        # Column widths: keep others compact, give remaining to notes
        try:
            section = doc.sections[0]
            page_width_inches = (section.page_width - section.left_margin - section.right_margin) / 914400

            base_in = {
                'laterality': 0.35,
                'group_ID': 0.5,
                'frequency': 0.65,
                'cathode': 0.95,
                'anode': 0.95,
                'amplitude': 0.65,
                'pulse_width': 0.75,
                'scale_name': 0.95,
                'scale_value': 0.65,
            }
            widths_in = [base_in.get(c, 0.8) for c in ordered_columns]
            if 'notes' in ordered_columns:
                notes_idx = ordered_columns.index('notes')
                widths_in[notes_idx] = 2.5
                used = sum(widths_in)
                if used < page_width_inches:
                    widths_in[notes_idx] += (page_width_inches - used)

            for i, w in enumerate(widths_in):
                table.columns[i].width = Inches(max(0.35, w))
        except Exception:
            pass

        prev_block_id = None
        for i, (idx, row) in enumerate(lateral_df.iterrows()):
            row_cells = table.rows[i + 1].cells
            
            # Check if block_id changed (each original row creates 2 lateral rows, so divide by 2)
            if block_ids and len(block_ids) > idx // 2:
                current_block_id = block_ids[idx // 2]
                # Apply thicker border when block changes and it's a Left row (first of pair)
                if prev_block_id is not None and current_block_id != prev_block_id and row.get('laterality') == 'L':
                    for cell in row_cells:
                        self._set_cell_border_top(cell, sz=24)  # Thicker border (24 = 3pt)
                prev_block_id = current_block_id
            
            # Cache column indices for scale_name/scale_value
            if i == 0:
                try:
                    scale_name_idx = ordered_columns.index('scale_name') if 'scale_name' in ordered_columns else -1
                    scale_value_idx = ordered_columns.index('scale_value') if 'scale_value' in ordered_columns else -1
                except Exception:
                    scale_name_idx = -1
                    scale_value_idx = -1

            # Pre-split scale/value lines (keep same count so dividers align visually)
            scale_name_lines = None
            scale_value_lines = None
            if scale_name_idx >= 0 and scale_value_idx >= 0:
                try:
                    raw_sn = row.get('scale_name', '')
                    raw_sv = row.get('scale_value', '')
                    sn_text = str(raw_sn) if pd.notna(raw_sn) else ''
                    sv_text = str(raw_sv) if pd.notna(raw_sv) else ''
                    scale_name_lines = sn_text.split('\n') if sn_text else ['']
                    scale_value_lines = sv_text.split('\n') if sv_text else ['']
                    max_len = max(len(scale_name_lines), len(scale_value_lines))
                    scale_name_lines += [''] * (max_len - len(scale_name_lines))
                    scale_value_lines += [''] * (max_len - len(scale_value_lines))
                except Exception:
                    scale_name_lines = None
                    scale_value_lines = None

            for j, col in enumerate(ordered_columns):
                if col not in row:
                    continue

                cell_value = str(row[col]) if pd.notna(row[col]) else ''

                if col in common_cols:
                    merged_target_cell = None
                    did_merge = False
                    if row.get('laterality') == 'R' and i > 0:
                        prev_cell = table.rows[i].cells[j]
                        prev_cell.merge(row_cells[j])
                        row_cells[j].text = ''
                        merged_target_cell = prev_cell
                        did_merge = True

                    # For scale_name/scale_value: draw per-item horizontal dividers via paragraph bottom borders.
                    # IMPORTANT: common columns are merged on the R row; render into the merged cell (prev_cell).
                    if col == 'scale_name' and scale_name_lines is not None and len(scale_name_lines) > 1:
                        if did_merge and merged_target_cell is not None:
                            self._write_multiline_cell_with_dividers(merged_target_cell, scale_name_lines)
                        else:
                            row_cells[j].text = cell_value
                    elif col == 'scale_value' and scale_value_lines is not None and len(scale_value_lines) > 1:
                        if did_merge and merged_target_cell is not None:
                            self._write_multiline_cell_with_dividers(merged_target_cell, scale_value_lines)
                        else:
                            row_cells[j].text = cell_value
                    else:
                        if did_merge and merged_target_cell is not None:
                            merged_target_cell.text = cell_value
                        else:
                            row_cells[j].text = cell_value
                else:
                    row_cells[j].text = cell_value

        doc.save(file_path)
        return True
