"""Modern dark/light styling for Reims Control Center."""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #121418;
    color: #F1F5F9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #F1F5F9;
}

/* Header & Panels */
#appHeader {
    background-color: #1A1D24;
    border-bottom: 1px solid #2B303B;
    padding: 12px 18px;
}

#brandTitle {
    font-size: 16px;
    font-weight: 700;
    color: #FFFFFF;
}

#brandSubtitle {
    font-size: 11px;
    color: #94A3B8;
}

/* Doctor Bar */
#doctorBar {
    background-color: #1A1D24;
    border: 1px solid #2B303B;
    border-radius: 8px;
    padding: 10px 16px;
}

/* Resource Monitor Bar (CPU/RAM charts) */
#resourceBar {
    background-color: #1A1D24;
    border: 1px solid #2B303B;
    border-radius: 8px;
    padding: 10px 16px;
}

.doctor-item {
    font-size: 12px;
    font-weight: 500;
    color: #94A3B8;
}

.doctor-item-ok {
    color: #22C55E;
    font-size: 12px;
    font-weight: 600;
}

.doctor-item-warn {
    color: #EF4444;
    font-size: 12px;
    font-weight: 600;
}

/* VM Card */
#vmCard {
    background-color: #1A1D24;
    border: 1px solid #2B303B;
    border-radius: 8px;
    padding: 16px;
}

#vmCard:hover {
    border-color: #3B82F6;
}

#vmCardTitle {
    font-size: 15px;
    font-weight: 700;
    color: #FFFFFF;
}

#vmCardMeta {
    font-size: 11px;
    color: #94A3B8;
}

#specGrid {
    background-color: #121418;
    border: 1px solid #2B303B;
    border-radius: 6px;
    padding: 8px 12px;
}

.spec-label {
    font-size: 10px;
    text-transform: uppercase;
    color: #64748B;
    font-weight: 600;
}

.spec-value {
    font-size: 13px;
    font-weight: 700;
    color: #F8FAFC;
}

/* Status Badges */
.badge-running {
    background-color: rgba(34, 197, 94, 0.15);
    color: #22C55E;
    border: 1px solid rgba(34, 197, 94, 0.4);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

.badge-stopped {
    background-color: rgba(148, 163, 184, 0.15);
    color: #94A3B8;
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

/* Buttons */
QPushButton {
    background-color: #262B35;
    color: #F8FAFC;
    border: 1px solid #333A48;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #333A48;
    border-color: #4B5563;
}

QPushButton:pressed {
    background-color: #1E232B;
}

QPushButton#primaryBtn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
}

QPushButton#primaryBtn:hover {
    background-color: #1D4ED8;
}

QPushButton#dangerBtn {
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

QPushButton#dangerBtn:hover {
    background-color: #EF4444;
    color: #FFFFFF;
}

/* Inputs, Combos, Sliders */
QLineEdit, QComboBox, QSpinBox {
    background-color: #121418;
    color: #F8FAFC;
    border: 1px solid #333A48;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #3B82F6;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QSlider::groove:horizontal {
    border: 1px solid #333A48;
    height: 6px;
    background: #121418;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #2563EB;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #2563EB;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
"""
