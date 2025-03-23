def get_physical_index(r, logical_index):
    p_rows, p_cols = 3, 5
    if r == 0:
        return logical_index
    elif r == 90:
        return ( (p_rows - 1 - (logical_index % p_rows)) ) * p_cols + (logical_index // p_rows )
    elif r == 180:
        return (p_rows * p_cols) - logical_index - 1
    elif r == 270:
        return ( (logical_index % p_rows) * p_cols ) + (p_cols - 1 - (logical_index // p_rows ))
    else:
        return None  # Handle unexpected rotation as needed

print(get_physical_index(270, 0))  # Should output 10


def get_logical_index(r, physical_index):
    p_rows, p_cols = 3, 5
    total = p_rows * p_cols
    if r == 0:
        return physical_index
    elif r == 90:
        return 3 * (physical_index % p_cols) + (2 - (physical_index // p_cols))
    elif r == 180:
        return total - 1 - physical_index
    elif r == 270:
        # Iterate possible b values (0,1,2) to find valid case
        for b in range(2, -1, -1):
            if 5 * b <= physical_index and 5 * b >= physical_index - 4:
                a = 4 + 5 * b - physical_index
                if 0 <= a <= 4:
                    return 3 * a + b
        return None  # Handle invalid case as needed
    else:
        return None  # Handle unexpected rotation as needed
    
print(get_logical_index(90, 10))