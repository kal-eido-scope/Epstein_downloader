from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings,SettingsConfigDict
from .consts import BASE_DIR, PAGE_DIR, FILE_DIR
from pathlib import Path

def get_absolute_dir(path:str):
    """将相对路径转换为相对根目录的绝对路径，如果已经是绝对路径则直接返回"""
    p = Path(path)
    if p.is_absolute():
        return p.as_posix()
    else:
        return (BASE_DIR / p).as_posix()

class PageConfig(BaseModel):
    base_url: str = "https://www.justice.gov/epstein/doj-disclosures"
    pattern: str|None = r'href="(https:\/\/[w]{3}\.justice\.gov\/epstein\/files\/DataSet[^"]+)"'
    dir_path: str = "pages"
    @field_validator("dir_path", mode="before")
    def validate_path(cls, path):
        """验证并转换路径字符串为Path对象"""
        try: 
            return get_absolute_dir(path)
        except:
            return PAGE_DIR.as_posix()
    max_retry_times: int = 7
    max_repeat_pages: int = 5
    
class FileConfig(BaseModel):
    dir_path: str = "files"
    @field_validator("dir_path", mode="before")
    def validate_path(cls, path):
        """验证并转换路径字符串为Path对象"""
        try:
            return get_absolute_dir(path)
        except:
            return FILE_DIR.as_posix()
    max_worker: int = 6
    max_retry_times: int = 3

class MySettings(BaseSettings):
    PAGE: PageConfig = Field(default_factory=PageConfig)
    FILE: FileConfig = Field(default_factory=FileConfig)
    
class Settings(MySettings):
    model_config = SettingsConfigDict(
        env_file = str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        )