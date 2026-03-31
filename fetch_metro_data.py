import asyncio
import json

import aiohttp

METRO_API_BASE = "https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2"


async def fetch():
    async with aiohttp.ClientSession() as session:
        # Get Lines
        print("Fetching Lines...")
        async with session.get(f"{METRO_API_BASE}/GetLines") as resp:
            data = await resp.json()
            lines = data.get("Data", [])

        stations_map = {}
        directions_map = {}

        for line in lines:
            line_id = line["Id"]
            print(f"Fetching Stations for Line {line_id}...")
            async with session.get(f"{METRO_API_BASE}/GetStationById/{line_id}") as resp:
                data = await resp.json()
                stations_map[line_id] = data.get("Data", [])

            print(f"Fetching Directions for Line {line_id}...")
            async with session.get(f"{METRO_API_BASE}/GetDirectionById/{line_id}") as resp:
                data = await resp.json()
                directions_map[line_id] = data.get("Data", [])

        # Generate Python Code
        content = f"# Generated Metro Data\n\nMETRO_LINES = {json.dumps(lines, ensure_ascii=False, indent=4)}\n\n"
        content += f"METRO_STATIONS = {json.dumps(stations_map, ensure_ascii=False, indent=4)}\n\n"
        content += f"METRO_DIRECTIONS = {json.dumps(directions_map, ensure_ascii=False, indent=4)}\n"

        with open("handlers/metro_data.py", "w", encoding="utf-8") as f:
            f.write(content)

        print("Done! Saved to handlers/metro_data.py")


if __name__ == "__main__":
    asyncio.run(fetch())
