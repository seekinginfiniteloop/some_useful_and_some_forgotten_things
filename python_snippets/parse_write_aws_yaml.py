from pathlib import Path
from typing import Any


import cfn_flip.yaml_dumper
import yaml

from cfn_tools import load_yaml


def parse_aws_yaml(raw_yaml: str) -> Any:
    return load_yaml(raw)

def write_aws_yaml(yaml_dict: dict[Any, Any], output_path: str | Path) -> None:
    dumper = cfn_flip.yaml_dumper.get_dumper(clean_up=True, long_form=False)
    Path(output_path).write_text(yaml.dump(yaml_dict, Dumper=dumper, default_flow_style=False, allow_unicode=True))
