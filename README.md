## to clone a git repository
```
git clone <repository_url>
```

## to commit changes to a git repository
```
git add .
git commit -m "<commit_message>"
git push
```

## to create a virtual environment
```
python -m venv .venv
```

## to activate the virtual environment
```
source .venv/bin/activate
```

## to deactivate the virtual environment
```
deactivate
```

## to install requirements
```
python -m pip install -r requirements.txt
```

## to run a python script
```
python <script_name.py>
```

## how to refresh your server
```
uvicorn mcp_server:app --reload
```

## using uv for package management
```
uv init  # initialise uv
uv commands
    add <package_name>
    remove <package_name>
    update <package_name>
    list
    info <package_name>
    search <package_name>
    
```
