# data_228_data_lighthouse_proj
Data 228 fall 2022 - team data lighthouse term project

# How to run on localhost
1. Create virtual env: ```python3 -m venv data_228_env```
2. Install virtual env: ```pip install -r requirements.txt```
3. Activate the env using Powershell:  C:\project\data_228_data_lighthouse_proj\data_228_env\Scripts\Activate.ps1
4. Run flask local env:
   1. Turn on debug mode (powershell): ``` set FLASK_ENV=development```
   2. start as debugger ```python app.py```

# Note
1. if installed new libraries using pip, always update requirements.txt using: python3 -m pip freeze > requirements.txt
