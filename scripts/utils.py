import cv2

def draw_line(img, coordinates):
    """
    Args:
        img: image on which you want to draw
        coordinates: list of list [[1, 2], [3, 4], [5, 6]]
    """
    for i in range(len(coordinates)):
        cv2.line(img, coordinates[i - 1], coordinates[i], 2)

    return img

def draw_shades(img, coordinates, relations):
    """
    Args:
        img: image on which you want to draw
        coordinates: list of list [[1, 2], [3, 4], [5, 6]]
        relations: relations between coordinates
    """
    pass

def draw_polygons(img, coordinates):
    pass

def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)

def crop(img, p=0.7, offset_x=0, offset_y=0):
    h, w = img.shape[:2]
    x = int(min(w, h) * p)
    l = (w - x) // 2
    r = w - l
    u = (h - x) // 2
    d = h - u

    offset_x = clamp(offset_x, -l, w - r)
    offset_y = clamp(offset_y, -u, h - d)

    l += offset_x
    r += offset_x
    u += offset_y
    d += offset_y

    return img[u:d, l:r], (offset_x, offset_y)