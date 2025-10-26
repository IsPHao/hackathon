from langchain_core.prompts import ChatPromptTemplate

# 使用 LangChain 的 ChatPromptTemplate
NOVEL_PARSE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的小说分析专家,擅长将小说文本解析成结构化数据。"),
    ("human", """请分析以下小说文本,提取以下信息:

1. **角色信息**(最多{max_characters}个主要角色)
   - 姓名
   - 详细外貌描述(性别、年龄、年龄段、发型、眼睛、服装、特征、体型、身高、肤色)
   - 性格特点
   - 在故事中的作用
   - 如果角色在不同年龄段有不同外貌,请在age_variants中记录

2. **章节和场景信息**
   - 先识别章节结构(如"第一章"、"第二章"等)
   - 每个章节包含标题、概要和多个场景
   
   **场景拆分原则**(重要):
   - 每个场景 = 一个静态画面 + 一段旁白或一句对话
   - 不同角色说话 → 拆分成不同场景
   - 同一角色不同动作 → 拆分成不同场景
   - 目的:用静态图片+单段语音/旁白来表示每个场景
   
   每个场景包含:
     * 场景编号
     * 地点
     * 时间(具体时间或时间段)
     * 出现的角色
     * 静态场景环境描述(背景、物体、环境细节)
     * 场景氛围和光线
     * 内容类型(narration或dialogue)
     * 旁白内容(当类型为narration时)
     * 说话角色和对话内容(当类型为dialogue时)
     * 角色当前动作(单一动作)
     * 角色外貌更新(如果本场景中描述了角色的外貌、年龄变化等)

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
                "gender": "male/female/unknown",
                "age": 年龄(数字,可为null),
                "age_stage": "年龄段(童年/少年/青年/中年/老年)",
                "hair": "发型和颜色",
                "eyes": "眼睛颜色和特征",
                "clothing": "典型服装",
                "features": "独特特征",
                "body_type": "体型特征",
                "height": "身高描述",
                "skin": "肤色特征"
            }},
            "personality": "性格特点",
            "role": "在故事中的作用",
            "age_variants": [
                {{
                    "age_stage": "年龄段",
                    "appearance": {{
                        "gender": "male/female",
                        "age": 年龄,
                        "age_stage": "年龄段",
                        "hair": "发型和颜色",
                        "eyes": "眼睛颜色和特征",
                        "clothing": "典型服装",
                        "features": "独特特征",
                        "body_type": "体型特征",
                        "height": "身高描述",
                        "skin": "肤色特征"
                    }}
                }}
            ]
        }}
    ],
    "chapters": [
        {{
            "chapter_id": 章节编号(数字,从1开始),
            "title": "章节标题",
            "summary": "章节概要",
            "scenes": [
                {{
                    "scene_id": 场景编号(数字),
                    "location": "地点",
                    "time": "时间",
                    "characters": ["角色1", "角色2"],
                    "description": "静态场景环境描述",
                    "atmosphere": "氛围",
                    "lighting": "光线描述",
                    "content_type": "narration或dialogue",
                    "narration": "旁白内容(当content_type=narration时)",
                    "speaker": "说话角色(当content_type=dialogue时)",
                    "dialogue_text": "对话内容(当content_type=dialogue时)",
                    "character_action": "角色当前动作",
                    "character_appearances": {{
                        "角色名": {{
                            "gender": "male/female",
                            "age": 年龄,
                            "age_stage": "年龄段",
                            "hair": "发型和颜色",
                            "eyes": "眼睛颜色和特征",
                            "clothing": "服装",
                            "features": "特征"
                        }}
                    }}
                }}
            ]
        }}
    ],
    "plot_points": [
        {{
            "scene_id": 场景编号,
            "type": "conflict/climax/resolution/normal",
            "description": "描述"
        }}
    ]
}}

注意事项:
1. 先识别章节结构(如"第一章"、"第二章"、"序章"等),如果没有明确章节,可以按内容自行划分
2. 每个章节应包含多个相关场景,场景编号在整个小说中连续递增
3. **场景拆分至关重要**:
   - 每个场景只能有一段旁白或一句对话,不能同时包含
   - 不同角色说话必须拆分成不同场景
   - 同一角色不同动作必须拆分成不同场景
   - 例如:"小明走进教室"是一个场景,"小明坐下来"是另一个场景
4. 角色外貌描述要详细具体,便于后续图像生成
5. 如果同一角色在不同年龄段有不同外貌,请在age_variants中分别记录
6. 场景中如果有角色外貌、年龄的描述,请在character_appearances中记录,用于更新全局角色信息
7. 场景描述要视觉化,包含环境、光线、氛围等细节
8. 对话要保留原文,不要总结
9. 所有字段如果没有信息,请提供空字符串或空数组,不要省略字段
10. 确保JSON格式正确,可以被解析""")
])
