import sys
import yaml
from openapi_spec_validator import validate_spec

def validate_openapi_schema(file_path="openapi.yaml"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            spec_dict = yaml.safe_load(f)
            
        validate_spec(spec_dict)
        print(f"SUCCESS: '{file_path}' validated successfully with 0 errors!")
    except Exception as e:
        print(f"VALIDATION FAILED for '{file_path}':\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_openapi_schema()