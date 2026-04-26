"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import os

import globals as gl

DEFAULT_DATA_PATH = os.path.expanduser("~/.var/app/com.core447.StreamController/data")


def handle_list_pages():
    """List available StreamController pages and print summary info."""
    print("Scanning for available pages...")
    print()

    try:
        # Try to get pages from the file system
        import os
        data_path = gl.DATA_PATH if hasattr(gl, 'DATA_PATH') else DEFAULT_DATA_PATH
        pages_dir = os.path.join(data_path, "pages")

        if not os.path.exists(pages_dir):
            print(f"Pages directory not found: {pages_dir}")
            print("\nThis might mean StreamController hasn't been set up yet.")
            return True

        page_files = [f for f in os.listdir(pages_dir) if f.endswith('.json') and not f.startswith('.')]

        if not page_files:
            print("No pages found.")
            print(f"\nPages should be located in: {pages_dir}")
            return True

        print(f"Found {len(page_files)} page(s):")
        print()

        for page_file in sorted(page_files):
            page_name = os.path.splitext(page_file)[0]
            page_path = os.path.join(pages_dir, page_file)

            try:
                # Try to read basic info from the page file
                import json
                with open(page_path, 'r') as f:
                    page_data = json.load(f)

                print(f"  {page_name}")

                # Count items with states
                items_with_states = 0
                for input_type in ['keys', 'dials', 'touchscreens']:
                    if input_type in page_data:
                        for item_id, item_data in page_data[input_type].items():
                            if 'states' in item_data and item_data['states']:
                                states_count = len(item_data['states'])
                                items_with_states += 1
                                if states_count > 1:
                                    print(f"    - {input_type[:-1]} {item_id}: {states_count} states")

                if items_with_states == 0:
                    print(f"    - No configured items")

            except Exception as e:
                print(f"    - Error reading page: {e}")

            print()

    except Exception as e:
        print(f"Error scanning pages: {e}")

    return True
