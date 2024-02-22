# Rag Chat
You need to download indexes.zip and KB.zip from "Surf Demo" Teams group.
Expand the zip in stramlit running directory


# atg_platform_streamlit

```
pip install streamlit

streamlit run main.py
```

# Packaging

# Using pyInstaller

Add run.py and hooks as per https://ploomber.io/blog/streamlit_exe/
`pyinstaller --onefile --additional-hooks-dir=./hooks run.py --clean`
Add data details in run.spec file
```python3
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

datas = [("{$YOURPYTHONENV}/site-packages/streamlit/runtime", "./streamlit/runtime")]
datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")
```
and update `datas=datas` in Analysis object
then
`pyinstaller run.spec --clean`


# Using Stlite
https://github.com/whitphx/stlite/blob/main/packages/desktop/README.md

```
mkdir -p package/streamlit_app
cat <<EOT >> package/package.json
{
  "name": "now_chat",
  "version": "0.1.0",
  "main": "./build/electron/main.js",
  "scripts": {
    "dump": "dump-stlite-desktop-artifacts",
    "serve": "cross-env NODE_ENV=production electron .",
    "pack": "electron-builder --dir",
    "dist": "electron-builder",
    "postinstall": "electron-builder install-app-deps"
  },
  "build": {
    "files": ["build/**/*"],
    "directories": {
      "buildResources": "assets"
    }
  },
  "devDependencies": {
    "@stlite/desktop": "^0.25.0",
    "cross-env": "^7.0.3",
    "electron": "23.1.1",
    "electron-builder": "^23.6.0"
  }
}
EOT
cp -r . package/streamlit_app/
mv package/streamlit_app/main.py package/streamlit_app/streamlit_app.py
rm -rf package/package
cd package
npm install
npm run dump streamlit_app
npm run dist
```

