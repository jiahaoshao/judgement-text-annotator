import json
from datetime import datetime
from docx import Document
import gradio as gr
import csv
import os
import tempfile
from io import StringIO
from dotenv import load_dotenv

from openai import OpenAI

load_dotenv()

# Deepseek API
API_key = os.getenv("DEEPSEEK_API_KEY")

file_path = []

mark_judgment_info = ""
def extract_info_from_judgment(judgment_text):
    system_prompt = """
        角色：
        你是一位专业且经验丰富的法律文书信息提取助手。

        背景：
        我们有一系列交通事故相关的法律文书，需要从中提取关键信息。

        知识：
        法律文书包含了诸如案件类型、文书ID、案件名称、案件编号、裁判日期等多方面的信息。

        任务：
        仔细阅读输入的法律文书，按照规定的JSON格式准确提取各项信息。若文书中未提及某项信息，则对应字段填写“空”。

        其他：
        JSON格式不用加上```json```标记，直接填写即可。

        """

    user_prompt = """请从以下法律文书中提取相关信息：
            "案件类型": "空",
            "文书ID": "空",
            "案件名称一": "空",
            "案件名称二": "空",
            "案件编号": "空",
            "裁判日期": "空",
            "法院名称": "空",
            "肇事人": "空",
            "性别": "空",
            "出生日期": "空",
            "民族": "空",
            "文化程度": "空",
            "户籍所在地": "空",
            "案发时间": "空",
            "车辆品牌和车型": "空",
            "事故发生地": "空",
            "酒精": "空",
            "伤亡数量": "空",
            "驾照实习期开始": "空",
            "驾驶实习期结束": "空",
            "驾照类型": "空",
            "实习期类型": "空",
            "经济损失": "空",
            "撤销案件号": "空",
            "维持案件号": "空"
        """ + judgment_text

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    client = OpenAI(api_key=API_key, base_url="https://api.deepseek.com")

    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        print(completion)
        content = completion.choices[0].message.content if completion.choices else ""
        # print(content)

        try:
            info_dict = json.loads(content)
            return info_dict
        except json.JSONDecodeError as e:
            print(f"解析JSON时出错: {e}")
            return {}

    except Exception as e:
        print(f"An error occurred: {e}")
    return {}

def mark_judgment(judgment_text):
    global mark_judgment_info
    if judgment_text == "":
        return []
    info_dict = extract_info_from_judgment(judgment_text)
    mark_judgment_info = [[key, value] for key, value in info_dict.items()]
    return mark_judgment_info

def download_csv():
    output = StringIO()
    writer = csv.writer(output)
    for key, value in mark_judgment_info:
        writer.writerow([key, value])
    output.seek(0)

    # 保存到临时文件
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    temp_file_path = os.path.join(tempfile.gettempdir(), f"marked_judgment_{timestamp}.csv")


    with open(temp_file_path, 'w', newline='', encoding='utf-8') as f:
        f.write(output.getvalue())

    file_path.append(temp_file_path)

    return file_path

def clear_input():
    return "", []

def read_docx(file):
    doc = Document(file.name)
    content = []
    for paragraph in doc.paragraphs:
        content.append(paragraph.text)
    return '\n'.join(content)

def read_uploaded_file(file):

    if file is None:
        return ""
    print(file.name)
    is_doc = file.name.endswith(".doc") or file.name.endswith(".docx")
    if is_doc:
        connect = read_docx(file)
        return connect
    else:
        try:
            with open(file.name, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except UnicodeDecodeError as e:
            return "读取文件时出现编码错误，请检查文件编码是否正确"

def main():
    with gr.Blocks() as demo:
        gr.Markdown("输入判决书文本内容，系统将输出标记后的信息。")

        with gr.Row():
            with gr.Column():
                input_text = gr.Textbox(
                    lines=10,
                    placeholder="请输入判决书文本内容...",
                    label="",
                    interactive=True
                )
                with gr.Row():
                    submit_btn = gr.Button("提交")
                    clear_btn = gr.Button("清除")
            with gr.Column():
                output_boxes = gr.DataFrame(headers=["Key", "Value"], visible=True, wrap=True, interactive=True)
                download_btn = gr.Button("转为CSV", elem_id="download-btn")
        with gr.Row():
            upload_file = gr.File(label="上传判决书", elem_id="upload-file")

        upload_file.change(fn=read_uploaded_file, inputs=upload_file, outputs=input_text)
        submit_btn.click(fn=mark_judgment, inputs=input_text, outputs=output_boxes)
        clear_btn.click(fn=clear_input, outputs=[input_text, output_boxes])
        download_btn.click(fn=download_csv, outputs=gr.File(label="CSV文件"))

        demo.launch()

if __name__ == "__main__":
   main()