import os
import io
import unicodedata
from PIL import Image, ImageDraw, ImageFont
from handright import Template, handwrite, Feature

# Helper functions copied from app.py
def clean_text_for_handwrite(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\u200b', '')
    text = text.replace('\u200c', '')
    text = text.replace('\u200d', '')
    text = text.replace('\ufeff', '')
    text = text.replace('\u00ad', '')
    
    block_chars = set(chr(i) for i in range(0x2580, 0x25A0))
    geometric_chars = set(chr(i) for i in range(0x25A0, 0x2600))
    
    cleaned = []
    for char in text:
        if char == '\n':
            cleaned.append(char)
        elif char == '\t':
            cleaned.append('    ')
        elif char in block_chars or char in geometric_chars:
            continue
        else:
            category = unicodedata.category(char)
            if category not in ('Cc', 'Cf', 'Co', 'Cs', 'Cn'):
                code_point = ord(char)
                if code_point < 0x1F000 or (0x2000 <= code_point < 0x2100):
                    if not (0xE000 <= code_point <= 0xF8FF):
                        cleaned.append(char)
    return ''.join(cleaned)

def filter_unsupported_chars(text, font):
    filtered = []
    for char in text:
        if char == '\n':
            filtered.append(char)
            continue
        # Simple check: if getbbox returns None, it might be unsupported (or whitespace)
        # But for whitespace it returns None too.
        # handright handles this internally mostly, but app.py had this function.
        # For simplicity in this script, I'll skip complex filtering as the default text is known to be safe.
        filtered.append(char)
    return ''.join(filtered)

def create_notebook_image(
    width,
    height,
    line_spacing,
    top_margin,
    bottom_margin,
    left_margin,
    right_margin,
    font_size,
    isUnderlined,
    line_color="red",
    paper_type="plain",
):
    if paper_type == "grid":
        grid_color = (0, 180, 180)
        paper_color = (255, 255, 255)
        image = Image.new("RGB", (width, height), paper_color)
        draw = ImageDraw.Draw(image)
        cell_size = int(font_size * 1.15)
        start_x = left_margin
        start_y = top_margin
        x = start_x
        while x <= width - right_margin:
            draw.line((x, start_y, x, height - bottom_margin), fill=grid_color, width=1)
            x += cell_size
        y = start_y
        while y <= height - bottom_margin:
            draw.line((start_x, y, width - right_margin, y), fill=grid_color, width=1)
            y += cell_size
            
    elif paper_type == "lined" or isUnderlined == True or isUnderlined == "true":
        paper_color = (255, 251, 240)
        image = Image.new("RGB", (width, height), paper_color)
        draw = ImageDraw.Draw(image)
        y = top_margin + line_spacing
        while y < height - bottom_margin:
            draw.line((left_margin, y-1, width - right_margin, y-1), fill=line_color)
            draw.line((left_margin, y, width - right_margin, y), fill=line_color)
            draw.line((left_margin, y+1, width - right_margin, y+1), fill=line_color)
            y += line_spacing
    else:
        image = Image.new("RGB", (width, height), "white")
    return image

# Main generation logic
def generate_default_preview():
    text = """                        《东风破》
                        词：方文山 曲：周杰伦

一盏离愁孤灯伫立在窗口，我在门后假装你人还没走，旧地如重游月圆更寂寞，夜半清醒的烛火不忍苛责我。一壶漂泊浪迹天涯难入喉，你走之后酒暖回忆思念瘦，水向东流时间怎么偷，花开就一次成熟我却错过。谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。

一壶漂泊浪迹天涯难入喉，你走之后酒暖回忆思念瘦，水向东流时间怎么偷，花开就一次成熟我却错过。谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。

谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。"""

    # Parameters
    width = 2480
    height = 3508
    font_size = 90
    line_spacing = 120
    word_spacing = 10
    top_margin = 150
    bottom_margin = 150
    left_margin = 150
    right_margin = 150
    paper_type = "lined" # red maps to lined with red color
    line_color = "red"
    is_underlined = True
    
    # Font
    font_path = os.path.join("font_assets", "司马彦硬笔手写体.TTF")
    if not os.path.exists(font_path):
        print(f"Font not found: {font_path}")
        return

    font = ImageFont.truetype(font_path, size=font_size)
    
    # Background
    background_image = create_notebook_image(
        width, height, line_spacing, top_margin, bottom_margin,
        left_margin, right_margin, font_size, is_underlined, line_color, paper_type
    )
    
    # Template
    template = Template(
        background=background_image,
        font=font,
        line_spacing=line_spacing,
        left_margin=left_margin,
        top_margin=top_margin,
        right_margin=right_margin - word_spacing * 2,
        bottom_margin=bottom_margin,
        word_spacing=word_spacing,
        line_spacing_sigma=2,
        font_size_sigma=2,
        word_spacing_sigma=2,
        end_chars="，。",
        perturb_x_sigma=2,
        perturb_y_sigma=2,
        perturb_theta_sigma=0.05,
    )
    
    # Generate
    text = clean_text_for_handwrite(text)
    images = list(handwrite(text, template))
    
    if images:
        # Save the first page
        output_dir = os.path.join("..", "web_frontend", "images")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "default_preview.png")
        images[0].save(output_path)
        print(f"Generated default preview at {output_path}")
    else:
        print("No images generated")

if __name__ == "__main__":
    generate_default_preview()
