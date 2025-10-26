
import sys
import os
import asyncio

# Add the current directory and venv to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
venv_packages = os.path.join(current_dir, '..', '.venv', 'Lib', 'site-packages')

# Insert paths at the beginning to take priority
sys.path.insert(0, current_dir)
sys.path.insert(0, venv_packages)

# Try to import fastapi to check if paths are set correctly
try:
    import fastapi
    print("FastAPI imported successfully from venv")
except ImportError as e:
    print(f"Failed to import FastAPI from venv: {e}")
    # Try to import from user site packages as fallback
    user_site_packages = r'C:\Users\28386\AppData\Roaming\Python\Python313\site-packages'
    sys.path.insert(0, user_site_packages)
    try:
        import fastapi
        print("FastAPI imported from user site-packages")
    except ImportError as e:
        print(f"Failed to import FastAPI from user site-packages: {e}")

# Now we can import fastapi and other modules
from src.api.app import app
import uvicorn
from src.core.pipeline import AnimePipeline
from src.core.progress_tracker import ProgressTracker

# 测试pipeline生成逻辑
if __name__ == "__main__":
    
    # 创建进度追踪器
    progress_tracker = ProgressTracker()
    
    # 创建 pipeline 实例
    pipeline = AnimePipeline(
        api_key=os.getenv("OPENAI_API_KEY"),
        progress_tracker=progress_tracker,
        task_id="test-tttttttttttttttt"
        # task_id=str(uuid4())
    )
    
    # 定义异步执行函数
    async def main():
        ret = await pipeline.execute(
            novel_text="""
                第一章 相遇
    
    阳光透过窗户洒进教室,小明坐在座位上认真听课。他是一个16岁的高中生,
    留着短黑发,棕色的眼睛充满了好奇。今天他穿着整洁的校服。
    
    "小明,你能回答这个问题吗?"老师问道。
    
    "好的,老师。"小明站起来,自信地回答。
    
    这时,教室门突然打开,一个女孩走了进来。她叫小红,也是16岁,
    长长的黑发扎成马尾,明亮的眼睛里带着一丝紧张。
    
    第二章 友谊
    
    下课后,小明和小红在操场上相遇。
    
    "你好,我是小明。"他友好地打招呼。
    
    "你好,我是小红。"她微笑着回应。
    
    从那天起,他们成了好朋友。
            """,
            options={}
        )
        print(ret)
    
    # 使用 asyncio.run() 运行异步函数
    asyncio.run(main())
