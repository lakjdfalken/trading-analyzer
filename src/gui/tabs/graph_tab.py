from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
                           QComboBox, QPushButton, QLineEdit, QTreeWidget, 
                           QTreeWidgetItem, QSizePolicy, QMessageBox, QApplication,
                           QSplitter)
from PyQt6.QtCore import Qt
import logging
import sqlite3
from datetime import datetime
from settings import BROKERS, VALID_GRAPH_TYPES, UI_SETTINGS
from visualize_data import create_visualization_figure
from chart_types.points import create_points_view
from chart_types.pl import (
    create_balance_history,
    create_daily_pl,
    create_daily_pl_vs_trades,
    create_relative_balance_history,
    create_market_pl_chart,
    create_win_loss_analysis,
)
# NOTE: normalize_trading_df is imported locally inside the handler to avoid circular-import issues
import traceback
import pandas as pd

logger = logging.getLogger(__name__)

class GraphTab(QWidget):
    def __init__(self, data_manager, visualization_manager, settings_manager):
        super().__init__()
        self.data_manager = data_manager
        self.visualization_manager = visualization_manager
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_accounts()  # Ensure accounts are loaded after UI setup

    def setup_ui(self):
        """Setup the graph tab UI using a QSplitter so the left column is resizable."""
        layout = QHBoxLayout(self)

        # Create a horizontal splitter so the selection column and graph area are resizable
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(8)

        # Create selection frame (create_selection_frame will return the widget when called without args)
        try:
            sel_frame = self.create_selection_frame()  # returns the selection QWidget
        except TypeError:
            # fallback for older create_selection_frame signature that expects a layout
            # create a temporary container and pass its layout
            sel_frame = QFrame()
            sel_layout = QVBoxLayout(sel_frame)
            sel_layout.setContentsMargins(0, 0, 0, 0)
            self.create_selection_frame(sel_layout)

        sel_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sel_frame.setMinimumWidth(UI_SETTINGS.get('graph_selection_width', 260))

        # Create graph display area
        self.graph_display_frame = QFrame()
        self.graph_display_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Add both panes to splitter and set initial sizes
        splitter.addWidget(sel_frame)
        splitter.addWidget(self.graph_display_frame)
        splitter.setSizes([UI_SETTINGS.get('graph_selection_width', 260), 1000])

        layout.addWidget(splitter)

    def create_selection_frame(self, parent_layout=None):
        """Create the left selection column. If parent_layout is provided it will add the frame to it.
        Otherwise the created selection frame widget is returned for use (e.g., with a QSplitter)."""
        selection_frame = QFrame()
        selection_layout = QVBoxLayout(selection_frame)
        selection_layout.setContentsMargins(8, 8, 8, 8)
        selection_layout.setSpacing(8)

        # Broker selection
        # Label above broker combo
        selection_layout.addWidget(QLabel("Broker"))
        self.broker_combo = QComboBox()
        self.broker_combo.clear()  # Ensure it's empty before adding items
        # Deduplicate broker display names (case-insensitive, strip whitespace)
        seen = set()
        unique_brokers = []
        for name in BROKERS.values():
            normalized = name.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_brokers.append(name.strip())
        self.broker_combo.addItems(['All'] + unique_brokers)
        self.broker_combo.setCurrentText('Trade Nation')
        selection_layout.addWidget(self.broker_combo)

        # Account filter
        self.create_account_filter(selection_layout)

        # Date range selection
        selection_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QLineEdit()
        selection_layout.addWidget(self.start_date)

        selection_layout.addWidget(QLabel("End Date:"))
        self.end_date = QLineEdit()
        selection_layout.addWidget(self.end_date)

        # Quick selection buttons
        self.create_quick_select_buttons(selection_layout)

        # Graph type selection
        selection_layout.addWidget(QLabel("Select Graph Type:"))
        self.graph_list = QTreeWidget()
        self.graph_list.setHeaderLabels(["Graph Types"])
        self.graph_list.setFixedWidth(UI_SETTINGS['graph_list_width'])
        self.graph_list.itemDoubleClicked.connect(self.on_graph_double_click)

        for graph_type in VALID_GRAPH_TYPES:
            item = QTreeWidgetItem([graph_type])
            self.graph_list.addTopLevelItem(item)

        selection_layout.addWidget(self.graph_list)

        # Display button
        display_button = QPushButton("Display Graph")
        display_button.clicked.connect(self.display_selected_graph)
        selection_layout.addWidget(display_button)

        # If caller gave a parent_layout, add selection_frame into it and return None
        if parent_layout is not None:
            parent_layout.addWidget(selection_frame)
            return None
        # Otherwise return the widget so the caller can insert it into a splitter
        return selection_frame

    def create_account_filter(self, parent_layout):
        """Create account filter dropdown"""
        account_frame = QFrame()
        account_layout = QHBoxLayout(account_frame)

        account_label = QLabel("Filter by Account:")
        account_layout.addWidget(account_label)

        self.account_combo = QComboBox()
        self.account_combo.addItem("All Accounts", "all")
        account_layout.addWidget(self.account_combo)

        parent_layout.addWidget(account_frame)

    def load_accounts(self):
        """Load accounts into the combo box"""
        try:
            conn = sqlite3.connect('trading.db')
            accounts_df = pd.read_sql_query("SELECT * FROM accounts", conn)
            conn.close()

            self.account_combo.clear()
            self.account_combo.addItem("All Accounts", "all")

            for _, row in accounts_df.iterrows():
                self.account_combo.addItem(f"{row['account_name']} ({row['account_id']})", row['account_id'])

        except Exception as e:
            logger.error(f"Failed to load accounts: {str(e)}")

    def create_quick_select_buttons(self, parent_layout):
        """Create quick date selection buttons"""
        quick_select_frame = QFrame()
        # allow the quick-select frame to use available horizontal space in the selection column
        quick_select_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        quick_select_layout = QHBoxLayout(quick_select_frame)
        quick_select_layout.setContentsMargins(0, 0, 0, 0)
        quick_select_layout.setSpacing(8)

        # Make buttons expand horizontally so labels are readable
        seven_days_btn = QPushButton("7 Days")
        seven_days_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        seven_days_btn.setMinimumWidth(80)
        seven_days_btn.clicked.connect(lambda: self.set_date_range(7))
        quick_select_layout.addWidget(seven_days_btn)

        thirty_days_btn = QPushButton("30 Days")
        thirty_days_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        thirty_days_btn.setMinimumWidth(90)
        thirty_days_btn.clicked.connect(lambda: self.set_date_range(30))
        quick_select_layout.addWidget(thirty_days_btn)

        all_btn = QPushButton("All")
        all_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        all_btn.setMinimumWidth(60)
        all_btn.clicked.connect(self.reset_date_range)
        quick_select_layout.addWidget(all_btn)

        # ensure buttons fill available width nicely
        quick_select_layout.addStretch()
        parent_layout.addWidget(quick_select_frame)

    def set_date_range(self, days):
        """Set date range for last N days"""
        if self.data_manager.has_data():
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)
            self.start_date.setText(start_date.strftime('%Y-%m-%d'))
            self.end_date.setText(end_date.strftime('%Y-%m-%d'))

    def reset_date_range(self):
        """Clear date range filters"""
        self.start_date.clear()
        self.end_date.clear()

    def on_graph_double_click(self, item, column):
        """Handle double-click on graph type"""
        self.graph_list.setCurrentItem(item)
        self.display_selected_graph()

    def display_selected_graph(self):
        """Display the selected graph"""
        try:
            # Get filtered data
            filtered_data = self.get_filtered_data()
            if filtered_data is None or filtered_data.empty:
                logger.warning("No data available after filtering")
                QMessageBox.warning(self, "Info", "No data available for selected date range")
                return

            # Get selected graph type
            current_item = self.graph_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "Selection", "Please select a graph type")
                return
                
            selection = current_item.text(0)

            # Generate filtered_data earlier in the function
            # Ensure we have a defined account variable for downstream calls (UI may not supply it yet)
            filtered_account = None

            # Backwards-compatibility: some chart modules expect a 'Description' column.
            # If missing, create it from Market/Desc (or as empty string) so older code won't KeyError.
            # DEBUG: log info about the filtered dataframe to locate where 'Description' accesses fail.
            try:
                # Defer import to avoid circular import issues
                try:
                    from chart_types.base import normalize_trading_df
                except Exception as _imp_e:
                    logger.debug("Could not import normalize_trading_df at module-import time: %s", _imp_e)
                    normalize_trading_df = None
                # normalize once for all charts so they all see the same columns/dtypes
                try:
                    if normalize_trading_df:
                        _orig_filtered_data = filtered_data
                        _nd = normalize_trading_df(filtered_data)
                        # Only accept the normalized result when it is a DataFrame.
                        # If normalizer returns None or something else, keep original data.
                        if isinstance(_nd, pd.DataFrame):
                            filtered_data = _nd
                        else:
                            logger.debug("normalize_trading_df returned non-DataFrame; keeping original filtered_data")
                except Exception:
                    logger.exception("normalize_trading_df failed; proceeding with original filtered_data")
                # Sanitize filtered_data so chart callers always receive a DataFrame
                if filtered_data is None:
                    filtered_data = pd.DataFrame()
                elif not isinstance(filtered_data, pd.DataFrame):
                    try:
                        filtered_data = pd.DataFrame(filtered_data)
                    except Exception:
                        logger.exception("Failed to coerce filtered_data to DataFrame; using empty DataFrame")
                        filtered_data = pd.DataFrame()

                logger.debug("Filtered data shape: %s", getattr(filtered_data, "shape", None))
                logger.debug("Filtered data columns: %s", list(getattr(filtered_data, "columns", [])))
                # log dtypes concise
                try:
                    logger.debug("Filtered data dtypes: %s", filtered_data.dtypes.apply(lambda dt: str(dt)).to_dict())
                except Exception:
                    logger.debug("Could not read dtypes for filtered_data")
                # sample a few rows of possible description-like columns
                desc_candidates = [c for c in ('Description', 'Desc', 'Market', 'Instrument', 'Symbol')
                                   if c in getattr(filtered_data, "columns", [])]
                if desc_candidates:
                    sample = filtered_data[desc_candidates].head(5).to_dict('records')
                    logger.debug("Sample of description-like columns (first 5 rows): %s", sample)
                else:
                    # show a tiny sample of the first 3 rows of the entire frame to help debugging
                    try:
                        logger.debug("No description-like columns. Data sample (first 3 rows): %s",
                                     filtered_data.head(3).to_dict('records'))
                    except Exception:
                        logger.debug("Unable to serialize filtered_data sample")
            except Exception:
                logger.exception("Error while logging filtered_data debug info")

            if filtered_data is not None and hasattr(filtered_data, "columns") and "Description" not in filtered_data.columns:
                try:
                    fd = filtered_data.copy()
                    if "Market" in fd.columns:
                        fd["Description"] = fd["Market"].astype(str)
                    elif "Desc" in fd.columns:
                        fd["Description"] = fd["Desc"].astype(str)
                    else:
                        fd["Description"] = ""
                    filtered_data = fd
                except Exception:
                    logger.exception("Failed to synthesize Description column for legacy charts; proceeding without change")
                    # fall through to existing error handling / UI notification

            # P/L visualizations dispatch
            if selection in (
                "Daily P/L",
                "P/L vs Trades",
                "Relative P/L",
                "P/L by Market",
                "Win/Loss Analysis",
            ):
                try:
                    if selection == "Daily P/L":
                        logger.debug("About to call create_daily_pl: %s (module=%s)", getattr(create_daily_pl, "__name__", None), getattr(create_daily_pl, "__module__", None))
                        fig = create_daily_pl(
                             filtered_data,
                             exchange_rates=self.settings_manager.get_exchange_rates(),
                             base_currency=self.settings_manager.get_base_currency(),
                             account_id=None
                         )
                    elif selection == "P/L vs Trades":
                        fig = create_daily_pl_vs_trades(
                            filtered_data,
                            exchange_rates=self.settings_manager.get_exchange_rates(),
                            base_currency=self.settings_manager.get_base_currency(),
                            account_id=None
                        )
                    elif selection == "Relative P/L":
                        fig = create_relative_balance_history(filtered_data)
                    elif selection == "P/L by Market":
                        # Use consolidated market P/L chart function (wrap to capture full traceback)
                        try:
                            fig = create_market_pl_chart(filtered_data, top_n=10)
                        except Exception as e:
                            import traceback as _tb
                            tb = _tb.format_exc()
                            logger.error("Error creating Market P/L visualization: %s\n%s", e, tb)
                            QMessageBox.critical(self, "Error", f"Failed to create Market P/L visualization:\n{e}\n\nSee logs for details.")
                            return
                    elif selection == "Win/Loss Analysis":
                        fig = create_win_loss_analysis(filtered_data)
                except Exception as e:
                    logger.exception("Error creating P/L visualization: %s", e)
                    QMessageBox.critical(self, "Error", f"Failed to create P/L visualization: {e}")
                    return
            elif selection == "Balance History":
                try:
                    # Use the already computed filtered_data (it respects UI start/end/account)
                    fd = filtered_data
                    logger.debug("create_balance_chart: using filtered_data directly for balance chart; shape=%s", getattr(fd, "shape", None))

                    acct = filtered_account if 'filtered_account' in locals() else None
                    try:
                        if acct == "all":
                            acct = None
                        elif acct is not None:
                            acct = int(acct)
                    except Exception:
                        logger.debug("Could not coerce account id to int; passing as-is: %r", acct)

                    fig = create_balance_history(
                        fd,
                        base_currency=(self.settings_manager.get_base_currency() if hasattr(self, "settings_manager") else None),
                        account_id=acct,
                        # pass UI start/end so the chart can reapply them if desired
                        start_date=self.start_date.text().strip() if hasattr(self, "start_date") and self.start_date.text().strip() else None,
                        end_date=self.end_date.text().strip() if hasattr(self, "end_date") and self.end_date.text().strip() else None,
                    )
                except Exception as e:
                    import traceback as _tb
                    tb = _tb.format_exc()
                    logger.error("Error creating Balance History visualization: %s\n%s", e, tb)
                    QMessageBox.critical(self, "Error", f"Failed to create Balance History visualization:\n{e}\n\nSee logs for details.")
                    return
            else:
                # existing non-PL visualization path
                fig = create_visualization_figure(
                    filtered_data,
                    selection,
                    self.settings_manager.get_exchange_rates(),
                    self.settings_manager.get_base_currency()
                )

            # Display in webview
            # Validate figure before display (prevent NoneType.write_html errors)
            if fig is None or not hasattr(fig, "write_html"):
                logger.error("No valid Plotly figure to display (fig=%s)", type(fig))
                QMessageBox.critical(self, "Visualization Error", "Unable to create visualization (no figure). See logs for details.")
                return
            try:
                self.visualization_manager.display_plotly_figure(
                    self.graph_display_frame,
                    fig,
                    "graph_display"
                )
            except Exception as e:
                logger.exception("Error displaying Plotly figure: %s", e)
                QMessageBox.critical(self, "Display Error", f"Failed to display visualization: {e}")
            
        except Exception as e:
            logger.error(f"Error displaying graph: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create visualization: {str(e)}")

    def get_filtered_data(self):
        """Get filtered data based on current selections.
        Calls DataManager.get_filtered_data adaptively (supports multiple signatures).
        Always returns a DataFrame (may be empty).
        """
        if not self.data_manager.has_data():
            logger.warning("No data in data_manager")
            return pd.DataFrame()

        # Log raw store shape if available
        try:
            logger.debug(f"Data shape before filtering: {self.data_manager.df.shape}")
        except Exception:
            pass

        # Build filter values from UI
        selected_broker = self.broker_combo.currentText()
        broker_key = None
        if selected_broker != 'All':
            bk = [k for k, v in BROKERS.items() if v == selected_broker]
            broker_key = bk[0] if bk else None

        account_id = None
        if hasattr(self, "account_combo"):
            account_id = self.account_combo.currentData()
            if account_id == "all":
                account_id = None
            # coerce to int when possible
            try:
                if account_id is not None:
                    account_id = int(account_id)
            except Exception:
                logger.debug("Could not coerce account_id to int; keeping original value")

        # validate/parse dates to avoid accidental filtering-out
        start_text = self.start_date.text().strip() if self.start_date.text() else None
        end_text = self.end_date.text().strip() if self.end_date.text() else None
        try:
            sd = pd.to_datetime(start_text, errors='coerce') if start_text else None
            ed = pd.to_datetime(end_text, errors='coerce') if end_text else None
            # only pass strings/datetimes that parsed successfully; otherwise None
            start_date = sd if (sd is not None and pd.notna(sd)) else None
            end_date = ed if (ed is not None and pd.notna(ed)) else None
        except Exception:
            start_date = None
            end_date = None

        logger.debug("Filters - broker_key: %s, account_id: %s, start_date: %s, end_date: %s",
                     broker_key, account_id, start_date, end_date)

        # Call DataManager.get_filtered_data adaptively (support different signatures)
        dm = self.data_manager
        df_out = pd.DataFrame()
        if dm is None:
            return df_out

        func = getattr(dm, "get_filtered_data", None)
        if not callable(func):
            logger.error("DataManager has no get_filtered_data method")
            return df_out

        try:
            import inspect
            sig = inspect.signature(func)
            call_kwargs = {}
            if 'broker_key' in sig.parameters:
                call_kwargs['broker_key'] = broker_key
            elif 'broker' in sig.parameters:
                call_kwargs['broker'] = broker_key
            if 'account_id' in sig.parameters:
                call_kwargs['account_id'] = account_id
            elif 'account' in sig.parameters:
                call_kwargs['account'] = account_id
            if 'start_date' in sig.parameters:
                call_kwargs['start_date'] = start_date
            if 'end_date' in sig.parameters:
                call_kwargs['end_date'] = end_date

            if call_kwargs:
                df_out = func(**call_kwargs)
            else:
                # fallback to positional calling: (broker_key, account_id, start_date, end_date)
                df_out = func(broker_key, account_id, start_date, end_date)
        except TypeError:
            # last-resort attempts
            try:
                df_out = func(broker_key, account_id, start_date, end_date)
            except Exception as e:
                logger.exception("Adaptive call to data_manager.get_filtered_data failed: %s", e)
                df_out = pd.DataFrame()
        except Exception as e:
            logger.exception("Error calling data_manager.get_filtered_data: %s", e)
            df_out = pd.DataFrame()

        # Ensure DataFrame return type
        if df_out is None:
            df_out = pd.DataFrame()
        elif not isinstance(df_out, pd.DataFrame):
            try:
                df_out = pd.DataFrame(df_out)
            except Exception:
                logger.exception("Could not coerce get_filtered_data result to DataFrame")
                df_out = pd.DataFrame()

        logger.debug("get_filtered_data returned shape=%s; columns=%s", getattr(df_out, "shape", None),
                     list(getattr(df_out, "columns", []) ) )
        try:
            logger.debug("Sample rows: %s", df_out.head(3).to_dict('records'))
        except Exception:
            pass

        return df_out

    def validate_date_range(self):
        """Validate date range inputs"""
        start = self.start_date.text()
        end = self.end_date.text()
        
        if not start or not end:
            return True  # Empty dates are valid
            
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d')
            end_date = datetime.strptime(end, '%Y-%m-%d')
            
            if start_date > end_date:
                QMessageBox.warning(self, "Invalid Date Range", 
                                  "Start date must be before end date")
                return False
                
            if end_date > datetime.now():
                QMessageBox.warning(self, "Invalid Date Range", 
                                  "End date cannot be in the future")
                return False
                
            return True
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Date Format", 
                              "Please use YYYY-MM-DD format")
            return False
    
    def create_balance_chart(self):
        """Create balance history chart with account filtering"""
        # Reuse the tab's adaptive filtering (parses dates / adapts to DataManager signatures)
        try:
            filtered_df = self.get_filtered_data()
            logger.debug("create_balance_chart: get_filtered_data returned shape=%s columns=%s",
                         getattr(filtered_df, "shape", None), list(getattr(filtered_df, "columns", [])))
            # Log the UI start/end text values for clarity
            try:
                sd_text = self.start_date.text() if hasattr(self, "start_date") else None
                ed_text = self.end_date.text() if hasattr(self, "end_date") else None
            except Exception:
                sd_text = ed_text = None
            logger.debug("create_balance_chart: UI start_date text=%r end_date text=%r", sd_text, ed_text)
 
            if filtered_df is None or filtered_df.empty:
                logger.error("No data available for the selected filters")
                QMessageBox.warning(self, "Info", "No data available for selected date range")
                return

            # Ensure account_id is an integer when passed explicitly
            account_id = None
            if hasattr(self, "account_combo"):
                account_id = self.account_combo.currentData()
                if account_id == "all":
                    account_id = None
                else:
                    try:
                        account_id = int(account_id) if account_id is not None else None
                    except Exception:
                        logger.debug("Could not coerce account_id to int; passing as-is")

            logger.debug("Calling create_balance_history with filtered_df.shape=%s account_id=%s",
                         getattr(filtered_df, "shape", None), account_id)

            fig = create_balance_history(
                filtered_df,
                base_currency=(self.settings_manager.get_base_currency() if hasattr(self, "settings_manager") else None),
                account_id=account_id,
            )

            # Display in webview
            self.visualization_manager.display_plotly_figure(
                self.graph_display_frame,
                fig,
                "balance_history"
            )
        except Exception as e:
            logger.exception("Error creating balance history chart: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to create balance history chart: {e}")

    def visualize_data(self, chart_key, df, **kwargs):
        """
        Dispatches the call to the appropriate visualization function based on the chart_key.
        
        Args:
            chart_key (str): The key representing the type of chart to create.
            df (DataFrame): The data to visualize.
            **kwargs: Additional keyword arguments for specific chart functions.
        """
        # ...existing code...

        # Points charts (consolidated)
        if chart_key in ('points_daily', 'points_monthly', 'points_per_market', 'points'):
            # determine mode
            if chart_key == 'points_daily':
                mode = 'daily'
            elif chart_key == 'points_monthly':
                mode = 'monthly'
            elif chart_key == 'points_per_market':
                mode = 'per_market'
            else:
                mode = kwargs.get('mode', 'daily')

            try:
                fig = create_points_view(df, mode=mode, top_n=kwargs.get('top_n', 10))
                # Replace the call below with your tab's actual renderer (e.g. self.display_figure or self.show_plot)
                if hasattr(self, "display_figure"):
                    self.display_figure(fig)
                elif hasattr(self, "display_graph"):
                    self.display_graph(fig)
                else:
                    # fallback: log and return
                    logger.warning("No display method found on graph tab; figure created but not shown")
                return
            except Exception as e:
                logger.exception("Error creating Points visualization: %s", e)
                # fall through to existing error handling / UI notification

        # ...existing code continues...