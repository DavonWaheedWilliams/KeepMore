# Upload KeepMore to GitHub

The repository is ready for GitHub. It contains Streamlit v0.1.2 and Python tests.
Personal databases, environment variables, API keys, and Python caches are excluded.

## 1. Create a private, empty repository
- Sign in to GitHub as `DavonWaheedWilliams`.
- Open https://github.com/new
- Repository name: `KeepMore`
- Visibility: **Private**
- Leave **Add README**, **Add .gitignore**, and **Choose a license** blank.
- Select **Create repository**.

## 2. Upload from Windows using Git
Install Git for Windows from https://git-scm.com/downloads/win if needed.
Extract `KeepMore_GitHub_Ready_v0.1.2.zip`.
Open the extracted `KeepMore` folder in File Explorer.
Click the address bar, enter `cmd`, and press Enter.

Run the following commands, one line at a time:

```bat
git init -b main
git add .
git status
git commit -m "Initial KeepMore Streamlit v0.1.2"
git remote add origin https://github.com/DavonWaheedWilliams/KeepMore.git
git push -u origin main
```

Complete the browser sign-in prompt if Git requests authentication.
Refresh https://github.com/DavonWaheedWilliams/KeepMore to confirm the upload.

## 3. Alternative: GitHub web upload
Open the repository. Select **uploading an existing file** (or **Add file** > **Upload files**).
Drag the extracted project files and folders into the upload area.
Upload *the extracted files*, not the ZIP itself. Confirm that `app.py`,
`keepmore/`, `tests/`, `.streamlit/`, and `requirements.txt` appear.
Commit directly to `main`.

## Subsequent updates
Open Command Prompt in the project folder and run:

```bat
git add .
git commit -m "Improve KeepMore"
git push
```

## Security
- Do not commit the `data/` directory or files containing financial records.
- Never commit `OPENAI_API_KEY`, `.env` or `.streamlit/secrets.toml`.
- Keep this repository **private** while building the commercial product.
- The current app has no secure multi-user authentication. Do not host it as
  a public financial-data service in its present form.
