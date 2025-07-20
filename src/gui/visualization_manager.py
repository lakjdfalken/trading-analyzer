import os
import shutil
from datetime import datetime, timedelta
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QVBoxLayout
import logging

logger = logging.getLogger(__name__)


class VisualizationManager:
    def __init__(self):
        self.webviews = {}  # Store webviews by name
        self.temp_dir = os.path.join(os.getcwd(), 'temp_graphs')

    def get_or_create_webview(self, name, parent_frame):
        """Get existing webview or create new one"""
        if name not in self.webviews or self.webviews[name] is None:
            # Create layout if frame doesn't have one
            if not parent_frame.layout():
                layout = QVBoxLayout()
                parent_frame.setLayout(layout)
            
            # Create webview
            webview = QWebEngineView()
            parent_frame.layout().addWidget(webview)
            self.webviews[name] = webview
            
        return self.webviews[name]

    def display_graph(self, parent_frame, html_content, webview_name="default"):
        """Display graph in webview"""
        try:
            # Ensure temp directory exists
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Get or create webview
            webview = self.get_or_create_webview(webview_name, parent_frame)
            
            # Save HTML content
            temp_path = os.path.join(self.temp_dir, f'{webview_name}.html')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Load in webview
            webview.load(QUrl.fromLocalFile(temp_path))
            
        except Exception as e:
            logger.error(f"Error displaying graph: {e}")
            raise

    def display_plotly_figure(self, parent_frame, fig, webview_name="default"):
        """Display Plotly figure in webview"""
        try:
            # Ensure temp directory exists
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Get or create webview
            webview = self.get_or_create_webview(webview_name, parent_frame)
            
            # Save figure as HTML
            temp_path = os.path.join(self.temp_dir, f'{webview_name}.html')
            fig.write_html(temp_path, include_plotlyjs=True, full_html=True)
            
            # Load in webview
            webview.load(QUrl.fromLocalFile(temp_path))
            
        except Exception as e:
            logger.error(f"Error displaying Plotly figure: {e}")
            raise

    def cleanup_temp_files(self):
        """Clean up temporary files older than 24 hours"""
        try:
            if os.path.exists(self.temp_dir):
                current_time = datetime.now()
                for filename in os.listdir(self.temp_dir):
                    filepath = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(filepath):
                        file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if current_time - file_modified > timedelta(hours=24):
                            os.remove(filepath)
                            logger.debug(f"Cleaned up old temp file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

    def cleanup(self):
        """Clean up all webviews and temp files"""
        try:
            # Clear webview references
            for name in self.webviews:
                self.webviews[name] = None
            self.webviews.clear()
            
            # Clean up temp directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"Error in visualization cleanup: {e}")