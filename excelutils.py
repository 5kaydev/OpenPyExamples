def cell_value_as_string(cell):
    """Gets the value of a cell as a string or None if there is no value.

    :param cell The cell to get the value from.
    :type cell: openpyxl.cell.cell.Cell

    :rtype: str or None
    """
    value = cell.value
    if value is None or isinstance(value, str):
        return value
    return str(value)


def stripped_cell_value(cell):
    """Gets the stripped value of a cell as a string or None if there is no value.

    :param cell The cell to get the value from.
    :type cell: openpyxl.cell.cell.Cell

    :rtype: str or None
    """
    if cell.value is None:
        return None
    value = cell.value if isinstance(cell.value, str) else str(cell.value)
    return value.strip()
