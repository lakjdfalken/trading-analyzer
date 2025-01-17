# Trading Analyzer

A tool for analyzing trading data and generating insights.

## Features

- Trade data analysis
- Performance metrics calculation
- Visualization of trading patterns
- Custom reporting capabilities

## Prerequisites

- Python 3.7 or higher

## Installation on MacOS

1. Clone the repository:

git clone https://github.com/lakjdfalken/trading-analyzer.git

cd trading-analyzer

2. Create a virtual environment:

python3 -m venv .venv

3. Activate the virtual environment:

source .venv/bin/activate

4. Install the required packages:

pip install -r requirements.txt

## Usage
python src/main.py

import the TransactionHistory.csv file and choose the date range you want to analyze from the menu.


## Installation on Windows

1. Clone the repository:
    
    git clone https://github.com/lakjdfalken/trading-analyzer.git

    cd trading-analyzer

2. Create a virtual environment:
  
  python -m venv .venv
  
  .venv\Scripts\activate.bat

3. Install the required packages: 
  
  pip install -r requirements.txt
    
4. Run the application:
  
  python src/main.py

## Building Windows Executable

1. Install PyInstaller:
  
  pip install pyinstaller

2. Create the executable:
  
  pyinstaller --onefile --windowed src/main.py