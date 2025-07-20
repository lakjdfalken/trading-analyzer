from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
import pandas as pd
import logging
from settings import DATA_COLUMNS

logger = logging.getLogger(__name__)


class DataTab(QWidget):
    def __init__(self):
        super().__init__()
        self.sort_states = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup the data tab UI"""
        layout = QVBoxLayout(self)
        
        # Create and configure tree widget
        self.tree = QTreeWidget()
        columns = ["broker_name", "Transaction Date", "Ref. No.", "Action", "Description", 
                  "Amount", "Open Period", "Opening", "Closing", "P/L", 
                  "Status", "Balance", "Currency", "Fund_Balance", "sl", "tp"]
        self.tree.setHeaderLabels(columns)
        
        # Enable sorting and visual indicators
        self.tree.setSortingEnabled(True)
        self.tree.header().setSectionsClickable(True)
        self.tree.header().setSortIndicatorShown(True)
        self.tree.header().sectionClicked.connect(self.sort_treeview)
        
        layout.addWidget(self.tree)

    def update_display(self, df):
        """Update the tree display with new data"""
        if df is None or df.empty:
            self.tree.clear()
            return
            
        self.tree.clear()
        treeview_columns = DATA_COLUMNS
        
        for idx, row in df.iterrows():
            item = QTreeWidgetItem()
            for col, column_name in enumerate(treeview_columns):
                value = row[column_name]
                
                # Handle numeric fields with nan values
                if column_name in ["Amount", "Opening", "Closing", "P/L", "Balance", "Fund_Balance"]:
                    if pd.isna(value):
                        item.setText(col, "")
                        item.setData(col, Qt.ItemDataRole.UserRole, 0)
                    else:
                        try:
                            num_value = float(str(value).replace(',', ''))
                            item.setText(col, str(value))
                            item.setData(col, Qt.ItemDataRole.UserRole, num_value)
                        except:
                            item.setText(col, "0")
                            item.setData(col, Qt.ItemDataRole.UserRole, 0)
                else:
                    item.setText(col, str(value))
                    
            self.tree.addTopLevelItem(item)

        # Adjust column widths based on content
        for column in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(column)

    def sort_treeview(self, column):
        """Handle column sorting"""
        # Initialize sort state for this column if needed
        if column not in self.sort_states:
            self.sort_states[column] = Qt.SortOrder.AscendingOrder
        
        # Toggle the sort state for this column
        self.sort_states[column] = (Qt.SortOrder.DescendingOrder 
            if self.sort_states[column] == Qt.SortOrder.AscendingOrder 
            else Qt.SortOrder.AscendingOrder)
        
        # Apply the sort
        self.tree.sortByColumn(column, self.sort_states[column])