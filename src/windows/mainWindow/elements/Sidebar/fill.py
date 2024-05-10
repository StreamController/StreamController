a = {1: "1", 10: "10", 3: "3"}

# Sort the dictionary by keys
sorted_keys = sorted(a.keys())

new_a = {}
for new_key, old_key in enumerate(sorted_keys):
    new_a[int(new_key)] = a[old_key]

print(new_a)