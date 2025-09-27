Hong Kong Weather Visualization for August 2024

I created an interactive data art visualization project showing Hong Kong's daily weather for August 2024, using Python and Pygame.
The project takes real-world weather data (via an API or CSV file), processes it, and renders a particle system, where each particle represents a day in August.
Features
 • Particle-based visualization
Each day’s weather (sunny, cloudy, rainy) is represented as a particle with distinct orbit radius, speed, and color.
 • Color mapping by temperature
Particle colors vary depending on the day’s mean temperature.
 • Interactive effects
• Hover with mouse → highlight particle & show tooltip with date + temperature
• Neighboring particles scatter slightly when one is hovered
• Particles rotate in circular/axis-based layouts
 • Axis-based layout
• X-axis = dates (Aug 1 – Aug 31)
• Y-axis = temperature scale
 • Collapsible statistics panel
Right-hand panel shows summary (number of sunny/rainy/cloudy days, average/max/min temperature).
Panel can be collapsed/expanded by clicking the title area.

While the course examples mainly use pandas and matplotlib for visualization, this project uses Pygame to create an interactive particle system. This approach demonstrates that data visualization can go beyond static charts and be represented as dynamic, interactive art.

⸻

Data Source
 • Primary: Hong Kong Observatory (HKO) Open Data
 • Fallback: Open-Meteo API (daily temperature, precipitation, weather code)
 • Offline option: Local CSV (data/hko_2024_08.csv) for reproducibility

⸻

Installation

Make sure you have Python 3.9+ installed. Then install dependencies:

pip install -r requirements.txt

⸻

Run

Start the visualization with:

python weather_galaxy.py

⸻

File Structure

.
data_fetch.py         # Fetches & parses weather data (API/CSV)
weather_galaxy.py     # Main visualization script (Pygame)
requirements.txt      # Dependencies (pygame, requests, pandas)
.gitignore            # Ignore cache/venv/system files
README.md             # Project documentation

⸻

Example Output
 • Particles arranged along date (X-axis) and temperature (Y-axis)
 • Interactive highlights with tooltips
 • Collapsible statistics panel with summary of weather
 
 reference:
 ## References / Data Sources
- Hong Kong Observatory (HKO) Open Data. Retrieved from: [https://www.hko.gov.hk/en/opendata/index.htm](https://www.hko.gov.hk/en/opendata/index.htm)  
- Open-Meteo API. Retrieved from: [https://open-meteo.com/](https://open-meteo.com/)  
- Offline backup: CSV file (`data/hko_2024_08.csv`) manually exported from HKO website for reproducibility.