#!/usr/bin/env python3
"""
간단한 타입 변환 테스트

Pydantic 모델의 타입 변환이 올바르게 작동하는지 테스트합니다.
"""

# 필요한 최소한의 constants를 직접 정의
SUPPORTED_OUTPUT_FORMATS = ["png", "jpeg", "webp"]
ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "2.39:1"]
IMAGE_QUALITY_LEVELS = ["auto", "low", "medium", "high"]
STYLE_PRESETS = ["photorealistic", "digital_art", "oil_painting", "watercolor", "cartoon", "anime", "sketch", "vintage"]
MAX_PROMPT_LENGTH = 2000
MIN_PROMPT_LENGTH = 3
MAX_BATCH_SIZE = 4

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

# 열거형 정의
class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg" 
    WEBP = "webp"

class QualityLevel(str, Enum):
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class StylePreset(str, Enum):
    PHOTOREALISTIC = "photorealistic"
    DIGITAL_ART = "digital_art"

# 기본 모델
class BaseRequest(BaseModel):
    class Config:
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"

# 테스트용 GenerateImageRequest
class TestGenerateImageRequest(BaseRequest):
    prompt: str = Field(..., min_length=MIN_PROMPT_LENGTH, max_length=MAX_PROMPT_LENGTH)
    candidate_count: Optional[int] = Field(1, ge=1, le=MAX_BATCH_SIZE)
    optimize_prompt: Optional[bool] = Field(True)
    
    @field_validator('candidate_count', mode='before')
    @classmethod
    def validate_candidate_count(cls, v):
        if v is None:
            return 1
        
        if isinstance(v, str):
            try:
                v = int(v.strip())
            except ValueError:
                raise ValueError(f"candidate_count must be a valid integer, got: '{v}'")
        
        if isinstance(v, int):
            return v
        
        raise ValueError(f"candidate_count must be an integer or string number, got: {type(v)}")
    
    @field_validator('optimize_prompt', mode='before')
    @classmethod
    def validate_optimize_prompt(cls, v):
        if v is None:
            return True
        
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"optimize_prompt must be a valid boolean string, got: '{v}'")
        
        if isinstance(v, bool):
            return v
        
        if isinstance(v, (int, float)):
            return bool(v)
        
        raise ValueError(f"optimize_prompt must be a boolean or string boolean, got: {type(v)}")

def test_conversions():
    print("🧪 Testing type conversions...")
    
    # candidate_count 테스트
    test_cases = [
        ({"prompt": "test", "candidate_count": "1"}, 1),
        ({"prompt": "test", "candidate_count": "4"}, 4),
        ({"prompt": "test", "candidate_count": 2}, 2),
        ({"prompt": "test", "candidate_count": None}, 1),
    ]
    
    for data, expected in test_cases:
        try:
            request = TestGenerateImageRequest(**data)
            actual = request.candidate_count
            if actual == expected:
                print(f"✅ candidate_count: {data['candidate_count']} → {actual}")
            else:
                print(f"❌ candidate_count: {data['candidate_count']} → {actual} (expected {expected})")
        except Exception as e:
            print(f"❌ candidate_count: {data['candidate_count']} → ERROR: {e}")
    
    # optimize_prompt 테스트  
    bool_test_cases = [
        ({"prompt": "test", "optimize_prompt": "true"}, True),
        ({"prompt": "test", "optimize_prompt": "false"}, False),
        ({"prompt": "test", "optimize_prompt": "1"}, True),
        ({"prompt": "test", "optimize_prompt": "0"}, False),
        ({"prompt": "test", "optimize_prompt": True}, True),
        ({"prompt": "test", "optimize_prompt": False}, False),
        ({"prompt": "test", "optimize_prompt": None}, True),
    ]
    
    for data, expected in bool_test_cases:
        try:
            request = TestGenerateImageRequest(**data)
            actual = request.optimize_prompt
            if actual == expected:
                print(f"✅ optimize_prompt: {data['optimize_prompt']} → {actual}")
            else:
                print(f"❌ optimize_prompt: {data['optimize_prompt']} → {actual} (expected {expected})")
        except Exception as e:
            print(f"❌ optimize_prompt: {data['optimize_prompt']} → ERROR: {e}")
    
    print("\n✅ Type conversion test completed!")

if __name__ == "__main__":
    test_conversions()