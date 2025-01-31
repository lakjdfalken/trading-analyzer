# Trading Analyzer

A tool for analyzing trading data and generating insights.

## Features

- Trade data analysis
- Performance metrics calculation
- Visualization of trading patterns
- Custom reporting capabilities

## Prerequisites

- Python 3.7 or higher
- pandas >= 1.3.0
- matplotlib >= 3.4.0
- numpy >= 1.20.0
- PyQt6 >= 6.6.0
- PyQt6-WebEngine >= 6.6.0 (for x86_64 systems)
- Microsoft Visual C++ 14.0 or greater Build Tools (Windows only)

For Windows systems:
- x86_64 architecture: All packages supported
- ARM64 architecture: Use matplotlib backend instead of WebEngine - in short, it doesn't work.

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


## Installation on Windows

0. Start a power shell as an administrator.

    winget install Microsoft.VisualStudio.2022.BuildTools

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

## Usage

1. Create a virtual environment:

    python -m venv .venv

2. Activate the virtual environment:

    source .venv/bin/activate
    .venv/bin/activate.bat # for Windows
    

3. Run the application:

    python src/main.py

4. Import the TransactionHistory.csv file 

    Choose the date range you want to analyze from the menu.

5. Laugh or cry.

## License
MIT License - See LICENSE file for details

## Support

You are on your own. I know nothing.

## Contributing

Code enhancements are welcome. Here's how you can contribute:

- Open an issue to discuss proposed changes
- Submit a pull request with improvements
- Share bug reports or feature requests
- Suggest code optimizations

This project benefits from contributions by:
- Sourcegraph Cody - Code refactoring, optimization suggestions, and documentation improvements