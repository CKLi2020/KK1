import fitz  # PyMuPDF
from PIL import Image
import tempfile
import os, shutil

def generate_pdf(image_sources, output_path=None):
    """
    生成PDF文件
    :param image_sources: 图片源列表，可以是PIL Image对象列表，也可以是文件路径列表
    :param output_path: 输出PDF文件的路径。如果为None，则生成临时文件
    :return: PDF文件路径
    """
    # 创建项目内的临时目录，避免使用系统临时目录
    project_temp_base = "./temp"
    os.makedirs(project_temp_base, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=project_temp_base)
    
    try:
        pdf_document = fitz.open()  # 创建一个新的空白PDF文档

        for i, source in enumerate(image_sources):
            # 处理图片源
            if isinstance(source, str):
                # 如果是文件路径
                img = Image.open(source)
                should_close = True
            else:
                # 如果是PIL Image对象
                img = source
                should_close = False
                
            width, height = img.size  # 获取图片原始宽高（单位：像素）
            
            # 保存每张图像到临时目录 (PyMuPDF insert_image 需要文件路径或流)
            temp_img_path = os.path.join(temp_dir, f'image{i}.jpg')
            img.save(temp_img_path, format="JPEG", quality=95)
            
            if should_close:
                img.close()

            # 创建新页面
            pdf_page = pdf_document.new_page(width=width, height=height)

            # 定义插入图像的矩形区域
            rect = fitz.Rect(0, 0, width, height)
            # 插入图像到PDF页面
            pdf_page.insert_image(rect, filename=temp_img_path)
            
        # 确定输出路径
        if output_path:
            final_path = output_path
        else:
            final_path = tempfile.mktemp(suffix='.pdf', dir=project_temp_base)

        # 保存PDF文档
        pdf_document.save(final_path)
        pdf_document.close()
        
        return final_path
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise e
    finally:
        # 清理临时目录及其内容
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# 调用示例
# 假设 images 是一个包含PIL Image对象的列表
# pdf_path = generate_pdf(images)
