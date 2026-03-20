import cv2
import numpy as np

# RGB format blue DATABASE
target_blues_rgb = [
    [34, 43, 92], [17, 35, 81], [25, 50, 106],
    [10, 41, 95], [23, 42, 98], [34, 44, 102],
    [25, 46, 96], [18, 42, 93], [27, 60, 122], 
]

# Convert RGB to BGR for OpenCV
target_blues_bgr = np.array([[b, g, r] for r, g, b in target_blues_rgb])

#Padding accuracy
padding = 5

lower_range = np.clip(np.min(target_blues_bgr, axis=0) - padding, 0, 255)
upper_range = np.clip(np.max(target_blues_bgr, axis=0) + padding, 0, 255)

def detect_blue_full(image_path, window_x=500, window_y=300, window_size=500, min_group_size=5):
    """
    Displays full PNG with detection box and pixel groups
    """
    img = cv2.imread(image_path)
    if img is None:
        print("Couldn't load image")
        return []
    
    h, w = img.shape[:2]
    window_x = min(window_x, w - window_size)
    window_y = min(window_y, h - window_size)
    
    # Make a copy of the full image to draw on
    display = img.copy()
    
    # Extract ROI for detection
    roi = img[window_y:window_y+window_size, window_x:window_x+window_size]
    
    # Create mask
    mask = cv2.inRange(roi, lower_range, upper_range)
    
    # Get connected components
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
    
    # Draw detection window on full image
    cv2.rectangle(display, (window_x, window_y), 
                 (window_x+window_size, window_y+window_size), 
                 (255, 255, 255), 2)  # White box
    
    # Draw groups on full image (adjusting coordinates to full image)
    groups = []
    for i in range(1, num_labels):
        size = stats[i, cv2.CC_STAT_AREA]
        left = stats[i, cv2.CC_STAT_LEFT] + window_x
        top = stats[i, cv2.CC_STAT_TOP] + window_y
        width = stats[i, cv2.CC_STAT_WIDTH]
        height = stats[i, cv2.CC_STAT_HEIGHT]
        centroid = (int(centroids[i][0]) + window_x, int(centroids[i][1]) + window_y)
        
        groups.append({
            'size': size,
            'bbox': (left, top, width, height),
            'centroid': centroid
        })
        
        if size >= min_group_size:
            # Draw green rectangle for significant groups
            cv2.rectangle(display, (left, top), (left+width, top+height), (0, 255, 0), 2)
            cv2.putText(display, f"{size}", (left, top-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            # Draw centroid
            cv2.circle(display, centroid, 3, (0, 255, 0), -1)
    
    # Add info text
    cv2.putText(display, f"Window: {window_size}x{window_size} at ({window_x},{window_y})", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(display, f"Groups ≥{min_group_size}px: {sum(1 for g in groups if g['size']>=min_group_size)}", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Show full image
    cv2.imshow('Full Image with Detection', display)
    print(f"Found {len(groups)} groups, {sum(1 for g in groups if g['size']>=min_group_size)} ≥{min_group_size}px")
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    return groups

# Usage - now shows full PNG with detection box and groups
groups = detect_blue_full('AUTOVENTPARRY_tests/vent1.png', window_x=155, window_y=150, window_size=350, min_group_size=500)