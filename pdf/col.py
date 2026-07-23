import cv2


# 設定影片路徑
video_path = 'cam3_13-00-03.mp4'
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("❌ 無法開啟影片檔案，請確認路徑是否正確")
    exit()

# 取得影片資訊
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

if fps == 0 or fps != fps:
    fps = 15

# 設定輸出影片
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output_video_no_ai.mp4', fourcc, fps, (width, height))

print("🔁 開始處理影片，按下 'q' 可隨時中斷...")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("✅ 影片播放完畢")
        break

    annotated_frame = frame.copy()
    current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0  
    
    # ---------------------------------------------------------
    # 繪製底部欄位標籤 (C15 - C19)
    # ---------------------------------------------------------
    color_green = (147, 255, 147)
    color_red = (151, 151, 255)

    column_info = [
        ("C15", color_green),      
        ("C16", color_green),  
        ("C17", color_green),
        ("C18", color_green),    
        ("C19", color_green)  
    ]
    

    # =============== 尺寸與排版動態計算區 ===============
    box_count = len(column_info)
    
    # 讓這 5 個框整體佔據畫面 90% 的寬度 (左右各留 5% 空白)
    available_width = width * 0.9  
    
    # 假設間距(spacing)大小是框寬度(box_width)的 0.3 倍
    # 總寬度 = 5個框 + 4個間距 = 5*W + 4*(0.3*W) = 6.2 * W
    width_ratio = box_count + (box_count - 1) * 0.3
    
    box_width = int(available_width / width_ratio)
    spacing = int(box_width * 0.3)
    
    # 高度與字體設定
    box_height = 120            # 框的高度
    font_scale = 1.8            # 字體大小
    font_thickness = 3          # 字體粗細
    
    # 重新精算總寬度以確保絕對置中
    total_width = box_count * box_width + (box_count - 1) * spacing
    start_x = (width - total_width) // 2  
    
    # 設定方框的 Y 軸位置 (設定在畫面底部往上算 80 像素的位置)
    y_pos = height - box_height - 80 
    if y_pos < 0:
        y_pos = height - box_height - 10
    # ====================================================

    for idx, (label, color) in enumerate(column_info):
        x_start = start_x + idx * (box_width + spacing)
        x_end = x_start + box_width
        top_left = (x_start, y_pos)
        bottom_right = (x_end, y_pos + box_height)

        # 畫底色
        cv2.rectangle(annotated_frame, top_left, bottom_right, color, -1)

        # 畫邊框
        cv2.rectangle(annotated_frame, top_left, bottom_right, (255, 255, 255), 3)

        # 畫文字 (置中)
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
        text_x = x_start + (box_width - text_size[0]) // 2
        text_y = y_pos + (box_height + text_size[1]) // 2
        
        cv2.putText(annotated_frame, label, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), font_thickness, cv2.LINE_AA)

    out.write(annotated_frame)



cap.release()
out.release()
cv2.destroyAllWindows()
print("✅ 已產出影片 output_video_no_ai.mp4")
# ====================================================
# ffmpeg 轉成 HTML5 最穩格式



