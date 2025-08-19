# Travecto

![Stars](https://img.shields.io/github/stars/Inc44/Travecto?style=social)
![Forks](https://img.shields.io/github/forks/Inc44/Travecto?style=social)
![Watchers](https://img.shields.io/github/watchers/Inc44/Travecto?style=social)
![Repo Size](https://img.shields.io/github/repo-size/Inc44/Travecto)
![Language Count](https://img.shields.io/github/languages/count/Inc44/Travecto)
![Top Language](https://img.shields.io/github/languages/top/Inc44/Travecto)
[![Issues](https://img.shields.io/github/issues/Inc44/Travecto)](https://github.com/Inc44/Travecto/issues?q=is%3Aopen+is%3Aissue)
![Last Commit](https://img.shields.io/github/last-commit/Inc44/Travecto?color=red)
[![Release](https://img.shields.io/github/release/Inc44/Travecto.svg)](https://github.com/Inc44/Travecto/releases)
[![Sponsor](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/Inc44)
[![Build](https://github.com/Inc44/Travecto/actions/workflows/build.yml/badge.svg)](https://github.com/Inc44/Travecto/actions/workflows/build.yml)

Optimizes travel routes using [Google Maps Geocoding API](https://developers.google.com/maps/documentation/geocoding/overview) and the [traveling salesman problem](https://en.wikipedia.org/wiki/Travelling_salesman_problem) solver from [OR-Tools](https://developers.google.com/optimization).

## ⚙️ Features

- Solves the traveling salesman problem for optimal route planning.
- Geocodes place names using Google Maps API with intelligent fallback strategies.
- Caches geocoding results to minimize API calls.
- Supports mandatory locations per day with automatic clustering.
- Calculates realistic travel times based on mixed Metro and walking transportation.
- Generates interactive route maps with satellite and street view options.
- Handles Unicode normalization for international place names.
- Configurable rate limiting with exponential backoff retry logic.
- TOML-based configuration for easy customization.

## ⚠️ Disclaimers

- **Google API Key Required**: This tool requires a valid Google Maps Geocoding API key. Pricing applies based on usage (Google offers 10,000 requests per month free).
- **Transportation Model**: Travel time calculations assume a mixed Metro/walking model optimized for the Paris Metro system. Accuracy may vary for other transportation systems.
- **Rate Limiting**: Default rate limit is set to 50 QPS to stay within Google API limits. Adjust based on your API quota.
- **Licensing Restrictions**: Google's terms are notably restrictive. Geocoding results cannot be stored permanently outside of Google's services. You may cache results for up to 30 days for performance, but permanent storage is only allowed if data is displayed on a Google map and used within Google's ecosystem, which is not the case for Travecto as it uses Folium, which uses Leaflet for displaying maps.

## 🚀 Installation

### With PyPI

```bash
pip install travecto
```

### With pipx

```bash
pipx install travecto
```

### With Conda

```bash
conda create -n travecto python=3.9 -y # up to 3.13
conda activate travecto
pip install travecto
```

### From Source

```bash
git clone https://github.com/Inc44/Travecto.git
cd Travecto
```

To install the package:

```bash
pip install .
```

To install only the dependencies:

```bash
pip install -r requirements.txt
```

_If you install only the dependencies, run the program using_ `python -m travecto.cli` _(or_ `python -OO travecto/cli.py`_) instead of the `travecto` command._

## 🛠️ Build from Source

```bash
pip install build
python -m build
```

## 📦 Publish

```bash
pip install twine
twine upload dist/*
```

## 🧾 Configuration

Set environment variable:

```powershell
setx /M GOOGLE_MAPS_API_KEY your_api_key
setx /M THUNDERFOREST_API_KEY your_api_key
```

For Linux/macOS:

```bash
echo 'export GOOGLE_MAPS_API_KEY="your_api_key"' >> ~/.bashrc # or ~/.zshrc
echo 'export THUNDERFOREST_API_KEY="your_api_key"' >> ~/.bashrc # or ~/.zshrc
```

Or create a `.env` file or modify /etc/environment:

```
GOOGLE_MAPS_API_KEY=your_api_key
THUNDERFOREST_API_KEY=your_api_key
```

Check by restarting the terminal and using:

```cmd
echo %GOOGLE_MAPS_API_KEY%
echo %THUNDERFOREST_API_KEY%
```

For Linux/macOS:

```bash
echo $GOOGLE_MAPS_API_KEY
echo $THUNDERFOREST_API_KEY
```

## 📖 Usage Examples

### Basic Route Planning

Calculate optimal routes for all configured cities:

```bash
python -m travecto
```

Same but loading .env file:

```bash
python -m dotenv -f /path/to/.env run -- travecto
```

### Generate Interactive Maps

Create HTML maps showing optimized routes:

```bash
python -m travecto --maps
```

### Custom Configuration

Use custom configuration file:

```bash
python -m travecto --input config.toml
```

### Custom Output Directory

Save maps to specific directory:

```bash
python -m travecto --maps --output html
```

## 🎨 Command-Line Arguments

| Argument               | Description                                                                        |
|------------------------|------------------------------------------------------------------------------------|
| `-i, --input <path>`   | Path to the TOML configuration file. Default: `demo.toml`.                         |
| `-o, --output <path>`  | Directory for map files. Default: `routes`.                                        |
| `--maps`               | Generate interactive HTML maps for visualization.                                  |
| `--workers <n>`        | Number of OR-Tools search workers. Default: 32.                                    |
| `--loglevel <level>`   | Set logging level (NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: ERROR. |

## 🎯 Motivation

Planning efficient tourist routes in large cities like Paris requires solving complex optimization problems. Traditional route planners fail to optimize across multiple locations or lack the flexibility for mandatory stops. [Google Maps](https://www.google.com/maps) supports a maximum of 10 destinations and [MapQuest](https://www.mapquest.com/routeplanner) supports a maximum of 26 addresses. So in the summer of 2025, as I had a need for about 80 stops, I decided to create this tool to solve multi-day touring itineraries using proven algorithms while maintaining practical transportation models for European cities.

## 🐛 Bugs

Not yet found.

## ⛔ Known Limitations

- Geocoding heavily depends on Google Maps API quality and may fail for very obscure locations; therefore, adding a postal code at the end of the destination name or defining renaming patterns is recommended.
- The transportation model assumes a uniform Metro/walking mix, which may not reflect actual city-specific conditions.
- OR-Tools TSP solver may not find globally optimal solutions for very large datasets within time limits.
- If you don't like the current selection of tile providers for Map, Satellite, and Transport, or they don't work for your region, modify the code by replacing them with others available at: [Leaflet Provider Demo](https://leaflet-extras.github.io/leaflet-providers/preview).
- Serving pre-compressed `.br`, `.zstd`, `.gz`, and `.deflate` files on an Apache server is not possible because the Cloudflare proxy dynamically recompresses responses when [Automatic HTTPS Rewrites](https://developers.cloudflare.com/speed/optimization/content/compression) are used.

## 🚧 TODO

- [ ] **Original-Order Mode (No Optimization)**.
- [ ] **Minimize-Time Mode**: Use minutes instead of km.
- [ ] **Per-Mode Speeds**.
- [ ] **Real-Time Transit Integration**.
- [ ] **Mixed Transportation Modes**.
- [ ] **Periodic Stops**: Restaurant and home stops.
- [ ] **Target Time**: Opening, closing, and visit windows.
- [ ] **Multi-Objective Optimization**: Enable optimization for factors beyond distance, such as opening hours, crowd levels, and personal preferences.
- [ ] **[routing_parameters_pb.jl](https://github.com/google/or-tools/blob/stable/ortools/julia/ORToolsGenerated.jl/src/genproto/operations_research/routing_parameters_pb.jl)**: Explore the configuration available for `search_params`.
- [ ] **More Maps**: Topology, cycling, and dark mode versions.
- [ ] **Security, Abuse Prevention, Quota Handling**.
- [ ] **Hide Internal Functions**: `__all__` or underscore prefix.
- [ ] **Tests**.

## 🙏 Thanks

Creators of:

- [Python](https://www.python.org)
- [Google Maps Platform](https://developers.google.com/maps)
- [OR-Tools](https://developers.google.com/optimization)
- [aiohttp](https://docs.aiohttp.org)
- [Folium](https://python-visualization.github.io/folium/)
- [Tenacity](https://tenacity.readthedocs.io)

## 🤝 Contribution

Contributions, suggestions, and new ideas are heartily welcomed. If you're considering significant modifications, please initiate an issue for discussion before submitting a pull request.

## 📜 License

[![MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](https://opensource.org/licenses/MIT)

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 💖 Support

[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/xamituchido)
[![Ko-Fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/inc44)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/Inc44)