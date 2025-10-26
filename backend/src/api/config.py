from pydantic import BaseModel, Field
import os


class APIConfig(BaseModel):
    """API configuration settings"""
    
    media_root: str = Field(
        default="./data",
        description="Root directory for media files (videos, images, etc.)"
    )
    
    media_url_prefix: str = Field(
        default="/static",
        description="URL prefix for accessing media files"
    )
    
    exposed_media_subdir: str = Field(
        default="videos",
        description="Subdirectory within media_root to expose publicly (for security)"
    )
    
    backend_base_url: str = Field(
        default="",
        description="Backend base URL for generating absolute URLs (e.g., http://localhost:8000). If empty, relative URLs are used."
    )
    
    def get_media_root_path(self) -> str:
        """Get absolute path to media root directory"""
        return os.path.abspath(self.media_root)
    
    def get_exposed_media_path(self) -> str:
        """Get absolute path to exposed media directory"""
        return os.path.join(self.get_media_root_path(), self.exposed_media_subdir)
    
    def path_to_url(self, file_path: str) -> str:
        """
        Convert local file path to URL
        
        Args:
            file_path: Local file path
            
        Returns:
            URL path (absolute if backend_base_url is set, relative otherwise)
        """
        if not file_path or not os.path.exists(file_path):
            return file_path
        
        file_path = os.path.abspath(file_path)
        exposed_path = os.path.abspath(self.get_exposed_media_path())
        media_root = self.get_media_root_path()
        
        if file_path.startswith(exposed_path):
            relative_path = os.path.relpath(file_path, exposed_path)
        elif file_path.startswith(media_root):
            relative_path = os.path.relpath(file_path, media_root)
        else:
            return file_path
        
        from urllib.parse import quote
        url_path = "/".join(quote(part, safe='') for part in relative_path.split(os.sep))
        url = f"{self.media_url_prefix}/{url_path}"
        
        if self.backend_base_url:
            return f"{self.backend_base_url.rstrip('/')}{url}"
        return url


# Global config instance (can be overridden via environment variables)
api_config = APIConfig(
    media_root=os.getenv("MEDIA_ROOT", "./data"),
    media_url_prefix=os.getenv("MEDIA_URL_PREFIX", "/static"),
    exposed_media_subdir=os.getenv("EXPOSED_MEDIA_SUBDIR", "videos"),
    backend_base_url=os.getenv("BACKEND_BASE_URL", "")
)
