
import numpy as np


def dist( n, m=None):
    """
    Return a rectangular array in which each pixel = euclidian
    distance from the origin.

    """
    n1 = n
    m1 = m if m else n

    x = np.arange(n1)
    x = np.array([val**2 if val < (n1-val) else (n1-val)**2 for val in x])
    a = np.ndarray((n1, m1), float)  # Make array

    for i in range(int((m1/2)+1)):  # Row loop
        y = np.sqrt(x+i**2.0)  # Euclidian distance
        a[i, :] = y  # Insert the row
        if i != 0: a[m1-i, :] = y  # Symmetrical
    return a