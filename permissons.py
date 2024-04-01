import subprocess
import shlex

def parse_flatpak_permissions(app_id):
    # Define the flatpak command with the --show-permissions flag for the app_id
    command = f"flatpak info --show-permissions {app_id}"
    # Execute the command, capturing stdout and stderr
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # If there is an error (captured in stderr), raise an exception
    if stderr:
        raise Exception(f"Error running flatpak info command: {stderr.decode()}")

    # Decode the stdout to get the permissions output as a string
    permissions_output = stdout.decode()
    # Initialize an empty dictionary to hold the parsed permissions
    permissions_dict = {}

    # Split the output into sections based on double newline characters
    sections = permissions_output.split('\n\n')
    for section in sections:
        # Split the section into lines and extract the header
        lines = section.strip().split('\n')
        header = lines.pop(0).strip('[]').lower().replace(' ', '-')
        # Parse the 'Context' section differently from the policy sections
        if header == 'context':
            context_dict = {}
            for line in lines:
                # Split each line on '=' and construct a list of values, ignoring the last empty string
                if '=' in line:
                    key, value = line.split('=')
                    context_dict[key] = value.split(';')[:-1]
            # Add the context dictionary to the permissions dictionary
            permissions_dict[header] = context_dict
        else: # For 'Session Bus Policy' and 'System Bus Policy' sections
            policy_list = []
            for line in lines:
                # For each policy, remove the '=talk' part and add the policy to the list
                if '=' in line:
                    policy = line.split('=')[0]
                    policy_list.append(policy)
            # Add the policy list to the permissions dictionary
            permissions_dict[header] = policy_list

    # Return the complete permissions dictionary
    return permissions_dict

# Example usage
app_id = "com.core447.StreamController"
permissions = parse_flatpak_permissions(app_id)
print(permissions)