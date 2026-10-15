"""
PyQt6 Settings GUI for calwallpaper.
Provides an intuitive, native KDE Plasma interface for managing
calendar feeds, appearance, translucency, sizing, timezones, and sync.
"""

import os
import sys
import yaml
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QSlider, QSpinBox, QComboBox, QLineEdit,
    QPushButton, QColorDialog, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QGroupBox, QFormLayout, QMessageBox,
    QStatusBar, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon

from .config import (
    DEFAULT_CONFIG_PATH, load_config, save_config,
    get_current_plasma_wallpaper, ORIGINAL_WP_FILE
)
from .compositor import render_composite
from .cli import apply_wallpaper_plasma


class WallpaperUpdateWorker(QThread):
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            cfg = load_config()
            out_path = render_composite(cfg)
            success = apply_wallpaper_plasma(out_path)
            if success:
                self.finished.emit(True, f"Wallpaper updated successfully! ({os.path.basename(out_path)})")
            else:
                self.finished.emit(False, "Rendered, but could not sync to all desktops.")
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class CalWallpaperSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendar Wallpaper Settings")
        self.setMinimumSize(780, 620)
        self.config = load_config()

        self.worker = None

        self.init_ui()
        self.load_values_into_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.tab_appearance = QWidget()
        self.tab_grid = QWidget()
        self.tab_calendars = QWidget()
        self.tab_system = QWidget()

        self.tabs.addTab(self.tab_appearance, "🎨 Appearance & Sizing")
        self.tabs.addTab(self.tab_grid, "📅 Grid & Timezones")
        self.tabs.addTab(self.tab_calendars, "🔗 Calendar Sources")
        self.tabs.addTab(self.tab_system, "⚙️ Sync & Automation")

        self.setup_appearance_tab()
        self.setup_grid_tab()
        self.setup_calendars_tab()
        self.setup_system_tab()

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_apply = QPushButton("Apply & Update Wallpaper")
        self.btn_apply.setStyleSheet("font-weight: bold; padding: 8px 16px; background-color: #2563eb; color: white; border-radius: 6px;")
        self.btn_apply.clicked.connect(self.on_apply_clicked)
        bottom_bar.addWidget(self.btn_apply)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setStyleSheet("padding: 8px 16px;")
        self.btn_save.clicked.connect(self.on_save_clicked)
        bottom_bar.addWidget(self.btn_save)

        bottom_bar.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        bottom_bar.addWidget(self.btn_close)

        main_layout.addLayout(bottom_bar)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    # ================= TAB 1: APPEARANCE =================
    def setup_appearance_tab(self):
        layout = QVBoxLayout(self.tab_appearance)
        layout.setSpacing(14)

        # Wallpaper Source Group
        wp_group = QGroupBox("Base Wallpaper Background")
        wp_form = QFormLayout(wp_group)

        self.chk_auto_wp = QCheckBox("Auto-detect active KDE Plasma wallpaper")
        self.chk_auto_wp.toggled.connect(self.on_auto_wp_toggled)
        wp_form.addRow(self.chk_auto_wp)

        wp_file_row = QHBoxLayout()
        self.txt_custom_wp = QLineEdit()
        self.btn_browse_wp = QPushButton("Browse...")
        self.btn_browse_wp.clicked.connect(self.on_browse_wallpaper)
        wp_file_row.addWidget(self.txt_custom_wp)
        wp_file_row.addWidget(self.btn_browse_wp)
        wp_form.addRow("Custom Image:", wp_file_row)

        layout.addWidget(wp_group)

        # Glassmorphism & Translucency Group
        glass_group = QGroupBox("Frosted Glass & Translucency")
        glass_form = QFormLayout(glass_group)

        # Opacity Slider
        op_row = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 100)
        self.lbl_opacity_val = QLabel("62%")
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        op_row.addWidget(self.slider_opacity)
        op_row.addWidget(self.lbl_opacity_val)
        glass_form.addRow("Card Opacity:", op_row)

        # Blur Slider
        blur_row = QHBoxLayout()
        self.slider_blur = QSlider(Qt.Orientation.Horizontal)
        self.slider_blur.setRange(0, 60)
        self.lbl_blur_val = QLabel("32 px")
        self.slider_blur.valueChanged.connect(lambda v: self.lbl_blur_val.setText(f"{v} px"))
        blur_row.addWidget(self.slider_blur)
        blur_row.addWidget(self.lbl_blur_val)
        glass_form.addRow("Blur Intensity:", blur_row)

        # Card Tint Color
        tint_row = QHBoxLayout()
        self.btn_tint_color = QPushButton()
        self.btn_tint_color.setFixedSize(60, 26)
        self.btn_tint_color.clicked.connect(self.on_pick_tint_color)
        self.lbl_tint_hex = QLabel("#080c14")
        tint_row.addWidget(self.btn_tint_color)
        tint_row.addWidget(self.lbl_tint_hex)
        tint_row.addStretch()
        glass_form.addRow("Card Tint Color:", tint_row)

        layout.addWidget(glass_group)

        # Card Sizing & Positioning Group
        size_group = QGroupBox("Card Sizing & Screen Margins")
        size_form = QFormLayout(size_group)

        # Width Percent
        w_row = QHBoxLayout()
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(50, 98)
        self.lbl_width_val = QLabel("82%")
        self.slider_width.valueChanged.connect(lambda v: self.lbl_width_val.setText(f"{v}%"))
        w_row.addWidget(self.slider_width)
        w_row.addWidget(self.lbl_width_val)
        size_form.addRow("Width (% of screen):", w_row)

        # Height Percent
        h_row = QHBoxLayout()
        self.slider_height = QSlider(Qt.Orientation.Horizontal)
        self.slider_height.setRange(50, 95)
        self.lbl_height_val = QLabel("74%")
        self.slider_height.valueChanged.connect(lambda v: self.lbl_height_val.setText(f"{v}%"))
        h_row.addWidget(self.slider_height)
        h_row.addWidget(self.lbl_height_val)
        size_form.addRow("Height (% of screen):", h_row)

        # Position
        self.combo_pos = QComboBox()
        self.combo_pos.addItems(["center", "top", "bottom"])
        size_form.addRow("Screen Position:", self.combo_pos)

        layout.addWidget(size_group)
        layout.addStretch()

    # ================= TAB 2: GRID & TIMEZONES =================
    def setup_grid_tab(self):
        layout = QVBoxLayout(self.tab_grid)
        layout.setSpacing(14)

        # Weekly Schedule Group
        week_group = QGroupBox("Weekly Schedule Layout")
        week_form = QFormLayout(week_group)

        self.combo_view_mode = QComboBox()
        self.combo_view_mode.addItems(["Weekly Grid (Time Blocks)", "Monthly Calendar (Full Month)"])
        week_form.addRow("Calendar View Mode:", self.combo_view_mode)

        self.combo_start_day = QComboBox()
        self.combo_start_day.addItems(["Sunday (Standard)", "Monday", "Today"])
        week_form.addRow("Start Week On:", self.combo_start_day)

        self.combo_time_fmt = QComboBox()
        self.combo_time_fmt.addItems(["12-hour (AM/PM)", "24-hour"])
        week_form.addRow("Time Format:", self.combo_time_fmt)

        hours_row = QHBoxLayout()
        self.spin_start_h = QSpinBox()
        self.spin_start_h.setRange(0, 23)
        self.spin_end_h = QSpinBox()
        self.spin_end_h.setRange(1, 24)
        hours_row.addWidget(QLabel("From:"))
        hours_row.addWidget(self.spin_start_h)
        hours_row.addWidget(QLabel("To:"))
        hours_row.addWidget(self.spin_end_h)
        hours_row.addStretch()
        week_form.addRow("Visible Grid Hours:", hours_row)

        layout.addWidget(week_group)

        # Dual Timezones Group
        tz_group = QGroupBox("Dual Timezone Columns (Left Gutter)")
        tz_form = QFormLayout(tz_group)

        tz1_row = QHBoxLayout()
        self.txt_primary_tz = QLineEdit("America/Denver")
        self.txt_primary_lbl = QLineEdit("MDT")
        self.txt_primary_lbl.setFixedWidth(80)
        tz1_row.addWidget(self.txt_primary_tz)
        tz1_row.addWidget(QLabel("Label:"))
        tz1_row.addWidget(self.txt_primary_lbl)
        tz_form.addRow("Primary Timezone:", tz1_row)

        tz2_row = QHBoxLayout()
        self.txt_secondary_tz = QLineEdit("America/Anchorage")
        self.txt_secondary_lbl = QLineEdit("AKDT")
        self.txt_secondary_lbl.setFixedWidth(80)
        tz2_row.addWidget(self.txt_secondary_tz)
        tz2_row.addWidget(QLabel("Label:"))
        tz2_row.addWidget(self.txt_secondary_lbl)
        tz_form.addRow("Secondary Timezone:", tz2_row)

        hint = QLabel("<i>Common timezones: America/Denver, America/Anchorage, America/New_York, America/Chicago, America/Los_Angeles, UTC</i>")
        hint.setStyleSheet("color: #64748b; font-size: 11px;")
        tz_form.addRow(hint)

        layout.addWidget(tz_group)
        layout.addStretch()

    # ================= TAB 3: CALENDARS =================
    def setup_calendars_tab(self):
        layout = QVBoxLayout(self.tab_calendars)
        layout.setSpacing(10)

        info = QLabel("Add public Google Calendar .ics links, secret iCal URLs, Outlook links, or local .ics files.")
        info.setStyleSheet("color: #94a3b8;")
        layout.addWidget(info)

        # Table of Calendars
        self.table_cals = QTableWidget(0, 4)
        self.table_cals.setHorizontalHeaderLabels(["Enabled", "Color", "Calendar Name", "iCal URL or File Path"])
        self.table_cals.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cals.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cals.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cals.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_cals.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_cals)

        # Table Buttons
        tbl_btn_row = QHBoxLayout()
        self.btn_add_cal = QPushButton("+ Add Calendar")
        self.btn_add_cal.clicked.connect(self.on_add_calendar_row)
        tbl_btn_row.addWidget(self.btn_add_cal)

        self.btn_remove_cal = QPushButton("- Remove Selected")
        self.btn_remove_cal.clicked.connect(self.on_remove_calendar_row)
        tbl_btn_row.addWidget(self.btn_remove_cal)

        tbl_btn_row.addStretch()

        self.btn_browse_ics = QPushButton("Browse Local .ics File...")
        self.btn_browse_ics.clicked.connect(self.on_browse_local_ics)
        tbl_btn_row.addWidget(self.btn_browse_ics)

        layout.addLayout(tbl_btn_row)

    # ================= TAB 4: SYSTEM & SYNC =================
    def setup_system_tab(self):
        layout = QVBoxLayout(self.tab_system)
        layout.setSpacing(14)

        sync_group = QGroupBox("Background Auto-Sync (systemd user timer)")
        sync_form = QFormLayout(sync_group)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 180)
        self.spin_interval.setValue(15)
        self.spin_interval.setSuffix(" minutes")
        sync_form.addRow("Refresh Interval:", self.spin_interval)

        self.lbl_timer_status = QLabel("Timer status: Checking...")
        sync_form.addRow(self.lbl_timer_status)

        btn_row = QHBoxLayout()
        self.btn_enable_timer = QPushButton("Enable / Reinstall Background Timer")
        self.btn_enable_timer.clicked.connect(self.on_reinstall_timer)
        btn_row.addWidget(self.btn_enable_timer)

        self.btn_disable_timer = QPushButton("Disable Background Timer")
        self.btn_disable_timer.clicked.connect(self.on_disable_timer)
        btn_row.addWidget(self.btn_disable_timer)

        sync_form.addRow(btn_row)
        layout.addWidget(sync_group)

        # Update status check
        self.check_systemd_status()

        layout.addStretch()

    # ================= LOAD CONFIG TO UI =================
    def load_values_into_ui(self):
        wp = self.config.get("wallpaper", {})
        layout = self.config.get("layout", {})
        tz = self.config.get("timezones", {})
        grid = self.config.get("grid_hours", {})

        # Wallpaper
        source = wp.get("source", "auto")
        if source == "auto":
            self.chk_auto_wp.setChecked(True)
            self.txt_custom_wp.setEnabled(False)
            self.btn_browse_wp.setEnabled(False)
            detected = get_current_plasma_wallpaper() or ""
            self.txt_custom_wp.setText(detected)
        else:
            self.chk_auto_wp.setChecked(False)
            self.txt_custom_wp.setEnabled(True)
            self.btn_browse_wp.setEnabled(True)
            self.txt_custom_wp.setText(source)

        # Opacity & Blur
        op_val = int(wp.get("card_opacity", 0.62) * 100)
        self.slider_opacity.setValue(op_val)
        self.lbl_opacity_val.setText(f"{op_val}%")

        blur_val = wp.get("blur_radius", 32)
        self.slider_blur.setValue(blur_val)
        self.lbl_blur_val.setText(f"{blur_val} px")

        # Tint Color
        tint = wp.get("card_tint", "#080c14")
        self.set_tint_button_color(tint)

        # Sizing
        w_val = layout.get("width_percent", 82)
        self.slider_width.setValue(w_val)
        self.lbl_width_val.setText(f"{w_val}%")

        h_val = layout.get("height_percent", 74)
        self.slider_height.setValue(h_val)
        self.lbl_height_val.setText(f"{h_val}%")

        pos = layout.get("position", "center")
        idx = self.combo_pos.findText(pos)
        if idx >= 0:
            self.combo_pos.setCurrentIndex(idx)

        # Grid
        view_mode = layout.get("view", "week").lower()
        self.combo_view_mode.setCurrentIndex(0 if view_mode == "week" else 1)

        start_d = layout.get("start_day", "sunday").lower()
        if start_d == "sunday":
            self.combo_start_day.setCurrentIndex(0)
        elif start_d == "monday":
            self.combo_start_day.setCurrentIndex(1)
        else:
            self.combo_start_day.setCurrentIndex(2)

        time_fmt = layout.get("time_format", "12h").lower()
        self.combo_time_fmt.setCurrentIndex(0 if time_fmt == "12h" else 1)

        self.spin_start_h.setValue(grid.get("start", 7))
        self.spin_end_h.setValue(grid.get("end", 21))

        # Timezones
        self.txt_primary_tz.setText(tz.get("primary", "America/Denver"))
        self.txt_primary_lbl.setText(tz.get("primary_label", "MDT"))
        self.txt_secondary_tz.setText(tz.get("secondary", "America/Anchorage"))
        self.txt_secondary_lbl.setText(tz.get("secondary_label", "AKDT"))

        # Calendars
        self.populate_calendars_table()

    def populate_calendars_table(self):
        cals = self.config.get("calendars", [])
        self.table_cals.setRowCount(0)
        for cal in cals:
            row = self.table_cals.rowCount()
            self.table_cals.insertRow(row)

            # Checkbox: Enabled
            chk = QCheckBox()
            chk.setChecked(cal.get("enabled", True))
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.addWidget(chk)
            chk_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            self.table_cals.setCellWidget(row, 0, chk_widget)

            # Color button
            btn_col = QPushButton()
            btn_col.setFixedSize(36, 22)
            col_hex = cal.get("color", "#38bdf8")
            btn_col.setStyleSheet(f"background-color: {col_hex}; border: 1px solid #ffffff; border-radius: 4px;")
            btn_col.setProperty("color_hex", col_hex)
            btn_col.clicked.connect(lambda _, b=btn_col: self.on_pick_calendar_color(b))

            col_widget = QWidget()
            col_lay = QHBoxLayout(col_widget)
            col_lay.addWidget(btn_col)
            col_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_lay.setContentsMargins(0, 0, 0, 0)
            self.table_cals.setCellWidget(row, 1, col_widget)

            # Name
            item_name = QTableWidgetItem(cal.get("name", "Calendar"))
            self.table_cals.setItem(row, 2, item_name)

            # URL / Path
            src = cal.get("url") or cal.get("path") or ""
            item_src = QTableWidgetItem(src)
            self.table_cals.setItem(row, 3, item_src)

    # ================= SAVE UI TO CONFIG =================
    def save_ui_to_config(self):
        # Wallpaper
        wp = self.config.setdefault("wallpaper", {})
        if self.chk_auto_wp.isChecked():
            wp["source"] = "auto"
        else:
            wp["source"] = self.txt_custom_wp.text().strip()

        wp["card_opacity"] = round(self.slider_opacity.value() / 100.0, 2)
        wp["blur_radius"] = self.slider_blur.value()
        wp["card_tint"] = self.lbl_tint_hex.text()

        # Layout
        lay = self.config.setdefault("layout", {})
        lay["view"] = "week" if self.combo_view_mode.currentIndex() == 0 else "month"
        lay["width_percent"] = self.slider_width.value()
        lay["height_percent"] = self.slider_height.value()
        lay["position"] = self.combo_pos.currentText()

        start_map = {0: "sunday", 1: "monday", 2: "today"}
        lay["start_day"] = start_map.get(self.combo_start_day.currentIndex(), "sunday")
        lay["time_format"] = "12h" if self.combo_time_fmt.currentIndex() == 0 else "24h"

        # Timezones
        tz = self.config.setdefault("timezones", {})
        tz["primary"] = self.txt_primary_tz.text().strip()
        tz["primary_label"] = self.txt_primary_lbl.text().strip()
        tz["secondary"] = self.txt_secondary_tz.text().strip()
        tz["secondary_label"] = self.txt_secondary_lbl.text().strip()

        # Grid Hours
        grid = self.config.setdefault("grid_hours", {})
        grid["start"] = self.spin_start_h.value()
        grid["end"] = self.spin_end_h.value()

        # Calendars Table
        cals = []
        for row in range(self.table_cals.rowCount()):
            chk_widget = self.table_cals.cellWidget(row, 0)
            chk = chk_widget.findChild(QCheckBox) if chk_widget else None
            enabled = chk.isChecked() if chk else True

            col_widget = self.table_cals.cellWidget(row, 1)
            btn_col = col_widget.findChild(QPushButton) if col_widget else None
            color = btn_col.property("color_hex") if btn_col else "#38bdf8"

            item_name = self.table_cals.item(row, 2)
            name = item_name.text().strip() if item_name else "Calendar"

            item_src = self.table_cals.item(row, 3)
            src = item_src.text().strip() if item_src else ""

            entry = {
                "name": name,
                "color": color,
                "enabled": enabled,
            }
            if src.startswith("http://") or src.startswith("https://") or src.startswith("webcal://"):
                entry["url"] = src
            else:
                entry["path"] = src

            cals.append(entry)

        self.config["calendars"] = cals
        save_config(self.config)

    # ================= EVENTS & HANDLERS =================
    def on_auto_wp_toggled(self, checked):
        self.txt_custom_wp.setEnabled(not checked)
        self.btn_browse_wp.setEnabled(not checked)
        if checked:
            detected = get_current_plasma_wallpaper() or ""
            self.txt_custom_wp.setText(detected)

    def on_browse_wallpaper(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Wallpaper Image", os.path.expanduser("~"), "Images (*.png *.jpg *.jpeg *.webp)")
        if fpath:
            self.txt_custom_wp.setText(fpath)

    def set_tint_button_color(self, hex_color):
        self.lbl_tint_hex.setText(hex_color)
        self.btn_tint_color.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #ffffff; border-radius: 4px;")

    def on_pick_tint_color(self):
        cur = QColor(self.lbl_tint_hex.text())
        chosen = QColorDialog.getColor(cur, self, "Pick Card Tint Color")
        if chosen.isValid():
            self.set_tint_button_color(chosen.name())

    def on_pick_calendar_color(self, button):
        cur = QColor(button.property("color_hex") or "#38bdf8")
        chosen = QColorDialog.getColor(cur, self, "Pick Calendar Accent Color")
        if chosen.isValid():
            hex_val = chosen.name()
            button.setProperty("color_hex", hex_val)
            button.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #ffffff; border-radius: 4px;")

    def on_add_calendar_row(self):
        row = self.table_cals.rowCount()
        self.table_cals.insertRow(row)

        chk = QCheckBox()
        chk.setChecked(True)
        chk_widget = QWidget()
        lay = QHBoxLayout(chk_widget)
        lay.addWidget(chk)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(0, 0, 0, 0)
        self.table_cals.setCellWidget(row, 0, chk_widget)

        btn_col = QPushButton()
        btn_col.setFixedSize(36, 22)
        btn_col.setStyleSheet("background-color: #38bdf8; border: 1px solid #ffffff; border-radius: 4px;")
        btn_col.setProperty("color_hex", "#38bdf8")
        btn_col.clicked.connect(lambda _, b=btn_col: self.on_pick_calendar_color(b))
        col_widget = QWidget()
        lay2 = QHBoxLayout(col_widget)
        lay2.addWidget(btn_col)
        lay2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay2.setContentsMargins(0, 0, 0, 0)
        self.table_cals.setCellWidget(row, 1, col_widget)

        self.table_cals.setItem(row, 2, QTableWidgetItem("New Calendar"))
        self.table_cals.setItem(row, 3, QTableWidgetItem(""))

    def on_remove_calendar_row(self):
        sel = self.table_cals.selectedIndexes()
        if sel:
            row = sel[0].row()
            self.table_cals.removeRow(row)

    def on_browse_local_ics(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Local .ics File", os.path.expanduser("~"), "iCalendar (*.ics)")
        if fpath:
            # Check if row is selected
            sel = self.table_cals.selectedIndexes()
            if sel:
                row = sel[0].row()
                self.table_cals.setItem(row, 3, QTableWidgetItem(fpath))
            else:
                self.on_add_calendar_row()
                last_row = self.table_cals.rowCount() - 1
                self.table_cals.setItem(last_row, 3, QTableWidgetItem(fpath))

    def on_save_clicked(self):
        self.save_ui_to_config()
        self.status_bar.showMessage("✓ Settings saved to config.yaml", 4000)

    def on_apply_clicked(self):
        self.save_ui_to_config()
        self.status_bar.showMessage("Rendering weekly wallpaper & syncing across desktops...")
        self.btn_apply.setEnabled(False)

        self.worker = WallpaperUpdateWorker()
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self, success, msg):
        self.btn_apply.setEnabled(True)
        if success:
            self.status_bar.showMessage(f"✓ {msg}", 6000)
        else:
            self.status_bar.showMessage(f"⚠ {msg}", 6000)
            QMessageBox.warning(self, "Update Result", msg)

    def check_systemd_status(self):
        try:
            res = subprocess.run(["systemctl", "--user", "is-active", "calwallpaper.timer"], capture_output=True, text=True)
            if res.returncode == 0:
                self.lbl_timer_status.setText("● Timer status: <b>Active (Running every 15 min)</b>")
                self.lbl_timer_status.setStyleSheet("color: #22c55e;")
            else:
                self.lbl_timer_status.setText("○ Timer status: Inactive")
                self.lbl_timer_status.setStyleSheet("color: #94a3b8;")
        except Exception:
            self.lbl_timer_status.setText("Timer status: Unknown")

    def on_reinstall_timer(self):
        val = self.spin_interval.value()
        try:
            subprocess.run(["calwallpaper", "install-service", "--interval", f"{val}min"], check=True)
            self.check_systemd_status()
            QMessageBox.information(self, "Timer Updated", f"Timer set to refresh every {val} minutes.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update timer: {e}")

    def on_disable_timer(self):
        try:
            subprocess.run(["calwallpaper", "uninstall-service"], check=True)
            self.check_systemd_status()
            QMessageBox.information(self, "Timer Disabled", "Background timer has been disabled.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to disable timer: {e}")


def launch_gui():
    app = QApplication(sys.argv)
    app.setApplicationName("Calendar Wallpaper Settings")
    app.setStyle("Breeze")
    win = CalWallpaperSettingsWindow()
    win.show()
    sys.exit(app.exec())
