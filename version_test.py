from packaging import version

def get_newest_compatible_plugin(current_app_version, available_plugin_versions):
    current_major_version = version.parse(current_app_version).major

    compatible_versions = [v for v in available_plugin_versions if version.parse(v).major == current_major_version]
    if compatible_versions:
        return max(compatible_versions)
    else:
        return None

# Example usage:
current_app_version = "1.1.2"
available_plugin_versions = ["1.0.1", "1.0.2", "1.0.3", "1.1.0", "0.9.9"]

newest_compatible_plugin = get_newest_compatible_plugin(current_app_version, available_plugin_versions)
print("Newest compatible plugin version:", newest_compatible_plugin)
