from langchain_core.prompts import ChatPromptTemplate

# 使用 LangChain 的 ChatPromptTemplate
STORYBOARD_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的动画分镜师,擅长将场景转换为详细的分镜脚本。"),
    ("human", """将以下场景转换为分镜脚本。

场景信息:
{scene_info}

角色信息:
{characters_info}

请为每个场景设计完整的渲染信息,包括:

1. 音频信息 (audio):
   - type: "dialogue"(对话) 或 "narration"(旁白)
   - speaker: 说话者名称(旁白时为"narrator")
   - text: 对话或旁白文本
   - estimated_duration: 预估时长(秒,基于文本长度,约3字/秒)

2. 图像渲染信息 (image):
   - prompt: 详细的图像生成提示词,包含环境、角色外貌、动作、光线、氛围
   - negative_prompt: 负向提示词(如"low quality, blurry")
   - style_tags: 风格标签数组(如["anime", "high quality"])
   - shot_type: 镜头类型
     * close_up: 特写
     * medium_shot: 中景
     * full_shot: 全景
     * wide_shot: 远景
   - camera_angle: 镜头角度
     * eye_level: 平视
     * high_angle: 俯视
     * low_angle: 仰视
   - composition: 构图原则
     * rule_of_thirds: 三分法
     * centered: 居中
     * symmetrical: 对称
   - lighting: 光线设计
     * natural: 自然光
     * soft: 柔光
     * dramatic: 戏剧性
     * backlight: 背光

3. 角色渲染信息 (characters):
   - 包含场景中每个角色的完整外貌信息
   - name: 角色名称
   - gender: 性别
   - age: 年龄
   - age_stage: 年龄段描述
   - hair: 发型和颜色
   - eyes: 眼睛颜色和特征
   - clothing: 服装描述
   - features: 独特特征
   - body_type: 体型
   - height: 身高描述
   - skin: 肤色
   - personality: 性格特点
   - role: 在故事中的作用

4. 场景基础信息:
   - location: 地点
   - time: 时间
   - atmosphere: 氛围
   - description: 场景描述
   - character_action: 角色动作描述
   - duration: 分镜时长(秒,最小3秒,最大10秒)

请以JSON格式输出,严格遵循以下schema:
{{
    "scenes": [
        {{
            "scene_id": 场景编号(数字),
            "chapter_id": 章节编号(数字),
            "location": "地点",
            "time": "时间",
            "atmosphere": "氛围",
            "description": "场景描述",
            "characters": [
                {{
                    "name": "角色名",
                    "gender": "性别",
                    "age": 年龄(数字或null),
                    "age_stage": "年龄段",
                    "hair": "发型",
                    "eyes": "眼睛",
                    "clothing": "服装",
                    "features": "特征",
                    "body_type": "体型",
                    "height": "身高",
                    "skin": "肤色",
                    "personality": "性格",
                    "role": "作用"
                }}
            ],
            "audio": {{
                "type": "dialogue或narration",
                "speaker": "说话者",
                "text": "文本内容",
                "estimated_duration": 时长(浮点数)
            }},
            "image": {{
                "prompt": "详细的图像生成提示词",
                "negative_prompt": "负向提示词",
                "style_tags": ["风格标签"],
                "shot_type": "镜头类型",
                "camera_angle": "镜头角度",
                "composition": "构图原则",
                "lighting": "光线设计"
            }},
            "duration": 时长(浮点数),
            "character_action": "角色动作"
        }}
    ]
}}

注意事项:
1. image.prompt必须详细具体,包含所有视觉元素
2. audio.type必须是"dialogue"或"narration"
3. 时长计算要符合实际需求(基于对话长度,约3字/秒)
4. characters数组必须包含场景中所有角色的完整信息
5. 确保JSON格式正确,可以被解析
6. 每个场景的scene_id必须与输入对应""")
])
