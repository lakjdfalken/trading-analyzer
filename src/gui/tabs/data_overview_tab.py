from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QTabWidget, QFrame)
from PyQt6.QtCore import Qt
import pandas as pd
import logging
import re
from settings import MARKET_POINT_MULTIPLIERS, OVERVIEW_SETTINGS, MARKET_MAPPINGS
from datetime import datetime

logger = logging.getLogger(__name__)

class DataOverviewTab(QWidget):
    def __init__(self, data_manager, settings_tab, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.settings_tab = settings_tab
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)

        # Create selection controls
        self.create_selection_frame(main_layout)

        # Create data display area
        self.create_data_display(main_layout)

        # Set the layout
        self.setLayout(main_layout)
        # Populate year list and initial data immediately
        try:
            self.refresh_data()
        except Exception:
            logger.exception("Failed to refresh DataOverviewTab during init")

    def create_selection_frame(self, parent_layout):
        """Create the selection controls (simplified: only Year selector)"""
        selection_frame = QWidget()
        selection_layout = QHBoxLayout(selection_frame)

        # Year selection
        selection_layout.addWidget(QLabel("Year:"))
        self.year_combo = QComboBox()
        self.year_combo.currentTextChanged.connect(self.update_data)
        selection_layout.addWidget(self.year_combo)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        selection_layout.addWidget(refresh_button)

        # Add stretch to push controls to the left
        selection_layout.addStretch()

        parent_layout.addWidget(selection_frame)

    def create_data_display(self, parent_layout):
        """Create the data display area: single pane with summary + monthly/daily tables"""
        self.data_display = QWidget()
        self.data_layout = QVBoxLayout(self.data_display)

        # Summary labels
        summary_frame = QFrame()
        summary_layout = QHBoxLayout(summary_frame)

        # Totals (single-line labels: "Label: value")
        totals_box = QVBoxLayout()
        self.total_pl_label = QLabel("Total P/L: 0.00")
        totals_box.addWidget(self.total_pl_label)
        self.total_points_label = QLabel("Total Points: 0")
        totals_box.addWidget(self.total_points_label)
        self.total_balance_label = QLabel("Total Balance: 0.00")
        totals_box.addWidget(self.total_balance_label)

        summary_layout.addLayout(totals_box)

        # Averages
        avg_box = QVBoxLayout()
        self.avg_pl_month_label = QLabel("Avg P/L per Month: 0.00")
        avg_box.addWidget(self.avg_pl_month_label)
        self.avg_pl_day_label = QLabel("Avg P/L per Day: 0.00")
        avg_box.addWidget(self.avg_pl_day_label)
        self.avg_pts_month_label = QLabel("Avg Points per Month: 0")
        avg_box.addWidget(self.avg_pts_month_label)
        self.avg_pts_day_label = QLabel("Avg Points per Day: 0")
        avg_box.addWidget(self.avg_pts_day_label)

        summary_layout.addLayout(avg_box)
        self.data_layout.addWidget(summary_frame)

        # Monthly breakdown table
        monthly_frame = QFrame()
        monthly_layout = QVBoxLayout(monthly_frame)
        monthly_layout.addWidget(QLabel("Monthly breakdown (Month, Total P/L, Points)"))
        self.monthly_table = QTableWidget()
        self.monthly_table.setColumnCount(3)
        self.monthly_table.setHorizontalHeaderLabels(['Month', 'Total P/L', 'Points'])
        self.monthly_table.horizontalHeader().setStretchLastSection(True)
        monthly_layout.addWidget(self.monthly_table)
        self.data_layout.addWidget(monthly_frame)

        # Daily breakdown table (top days by P/L)
        daily_frame = QFrame()
        daily_layout = QVBoxLayout(daily_frame)
        daily_layout.addWidget(QLabel("Daily breakdown (Top days by Total P/L)"))
        self.daily_table = QTableWidget()
        self.daily_table.setColumnCount(3)
        self.daily_table.setHorizontalHeaderLabels(['Date', 'Total P/L', 'Points'])
        self.daily_table.horizontalHeader().setStretchLastSection(True)
        daily_layout.addWidget(self.daily_table)
        self.data_layout.addWidget(daily_frame)

        # Add stretch to push content to the top
        self.data_layout.addStretch()
        parent_layout.addWidget(self.data_display)

    def update_year_combo(self, df):
        """Update the year combo box with available years (All + actual years)"""
        if df is None or df.empty:
            self.year_combo.clear()
            self.year_combo.addItem(OVERVIEW_SETTINGS.get('year_all_label', 'All Years'))
            return

        try:
            # DataManager should already provide normalized 'Transaction Date'
            if 'Transaction Date' not in df.columns:
                # try to normalize if DataManager didn't
                try:
                    df = df.copy()
                    df['Transaction Date'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
                except Exception:
                    pass

            years = sorted(df['Transaction Date'].dt.year.dropna().unique().tolist(), reverse=True)
            self.year_combo.clear()
            all_label = OVERVIEW_SETTINGS.get('year_all_label', 'All Years')
            self.year_combo.addItem(all_label)
            year_items = [str(int(y)) for y in years if pd.notna(y)]
            self.year_combo.addItems(year_items)
            # default to current year if present, otherwise leave "All Years" selected
            try:
                current_year = str(datetime.now().year)
                if current_year in year_items:
                    self.year_combo.setCurrentText(current_year)
                else:
                    self.year_combo.setCurrentText(all_label)
            except Exception:
                # fallback: do nothing
                pass
        except Exception as e:
            logger.error(f"Error updating year combo: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def refresh_data(self):
        """Refresh data (rebuild year list and refresh stats)"""
        df = self.data_manager.get_data()
        self.update_year_combo(df)
        self.update_data()

    def update_data(self):
        """Update the statistics display for the selected year (or all)"""
        try:
            # Debug: show incoming dataframe shape & columns so we can diagnose empty views
            df_preview = None
            try:
                df_preview = self.data_manager.get_data()
                logger.debug("DataOverviewTab.update_data: raw df shape=%s columns=%s", getattr(df_preview, 'shape', None), list(getattr(df_preview, 'columns', [])))
            except Exception:
                logger.debug("DataOverviewTab.update_data: couldn't fetch preview df for debug")

             # Determine selected year
            year_text = self.year_combo.currentText()
            year_all_label = OVERVIEW_SETTINGS.get('year_all_label', 'All Years')
            df = self.data_manager.get_data()
            logger.debug("DataOverviewTab.update_data: selected year=%s, df rows=%s", year_text, len(df) if df is not None else 'None')
            if df is None or df.empty:
                 # clear tables/labels (single-line format)
                 self.total_pl_label.setText("Total P/L: 0.00")
                 self.total_points_label.setText("Total Points: 0")
                 self.total_balance_label.setText("Total Balance: 0.00")
                 self.avg_pl_month_label.setText("Avg P/L per Month: 0.00")
                 self.avg_pl_day_label.setText("Avg P/L per Day: 0.00")
                 self.avg_pts_month_label.setText("Avg Points per Month: 0")
                 self.avg_pts_day_label.setText("Avg Points per Day: 0")
                 self.monthly_table.setRowCount(0)
                 self.daily_table.setRowCount(0)
                 return

            # Ensure Transaction Date and P/L exist
            if 'Transaction Date' not in df.columns:
                try:
                    df = df.copy()
                    df['Transaction Date'] = pd.to_datetime(df['date'] if 'date' in df.columns else df.iloc[:, 0], errors='coerce')
                except Exception:
                    logger.warning("No Transaction Date column found; aborting overview update")
                    return

            if 'P/L' not in df.columns:
                # try to use numeric alias from DataManager normalisation
                for alias in ('_pl_numeric', 'pl_numeric', '_pl'):
                    if alias in df.columns:
                        df['P/L'] = df[alias]
                        break
            if 'P/L' not in df.columns:
                logger.warning("Missing 'P/L' column; cannot compute metrics")
                return

            # Filter by year if not "All Years"
            if year_text and year_text != year_all_label:
                try:
                    year_int = int(year_text)
                    df = df[df['Transaction Date'].dt.year == year_int]
                    logger.debug("DataOverviewTab.update_data: after year filter rows=%s", len(df))
                except Exception:
                    # invalid selection -> show nothing
                    return

            if df.empty:
                # clear displays (single-line format)
                self.total_pl_label.setText("Total P/L: 0.00")
                self.total_points_label.setText("Total Points: 0")
                self.total_balance_label.setText("Total Balance: 0.00")
                self.monthly_table.setRowCount(0)
                self.daily_table.setRowCount(0)
                return

            # Use trading-only data for P/L and points so funding/deposits don't skew results
            trading_df = self.data_manager.get_trading_df(df)
            # Debug: log trading subset shape and a quick summary so we can see why numbers are missing
            try:
                logger.debug("Trading DF rows=%d columns=%s", len(trading_df), list(trading_df.columns))
                logger.debug("Action value counts: %s", trading_df.get('Action', trading_df.get('action', pd.Series())).astype(str).value_counts().to_dict())
                logger.debug("Has _pl_numeric: %s", '_pl_numeric' in trading_df.columns)
                if '_pl_numeric' in trading_df.columns:
                    logger.debug("Trading _pl_numeric sum=%s mean=%s", trading_df['_pl_numeric'].sum(), trading_df['_pl_numeric'].mean())
            except Exception:
                logger.exception("Error while logging trading_df diagnostic info")

            if trading_df is None or trading_df.empty:
                logger.warning("Trading DataFrame is empty after filtering — overview will show zeros for trading metrics")
                total_pl = 0.0
                total_points = 0
            else:
                # Use trading_df consistently when computing totals/points
                total_pl = float(self.data_manager.get_trading_pl_total(trading_df))
                total_points = int(self.data_manager.calculate_points(trading_df))

            # Base currency and total balance
            base_currency = None
            try:
                base_currency = self.settings_tab.get_base_currency()
            except Exception:
                base_currency = None
            exchange_rates = {}
            if hasattr(self.settings_tab, "get_exchange_rates"):
                exchange_rates = self.settings_tab.get_exchange_rates()
            try:
                total_balance = self.data_manager.calculate_total_balance(df, base_currency, exchange_rates)
            except Exception:
                total_balance = 0.0

            # Monthly aggregates (trading-only P/L)
            if trading_df is None or trading_df.empty:
                monthly_pl = pd.Series(dtype=float)
            else:
                df_month = trading_df.set_index('Transaction Date')
                monthly_pl = df_month['_pl_numeric'].resample('MS').sum().fillna(0)

            # Points per month: calculate on per-month subset via DataManager to reuse central logic
            monthly_points = []
            monthly_index = monthly_pl.index
            for ts in monthly_index:
                # build explicit [month_start, next_month) range to avoid Period freq issues
                month_start = pd.Timestamp(year=ts.year, month=ts.month, day=1)
                next_month = month_start + pd.DateOffset(months=1)
                month_df = df[(df['Transaction Date'] >= month_start) & (df['Transaction Date'] < next_month)]
                # use trading-only subset for points calculation
                month_trading = self.data_manager.get_trading_df(month_df)
                pts = int(self.data_manager.calculate_points(month_trading))
                monthly_points.append(pts)
            if monthly_points:
                monthly_points_series = pd.Series(monthly_points, index=monthly_index)
            else:
                monthly_points_series = pd.Series(dtype=float)

            # Daily aggregates (total P/L per day)
            if trading_df is None or trading_df.empty:
                daily_pl = pd.Series(dtype=float)
            else:
                # reuse df_month if available; create if not
                if 'df_month' not in locals():
                    df_month = trading_df.set_index('Transaction Date')
                daily_pl = df_month['_pl_numeric'].resample('D').sum().fillna(0)

            # Averages
            avg_pl_per_month = float(monthly_pl.mean()) if not monthly_pl.empty else 0.0
            avg_pl_per_day = float(daily_pl.mean()) if not daily_pl.empty else 0.0
            avg_pts_per_month = float(monthly_points_series.mean()) if not monthly_points_series.empty else 0.0

            # Points per day: compute per-day via DataManager (delegated)
            daily_points = []
            daily_index = daily_pl.index
            for day_ts in daily_index:
                day_start = pd.Timestamp(year=day_ts.year, month=day_ts.month, day=day_ts.day)
                next_day = day_start + pd.Timedelta(days=1)
                day_df = df[(df['Transaction Date'] >= day_start) & (df['Transaction Date'] < next_day)]
                day_trading = self.data_manager.get_trading_df(day_df)
                pts = int(self.data_manager.calculate_points(day_trading))
                daily_points.append(pts)
            if daily_points:
                daily_points_series = pd.Series(daily_points, index=daily_index)
            else:
                daily_points_series = pd.Series(dtype=float)
            avg_pts_per_day = float(daily_points_series.mean()) if not daily_points_series.empty else 0.0

            # update single-line labels
            self.total_pl_label.setText(f"Total P/L: {total_pl:.2f}")
            self.total_points_label.setText(f"Total Points: {total_points}")
            if base_currency:
                self.total_balance_label.setText(f"Total Balance: {total_balance:.2f} {base_currency}")
            else:
                self.total_balance_label.setText(f"Total Balance: {total_balance:.2f}")

            self.avg_pl_month_label.setText(f"Avg P/L per Month: {avg_pl_per_month:.2f}")
            self.avg_pl_day_label.setText(f"Avg P/L per Day: {avg_pl_per_day:.2f}")
            self.avg_pts_month_label.setText(f"Avg Points per Month: {avg_pts_per_month:.1f}")
            self.avg_pts_day_label.setText(f"Avg Points per Day: {avg_pts_per_day:.1f}")

            # Populate monthly table
            self.monthly_table.setRowCount(0)
            for idx, ts in enumerate(monthly_pl.index):
                month_label = ts.strftime("%Y-%m")
                pl_val = monthly_pl.iloc[idx]
                pts_val = int(monthly_points_series.iloc[idx]) if idx < len(monthly_points_series) else 0
                row = self.monthly_table.rowCount()
                self.monthly_table.insertRow(row)
                self.monthly_table.setItem(row, 0, QTableWidgetItem(month_label))
                self.monthly_table.setItem(row, 1, QTableWidgetItem(f"{pl_val:.2f}"))
                self.monthly_table.setItem(row, 2, QTableWidgetItem(str(pts_val)))

            # Populate daily table (show top days by P/L)
            daily_df = pd.DataFrame({
                'date': daily_pl.index,
                'pl': daily_pl.values,
                'points': daily_points_series.values
            })
            top_daily = daily_df.sort_values('pl', ascending=False).head(31)
            self.daily_table.setRowCount(0)
            for _, r in top_daily.iterrows():
                row = self.daily_table.rowCount()
                self.daily_table.insertRow(row)
                self.daily_table.setItem(row, 0, QTableWidgetItem(r['date'].strftime("%Y-%m-%d")))
                self.daily_table.setItem(row, 1, QTableWidgetItem(f"{r['pl']:.2f}"))
                self.daily_table.setItem(row, 2, QTableWidgetItem(str(int(r['points']))))

        except Exception as e:
            logger.error(f"Error in update_data: {e}")
            import traceback
            logger.error(traceback.format_exc())