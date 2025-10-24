from langchain_core.prompts import ChatPromptTemplate

# 使用 LangChain 的 ChatPromptTemplate
NOVEL_PARSE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的小说分析专家,擅长将小说文本解析成结构化数据。"),
    ("human", """请分析以下小说文本,提取以下信息:

1. **角色信息**(最多{max_characters}个主要角色)
   - 姓名
   - 详细外貌描述(性别、年龄、发型、眼睛、服装、特征)
   - 性格特点
   - 在故事中的作用

2. **场景信息**(最多{max_scenes}个关键场景)
   - 场景编号
   - 地点
   - 时间(具体时间或时间段)
   - 出现的角色
   - 场景描述(环境、氛围、光线)
   - 对话内容(角色+对话)
   - 动作描述
   - 场景氛围

3. **情节点**
   - 关键转折点
   - 冲突点
   - 高潮点

小说文本:
\"\"\"
{novel_text}
\"\"\"

请以JSON格式输出,严格遵循以下schema:
{{
    "characters": [
        {{
            "name": "角色名",
            "description": "简短描述",
            "appearance": {{
                "gender": "male/female",
                "age": 年龄(数字),
                "hair": "发型和颜色",
                "eyes": "眼睛颜色和特征",
                "clothing": "典型服装",
                "features": "独特特征"
            }},
            "personality": "性格特点"
        }}
    ],
    "scenes": [
        {{
            "scene_id": 场景编号(数字),
            "location": "地点",
            "time": "时间",
            "characters": ["角色1", "角色2"],
            "description": "场景描述",
            "dialogue": [
                {{"character": "角色", "text": "对话内容"}}
            ],
            "actions": ["动作1", "动作2"],
            "atmosphere": "氛围"
        }}
    ],
    "plot_points": [
        {{
            "scene_id": 场景编号,
            "type": "conflict/climax/resolution",
            "description": "描述"
        }}
    ]
}}

注意事项:
1. 角色外貌描述要详细具体,便于后续图像生成
2. 场景描述要视觉化,包含环境、光线、氛围等细节
3. 对话要保留原文,不要总结
4. 确保JSON格式正确,可以被解析""")
])

CHARACTER_APPEARANCE_ENHANCE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的角色设计专家,擅长生成详细的视觉化外貌描述。"),
    ("human", """基于以下角色基础信息,生成详细的视觉化外貌描述,用于图像生成。

角色信息:
姓名:{name}
基础描述:{description}
外貌:{appearance}

请生成一个详细的外貌描述,包括:
1. 整体风格(anime style / realistic / etc)
2. 性别和年龄
3. 发型和发色(详细描述)
4. 眼睛(颜色、形状、神态)
5. 面部特征(脸型、皮肤、特殊标记)
6. 身材体型
7. 典型服装(详细描述)
8. 独特标识(配饰、纹身等)
9. 整体气质

输出格式(用于图像生成):
{{
    "prompt": "anime style, detailed character description...",
    "negative_prompt": "low quality, blurry, distorted...",
    "style_tags": ["anime", "high quality", "detailed"]
}}""")
])

