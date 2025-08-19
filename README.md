# 🍲 Food Planner App (Kivy)

Plan meals, generate shopping lists, and reduce grocery trips.

## Features
- 📚 Recipe library
- 📅 Weekly planner
- 🛒 Auto-generated shopping list

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build APK (manual)
```bash
buildozer -v android debug
```

## GitHub Actions
Push to `main` → check **Actions** tab → download APK from **Artifacts**.
