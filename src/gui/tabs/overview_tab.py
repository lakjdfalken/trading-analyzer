from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
                           QComboBox, QPushButton, QSizePolicy, QMessageBox,
                           QFileDialog)
import logging
from settings import BROKERS, UI_SETTINGS
from chart_types.tax_overview import (create_tax_overview_table, create_yearly_summary_chart, 
                                    get_available_years, get_tax_overview_data)

logger = logging.getLogger(__name__)


class OverviewTab(QWidget):
    def __init__(self, data_manager, visualization_manager):
        super().__init__()
        self.data_manager = data_manager
        self.visualization_manager = visualization_manager
        self.setup_ui()

    def setup_ui(self):
        """Setup the tax overview tab UI"""
        layout = QHBoxLayout(self)

        # Create selection frame
        self.create_selection_frame(layout)
        
        # Create overview display area
        self.overview_display_frame = QFrame()
        self.overview_display_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.overview_display_frame)

    def create_selection_frame(self, parent_layout):
        """Create the overview selection controls"""
        selection_frame = QFrame()
        selection_frame.setFixedWidth(UI_SETTINGS['graph_selection_width'])
        selection_layout = QVBoxLayout(selection_frame)

        # Year selection
        selection_layout.addWidget(QLabel("Select Year:"))
        self.year_combo = QComboBox()
        self.year_combo.addItem("All Years")
        selection_layout.addWidget(self.year_combo)

        # Broker filter
        selection_layout.addWidget(QLabel("Filter by Broker:"))
        self.broker_combo = QComboBox()
        self.broker_combo.addItems(['All'] + list(BROKERS.values()))
        selection_layout.addWidget(self.broker_combo)

        # View type selection
        selection_layout.addWidget(QLabel("View Type:"))
        self.view_type_combo = QComboBox()
        self.view_type_combo.addItems(['Tax Overview Table', 'Yearly Summary Chart'])
        selection_layout.addWidget(self.view_type_combo)

        # Generate button
        generate_button = QPushButton("Generate Overview")
        generate_button.clicked.connect(self.generate_tax_overview)
        selection_layout.addWidget(generate_button)

        # Export button
        export_button = QPushButton("Export to CSV")
        export_button.clicked.connect(self.export_tax_data)
        selection_layout.addWidget(export_button)

        # Add stretch to push controls to top
        selection_layout.addStretch()

        parent_layout.addWidget(selection_frame)

    def update_year_combo(self, df):
        """Update the year combo box with available years from data"""
        if df is not None and not df.empty:
            years = get_available_years(df)
            self.year_combo.clear()
            self.year_combo.addItem("All Years")
            for year in years:
                self.year_combo.addItem(str(year))

    def generate_tax_overview(self):
        """Generate the tax overview based on selected options"""
        try:
            if not self.data_manager.has_data():
                QMessageBox.warning(self, "No Data", "Please import trading data first")
                return

            # Get selected parameters
            selected_year_text = self.year_combo.currentText()
            selected_year = None if selected_year_text == "All Years" else int(selected_year_text)

            selected_broker_text = self.broker_combo.currentText()
            selected_broker = self.get_broker_key(selected_broker_text)

            view_type = self.view_type_combo.currentText()

            # Generate appropriate visualization
            df = self.data_manager.get_data()
            if view_type == 'Tax Overview Table':
                fig = create_tax_overview_table(df, selected_year, selected_broker)
            else:  # Yearly Summary Chart
                fig = create_yearly_summary_chart(df, selected_broker)

            # Display in webview
            self.visualization_manager.display_plotly_figure(
                self.overview_display_frame,
                fig,
                "tax_overview"
            )

        except Exception as e:
            logger.error(f"Error generating tax overview: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to generate tax overview: {str(e)}")

    def export_tax_data(self):
        """Export tax overview data to CSV"""
        try:
            if not self.data_manager.has_data():
                QMessageBox.warning(self, "No Data", "Please import trading data first")
                return

            # Get selected parameters
            selected_year_text = self.year_combo.currentText()
            selected_year = None if selected_year_text == "All Years" else int(selected_year_text)

            selected_broker_text = self.broker_combo.currentText()
            selected_broker = self.get_broker_key(selected_broker_text)

            # Get tax data
            df = self.data_manager.get_data()
            tax_data = get_tax_overview_data(df, selected_year, selected_broker)
        
            if tax_data.empty:
                QMessageBox.warning(self, "No Data", "No tax data available for export")
                return

            # Get file path for export
            broker_suffix = f"_{selected_broker_text}" if selected_broker_text != 'All' else ""
            default_filename = f"tax_overview_{selected_year if selected_year else 'all_years'}{broker_suffix}.csv"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Tax Overview",
                default_filename,
                "CSV Files (*.csv)"
            )
        
            if file_path:
                # Prepare data for export
                export_data = self.prepare_export_data(tax_data)
                
                # Export to CSV
                export_data.to_csv(file_path, index=False)
                QMessageBox.information(self, "Export Successful", f"Tax overview exported to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting tax data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export tax data: {str(e)}")

    def get_broker_key(self, broker_display_name):
        """Convert broker display name to broker key"""
        if broker_display_name == 'All':
            return None
        
        # Find the broker key from the display name
        broker_keys = [k for k, v in BROKERS.items() if v == broker_display_name]
        return broker_keys[0] if broker_keys else None

    def prepare_export_data(self, tax_data):
        """Prepare tax data for export"""
        export_data = tax_data.copy()
        
        # Remove internal broker name column if it exists
        if 'broker_name' in export_data.columns:
            export_data = export_data.drop(['broker_name'], axis=1)
        
        # Rename columns for better readability
        column_renames = {
            'Broker_Display': 'Broker',
            'Description': 'Market',
            'Total_PL': 'Total_P/L',
            'Trade_Count': 'Number_of_Trades',
            'First_Trade': 'First_Trade_Date',
            'Last_Trade': 'Last_Trade_Date'
        }
        
        # Only rename columns that exist
        existing_renames = {k: v for k, v in column_renames.items() if k in export_data.columns}
        export_data = export_data.rename(columns=existing_renames)
        
        return export_data