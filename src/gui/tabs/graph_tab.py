from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
                           QComboBox, QPushButton, QLineEdit, QTreeWidget, 
                           QTreeWidgetItem, QSizePolicy, QMessageBox)
from PyQt6.QtCore import Qt
import logging
import sqlite3
from datetime import datetime
from settings import BROKERS, VALID_GRAPH_TYPES, UI_SETTINGS
from visualize_data import create_visualization_figure
from chart_types.balance import create_balance_history
from chart_types.points import create_points_view
from chart_types.pl import (
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
        """Setup the graph tab UI"""
        layout = QHBoxLayout(self)

        # Create selection frame
        self.create_selection_frame(layout)
        
        # Create graph display area
        self.graph_display_frame = QFrame()
        self.graph_display_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.graph_display_frame)

    def create_selection_frame(self, parent_layout):
        """Create the graph selection controls"""
        selection_frame = QFrame()
        selection_frame.setFixedWidth(UI_SETTINGS['graph_selection_width'])
        selection_layout = QVBoxLayout(selection_frame)

        # Broker selection
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

        parent_layout.addWidget(selection_frame)

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
        quick_select_layout = QHBoxLayout(quick_select_frame)

        seven_days_btn = QPushButton("7 Days")
        seven_days_btn.clicked.connect(lambda: self.set_date_range(7))
        quick_select_layout.addWidget(seven_days_btn)

        thirty_days_btn = QPushButton("30 Days")
        thirty_days_btn.clicked.connect(lambda: self.set_date_range(30))
        quick_select_layout.addWidget(thirty_days_btn)

        all_btn = QPushButton("All")
        all_btn.clicked.connect(self.reset_date_range)
        quick_select_layout.addWidget(all_btn)

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
                    # Prefer DataManager's filtering if available so chart modules get canonical data
                    fd = filtered_data
                    dm = getattr(self, "data_manager", None)
                    if dm is not None and callable(getattr(dm, "get_filtered_data", None)):
                        try:
                            # call get_filtered_data adaptively: prefer kwargs, fall back to positional
                            func = dm.get_filtered_data
                            # build arg values from locals (use None when missing)
                            bk = broker_key if 'broker_key' in locals() else None
                            acc = filtered_account if 'filtered_account' in locals() else None
                            sd = start_date if 'start_date' in locals() else None
                            ed = end_date if 'end_date' in locals() else None
                            import inspect
                            sig = inspect.signature(func)
                            # try keyword call first when supported
                            try:
                                call_kwargs = {}
                                if 'broker_key' in sig.parameters:
                                    call_kwargs['broker_key'] = bk
                                if 'account_id' in sig.parameters or 'account' in sig.parameters:
                                    # accept either account_id or account
                                    if 'account_id' in sig.parameters:
                                        call_kwargs['account_id'] = acc
                                    else:
                                        call_kwargs['account'] = acc
                                if 'start_date' in sig.parameters:
                                    call_kwargs['start_date'] = sd
                                if 'end_date' in sig.parameters:
                                    call_kwargs['end_date'] = ed
                                if call_kwargs:
                                    fd = func(**call_kwargs)
                                else:
                                    # no recognizable kw params, try positional
                                    fd = func(bk, acc, sd, ed)
                            except TypeError:
                                # fallback: attempt a positional call
                                try:
                                    fd = func(bk, acc, sd, ed)
                                except Exception:
                                    # last resort: call without args
                                    fd = func()
                        except Exception:
                            logger.exception("data_manager.get_filtered_data failed; falling back to existing filtered_data")

                    fig = create_balance_history(
                        fd,
                        base_currency=(self.settings_manager.get_base_currency() if hasattr(self, "settings_manager") else None),
                        account_id=(filtered_account if 'filtered_account' in locals() else None),
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
        # Get the selected filters
        selected_broker = self.broker_combo.currentText()
        broker_key = None
        if selected_broker != 'All':
            broker_key = [k for k, v in BROKERS.items() if v == selected_broker]
            broker_key = broker_key[0] if broker_key else None

        account_id = None
        if hasattr(self, "account_combo"):
            account_id = self.account_combo.currentData()
            if account_id == "all":
                account_id = None

        start_date = self.start_date.text() if self.start_date.text() else None
        end_date = self.end_date.text() if self.end_date.text() else None

        logger.debug(f"Filters - broker_key: {broker_key}, account_id: {account_id}, start_date: {start_date}, end_date: {end_date}")

        # Add debug logging to print the type of account_id
        logger.debug(f"Type of account_id: {type(account_id)}")

        # Get the filtered data
        filtered_df = self.data_manager.get_filtered_data(
            broker_key, account_id, start_date, end_date
        )
        logger.debug(f"Account ID being passed to create_balance_history: {account_id}")

        logger.debug(f"Data shape before filtering: {filtered_df.shape}")

        if filtered_df is None or filtered_df.empty:
            logger.error("No data available for the selected filters")
            QMessageBox.warning(self, "Info", "No data available for selected date range")
            return

        
        # Create the balance history chart
        try:
            # Add debug logging to print the account_id being passed to create_balance_history
            logger.debug(f"Account ID being passed to create_balance_history: {account_id}")
            
            # Ensure account_id is an integer
            if account_id and account_id != "all":
                account_id = int(account_id)

            

            fig = create_balance_history(filtered_df, account_id=account_id)

            # Display in webview
            self.visualization_manager.display_plotly_figure(
                self.graph_display_frame,
                fig,
                "balance_history"
            )
        except Exception as e:
            logger.error(f"Error creating balance history chart: {e}")
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