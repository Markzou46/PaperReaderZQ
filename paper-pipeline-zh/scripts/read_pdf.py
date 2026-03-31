#!/usr/bin/env python3
"""PDF阅读脚本"""
import sys

def read_pdf(file_path):
    """读取PDF文件并输出内容"""
    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            print(f"PDF文件: {file_path}")
            print(f"总页数: {len(pdf.pages)}")
            print("=" * 80)

            full_text = []
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text.append(f"\n--- 第 {i} 页 ---\n")
                    full_text.append(text)

            content = "\n".join(full_text)
            print(content)
            return content

    except ImportError:
        print("pdfplumber未安装，尝试使用PyPDF2...")
        try:
            import PyPDF2

            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                print(f"PDF文件: {file_path}")
                print(f"总页数: {len(reader.pages)}")
                print("=" * 80)

                full_text = []
                for i, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text.append(f"\n--- 第 {i} 页 ---\n")
                        full_text.append(text)

                content = "\n".join(full_text)
                print(content)
                return content

        except ImportError:
            print("错误: 需要安装 pdfplumber 或 PyPDF2")
            print("请运行: pip install pdfplumber 或 pip install PyPDF2")
            sys.exit(1)
    except Exception as e:
        print(f"读取PDF时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python read_pdf.py <pdf文件路径>")
        sys.exit(1)

    read_pdf(sys.argv[1])
