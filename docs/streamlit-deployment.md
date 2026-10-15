# Streamlit deployment

Deploy this repository's `main` branch using `app.py` as the main file and Python 3.11. The committed `outputs` directory supplies all dashboard data, so startup does not need to download the USGS source or execute the pipeline. No secrets, API keys, database server or local laptop connection are required.

The dashboard labels the property portfolio as synthetic and the USGS shaking map as a historical scenario. Sidebar filters update the charts, property map and concentration table. The expanded hazard map and data-quality tab intentionally describe the full portfolio.

To refresh the analytical outputs, run `python pipeline.py`, verify `python -m pytest -q`, and commit the updated output files. Streamlit rebuilds from repository changes. Map tiles and map JavaScript need internet access. Community Cloud can put inactive apps to sleep; visitors may need to wait while the app wakes up.
